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


def make_datasette(**extra_permissions):
    permissions = {"datasette-comments-access": {"id": ["alex"]}}
    permissions.update(extra_permissions)
    return Datasette(memory=True, config={"permissions": permissions})


@pytest.mark.asyncio
async def test_permissions():
    datasette = make_datasette()

    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "foo", "comment": "lol #yo"},
        cookies=cookie_for_actor(datasette, "alex"),
    )
    assert response.status_code == 200

    thread_id = response.json()["thread_id"]
    assert ULID.from_str(thread_id.upper()) is not None

    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "foo", "comment": "lol #yo"},
        cookies=cookie_for_actor(datasette, "unknown"),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_readonly_permissions():
    datasette = make_datasette(**{"datasette-comments-readonly": {"id": ["readonly"]}})

    # datasette-comments-access users can create threads
    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "foo", "comment": "lol #yo"},
        cookies=cookie_for_actor(datasette, "alex"),
    )
    assert response.status_code == 200

    thread_id = response.json()["thread_id"]
    assert ULID.from_str(thread_id.upper()) is not None

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
                        "name": "1",
                        "profile_photo_url": None,
                        "username": "1",
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
                        "name": "2",
                        "profile_photo_url": None,
                        "username": "2",
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


# --- New tests for expanded API coverage ---


@pytest.mark.asyncio
async def test_thread_new_database():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "mydb", "comment": "db comment"},
        cookies=cookies,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert ULID.from_str(data["thread_id"].upper()) is not None


@pytest.mark.asyncio
async def test_thread_new_table():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={
            "type": "table",
            "database": "mydb",
            "table": "mytable",
            "comment": "table comment",
        },
        cookies=cookies,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


@pytest.mark.asyncio
async def test_thread_new_row():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={
            "type": "row",
            "database": "mydb",
            "table": "mytable",
            "rowids": "1",
            "comment": "row comment",
        },
        cookies=cookies,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


@pytest.mark.asyncio
async def test_thread_comments_roundtrip():
    """Create a thread, add a comment, retrieve both."""
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    # Create thread
    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={
            "type": "database",
            "database": "testdb",
            "comment": "first comment #hello @someone",
        },
        cookies=cookies,
    )
    assert response.status_code == 200
    thread_id = response.json()["thread_id"]

    # Add a second comment
    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/comment/add",
        json={"thread_id": thread_id, "contents": "second comment"},
        cookies=cookies,
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # Retrieve comments
    response = await datasette.client.get(
        f"/-/datasette-comments/api/thread/comments/{thread_id}",
        cookies=cookies,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["data"]) == 2
    assert data["data"][0]["contents"] == "first comment #hello @someone"
    assert data["data"][1]["contents"] == "second comment"
    # Check render_nodes exist
    assert len(data["data"][0]["render_nodes"]) > 0
    # Check author is populated
    assert data["data"][0]["author"]["actor_id"] == "alex"


@pytest.mark.asyncio
async def test_thread_mark_resolved():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    # Create thread
    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "testdb", "comment": "resolve me"},
        cookies=cookies,
    )
    thread_id = response.json()["thread_id"]

    # Resolve it
    response = await datasette.client.post(
        "/-/datasette-comments/api/threads/mark_resolved",
        json={"thread_id": thread_id},
        cookies=cookies,
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.asyncio
async def test_reaction_add_and_remove():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    # Create thread to get a comment_id
    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "database": "testdb", "comment": "react to me"},
        cookies=cookies,
    )
    thread_id = response.json()["thread_id"]

    # Get comment ID
    response = await datasette.client.get(
        f"/-/datasette-comments/api/thread/comments/{thread_id}",
        cookies=cookies,
    )
    comment_id = response.json()["data"][0]["id"]

    # Add reaction
    response = await datasette.client.post(
        "/-/datasette-comments/api/reaction/add",
        json={"comment_id": comment_id, "reaction": "👍"},
        cookies=cookies,
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # Get reactions
    response = await datasette.client.get(
        f"/-/datasette-comments/api/reactions/{comment_id}",
        cookies=cookies,
    )
    assert response.status_code == 200
    reactions = response.json()
    assert len(reactions) == 1
    assert reactions[0]["reaction"] == "👍"
    assert reactions[0]["reactor_actor_id"] == "alex"

    # Remove reaction
    response = await datasette.client.post(
        "/-/datasette-comments/api/reaction/remove",
        json={"comment_id": comment_id, "reaction": "👍"},
        cookies=cookies,
    )
    assert response.status_code == 200

    # Verify removed
    response = await datasette.client.get(
        f"/-/datasette-comments/api/reactions/{comment_id}",
        cookies=cookies,
    )
    assert response.json() == []


@pytest.mark.asyncio
async def test_table_view_threads():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    # Create a row thread
    await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={
            "type": "row",
            "database": "mydb",
            "table": "mytable",
            "rowids": "1",
            "comment": "row 1 comment",
        },
        cookies=cookies,
    )

    # Query table view threads
    response = await datasette.client.post(
        "/-/datasette-comments/api/threads/table_view",
        json={
            "database": "mydb",
            "table": "mytable",
            "rowids": ["1"],
        },
        cookies=cookies,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["data"]["row_threads"]) == 1


@pytest.mark.asyncio
async def test_row_view_threads():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    # Create a row thread
    await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={
            "type": "row",
            "database": "mydb",
            "table": "mytable",
            "rowids": "42",
            "comment": "row 42 comment",
        },
        cookies=cookies,
    )

    # Query row view threads
    response = await datasette.client.post(
        "/-/datasette-comments/api/threads/row_view",
        json={
            "database": "mydb",
            "table": "mytable",
            "rowids": "42",
        },
        cookies=cookies,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["data"]["row_threads"]) == 1


@pytest.mark.asyncio
async def test_activity_search_basic():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    # Create a thread with a tag
    await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={
            "type": "database",
            "database": "testdb",
            "comment": "searchable comment #urgent",
        },
        cookies=cookies,
    )

    # Search all
    response = await datasette.client.get(
        "/-/datasette-comments/api/activity_search",
        cookies=cookies,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 1

    # Search by tag
    response = await datasette.client.get(
        "/-/datasette-comments/api/activity_search?containsTag=urgent",
        cookies=cookies,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 1
    assert "urgent" in data["data"][0]["contents"]


@pytest.mark.asyncio
async def test_thread_new_invalid_type():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "invalid_type", "database": "foo", "comment": "test"},
        cookies=cookies,
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_thread_new_missing_database():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    response = await datasette.client.post(
        "/-/datasette-comments/api/thread/new",
        json={"type": "database", "comment": "test"},
        cookies=cookies,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_activity_page():
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    response = await datasette.client.get(
        "/-/datasette-comments/activity",
        cookies=cookies,
    )
    assert response.status_code == 200
    assert "Comments" in response.text


@pytest.mark.asyncio
async def test_content_script_injection():
    """Test that extra_body_script returns valid JSON for authorized users."""
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    response = await datasette.client.get("/", cookies=cookies)
    assert response.status_code == 200
    assert "DATASETTE_COMMENTS_META" in response.text
    # Should include the vite-built content script JS
    assert "content_script" in response.text


@pytest.mark.asyncio
async def test_activity_page_vite_entry():
    """Test that the activity page uses vite_entry for its JS/CSS."""
    datasette = make_datasette()
    cookies = cookie_for_actor(datasette, "alex")

    response = await datasette.client.get(
        "/-/datasette-comments/activity",
        cookies=cookies,
    )
    assert response.status_code == 200
    # Should include vite-built activity JS
    assert "activity" in response.text
