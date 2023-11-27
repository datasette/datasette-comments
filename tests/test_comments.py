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


@pytest.mark.asyncio
async def test_readonly_permissions():
    datasette = Datasette(
        memory=True,
        metadata={
            "permissions": {
                "datasette-comments-access": {"id": ["alex"]},
                "datasette-comments-readonly": {"id": ["readonly"]},
            }
        },
    )

    # datasette-comments-access users can create threads
    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "foo", "comment": "lol #yo"},
        cookies=cookie_for_actor(datasette, "alex"),
    )
    assert response.status_code == 200

    thread_id = response.json()["thread_id"]
    assert ULID.from_str(thread_id) is not None

    # readonly user cannot create a new thread
    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "foo", "comment": "lol #yo"},
        cookies=cookie_for_actor(datasette, "readonly"),
    )
    assert response.status_code == 403

    # access user can read a thread
    response = await datasette.client.get(
        f"/-/datasette-comments/api/thread/comments/{thread_id}",
        cookies=cookie_for_actor(datasette, "alex"),
    )
    assert response.status_code == 200

    # readonly user can read a thread
    response = await datasette.client.get(
        f"/-/datasette-comments/api/thread/comments/{thread_id}",
        cookies=cookie_for_actor(datasette, "readonly"),
    )
    assert response.status_code == 200

    # Non-access and non-readonly cant read threads
    response = await datasette.client.get(
        f"/-/datasette-comments/api/thread/comments/{thread_id}",
        cookies=cookie_for_actor(datasette, "unknown"),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prefix,expected",
    [
        (
            "a",
            [
                {
                    "username": "asg017",
                    "author": {
                        "actor_id": "1",
                        "name": None,
                        "profile_photo_url": None,
                        "username": None,
                    },
                }
            ],
        ),
        (
            "s",
            [
                {
                    "author": {
                        "actor_id": "2",
                        "name": None,
                        "profile_photo_url": None,
                        "username": None,
                    },
                    "username": "simonw",
                }
            ],
        ),
    ],
)
async def test_autocomplete_mentions(datasette_with_plugin, prefix, expected):
    assert not hasattr(datasette_with_plugin, "_datasette_comments_users_accessed")
    response = await datasette_with_plugin.client.get(
        "/-/datasette-comments/api/autocomplete/mentions?prefix={}".format(prefix),
        cookies=cookie_for_actor(datasette_with_plugin, "alex"),
    )
    assert datasette_with_plugin._datasette_comments_users_accessed
    assert response.status_code == 200
    data = response.json()
    assert data == {"suggestions": expected}
    delattr(datasette_with_plugin, "_datasette_comments_users_accessed")
