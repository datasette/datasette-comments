from datasette.app import Datasette
import pytest
from ulid import ULID


@pytest.mark.asyncio
async def test_plugin_is_installed():
    datasette = Datasette(memory=True)
    response = await datasette.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-comments" in installed_plugins


def cookie_for_actor(datasette, actor_id):
    return {"ds_actor": datasette.sign({"a": {"id": actor_id}}, "actor")}


@pytest.mark.asyncio
async def test_permissions():
    datasette = Datasette(
        memory=True,
        metadata={"permissions": {"datasette-comments-access": {"id": ["alex"]}}},
    )

    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "foo", "comment": "lol #yo"},
        cookies=cookie_for_actor(datasette, "alex"),
    )
    assert response.status_code == 200

    thread_id = response.json()["thread_id"]
    assert ULID.from_str(thread_id) is not None

    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "foo", "comment": "lol #yo"},
        cookies=cookie_for_actor(datasette, "unknown"),
    )
    assert response.status_code == 403
