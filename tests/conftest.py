import json
from datasette.app import Datasette
from datasette.plugins import pm
from datasette import hookimpl
from subprocess import Popen, PIPE
import pytest
import pytest_asyncio
from syrupy.extensions.image import PNGImageSnapshotExtension
from sys import executable
from datasette_comments import SCHEMA
import tempfile
import sqlite3
from pathlib import Path
import time
import httpx


FIXTURES_SQL = (Path(__file__).parent / "comments-fixtures.sql").read_text()
INTERNAL_FIXTURES_SQL = (
    Path(__file__).parent / "comments-internal-fixtures.sql"
).read_text()


def profile_pic(fill):
    return f"data:image/svg+xml,%3Csvg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='100' height='100' fill='{fill}'/%3E%3C/svg%3E"


PLUGIN_PY = f"""
from datasette import hookimpl

actors = {{
    "1": {{
        "id": "1",
        "username": "asg017",
        "name": "Alex Garcia",
        "profile_picture_url": "{profile_pic('red')}",
    }},
    "2": {{
        "id": "2",
        "username": "simonw",
        "name": "Simon Willison",
        "profile_picture_url": "{profile_pic('blue')}",
    }},
}}


@hookimpl
def datasette_comments_users():
    async def inner():
        return list(actors.values())

    return inner


@hookimpl
def actor_from_request(datasette, request):
    actor_id = request.cookies.get("actor")
    for key in actors:
        if key == actor_id:
            return actors[key]


@hookimpl
def actors_from_ids(datasette, actor_ids):
    return actors
"""

METADATA = {"permissions": {"datasette-comments-access": {"id": ["1", "2"]}}}


@pytest.fixture
def screenshot_snapshot(snapshot):
    return snapshot.use_extension(PNGImageSnapshotExtension)


@pytest.fixture
def ds_server(request):
    tmpdir = tempfile.TemporaryDirectory()
    internal_db_path = Path(tmpdir.name) / "internal.db"
    mydata_db_path = Path(tmpdir.name) / "my_data.db"
    metadata_path = Path(tmpdir.name) / "metadata.json"

    internal_db = sqlite3.connect(internal_db_path)
    internal_db.executescript(SCHEMA)
    internal_db.executescript(INTERNAL_FIXTURES_SQL)
    internal_db.close()

    mydata_db = sqlite3.connect(mydata_db_path)
    mydata_db.executescript(FIXTURES_SQL)
    mydata_db.close()

    (Path(tmpdir.name) / "plugin.py").write_text(PLUGIN_PY)
    metadata_path.write_text(json.dumps(METADATA))

    process = Popen(
        [
            executable,
            "-m",
            "datasette",
            "--port",
            "8123",
            str(mydata_db_path.absolute()),
            "--internal",
            str(internal_db_path.absolute()),
            "--plugins-dir",
            str(Path(tmpdir.name).absolute()),
            "--metadata",
            str(metadata_path.absolute()),
        ],
        stdout=PIPE,
    )
    wait_until_responds("http://localhost:8123/")
    yield "http://localhost:8123"

    process.terminate()
    process.wait()
    tmpdir.cleanup()


def wait_until_responds(url, timeout=5.0, **kwargs):
    start = time.time()
    while time.time() - start < timeout:
        try:
            httpx.get(url, **kwargs)
            return
        except httpx.ConnectError:
            time.sleep(0.1)
    raise AssertionError("Timed out waiting for {} to respond".format(url))


@pytest_asyncio.fixture
async def datasette_with_plugin():
    actors = {
        "1": {
            "id": "1",
            "username": "asg017",
            "name": "Alex Garcia",
            "email": "alexsebastian.garcia@example.com",
        },
        "2": {
            "id": "2",
            "username": "simonw",
            "name": "Simon Willison",
            "email": "swillison@example.com",
        },
    }

    class TestPlugin:
        __name__ = "TestPlugin"

        @hookimpl
        def datasette_comments_users(self):
            async def inner():
                return list(actors.values())

            return inner

    pm.register(TestPlugin(), name="undo")
    try:
        yield Datasette(
            memory=True,
            metadata={"permissions": {"datasette-comments-access": {"id": ["alex"]}}},
            pdb=True,
        )
    finally:
        pm.unregister(name="undo")
