from playwright.sync_api import Page, expect
from datasette.app import Datasette
from subprocess import Popen, PIPE
from sys import executable
import time
import httpx
import pytest
from syrupy.extensions.image import PNGImageSnapshotExtension
from pathlib import Path
import tempfile
import sqlite3
from datasette_comments import SCHEMA

FIXTURES_SQL = (Path(__file__).parent / "comments-fixtures.sql").read_text()
INTERNAL_FIXTURES_SQL = (
    Path(__file__).parent / "comments-internal-fixtures.sql"
).read_text()
PLUGIN_PY = """
from datasette import hookimpl

actors = {
    "1": {
        "id": "1",
        "username": "asg017",
        "name": "Alex Garcia",
        "profile_picture_url": "https://avatars.githubusercontent.com/u/15178711?v=4",
    },
    "2": {
        "id": "2",
        "username": "simonw",
        "name": "Simon Willison",
        "profile_picture_url": "https://avatars.githubusercontent.com/u/9599?v=4",
    },
}


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


@pytest.fixture
def screenshot_snapshot(snapshot):
    return snapshot.use_extension(PNGImageSnapshotExtension)


@pytest.fixture
def ds_server(request):
    tmpdir = tempfile.TemporaryDirectory()
    internal_db_path = Path(tmpdir.name) / "internal.db"
    mydata_db_path = Path(tmpdir.name) / "my_data.db"

    internal_db = sqlite3.connect(internal_db_path)
    internal_db.executescript(SCHEMA)
    internal_db.executescript(INTERNAL_FIXTURES_SQL)
    internal_db.close()

    mydata_db = sqlite3.connect(mydata_db_path)
    mydata_db.executescript(FIXTURES_SQL)
    mydata_db.close()

    (Path(tmpdir.name) / "plugin.py").write_text(PLUGIN_PY)

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
        ],
        stdout=PIPE,
    )
    wait_until_responds("http://localhost:8123/")

    def destroy():
        process.terminate()
        process.wait()
        tmpdir.cleanup()

    request.addfinalizer(destroy)

    return "http://localhost:8123"


def test_initial_load(page: Page, screenshot_snapshot, ds_server):
    page.goto(f"{ds_server}/-/datasette-comments/tags/tag1")
    assert page.screenshot() == screenshot_snapshot()


def test_table_view(page: Page, screenshot_snapshot, ds_server):
    page.context.add_cookies(
        [
            {
                "name": "actor",
                "value": "2",
                "url": "http://localhost:8123",  # "domain": "", "path": "/"
            }
        ]
    )
    page.goto(f"{ds_server}/my_data/students")
    table = page.locator("table")
    assert table.screenshot() == screenshot_snapshot(name="table")

    aaa_id_td = page.locator("table tbody tr:nth-child(1) td:nth-child(1)")
    bbb_id_td = page.locator("table tbody tr:nth-child(2) td:nth-child(1)")

    # when a user hovers over a row with no comments, it should show the "comment" icon
    bbb_id_td_rect = bbb_id_td.bounding_box()
    page.mouse.move(bbb_id_td_rect["x"], bbb_id_td_rect["y"])
    assert table.screenshot() == screenshot_snapshot(name="table-hover-no-comment")

    aaa_id_td.click()

    assert page.screenshot() == screenshot_snapshot(name="table-row-comment-click")


def wait_until_responds(url, timeout=5.0, **kwargs):
    start = time.time()
    while time.time() - start < timeout:
        try:
            httpx.get(url, **kwargs)
            return
        except httpx.ConnectError:
            time.sleep(0.1)
    raise AssertionError("Timed out waiting for {} to respond".format(url))
