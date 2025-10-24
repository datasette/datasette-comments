import pytest
from datasette_comments.contract import ApiThreadNewResponse


def cookie_for_actor(datasette, actor_id):
    return {"ds_actor": datasette.sign({"a": {"id": actor_id}}, "actor")}


@pytest.mark.asyncio
async def test_routes_thread_comments(datasette_with_plugin):
    print(datasette_with_plugin.databases)
    response = await datasette_with_plugin.client.post(
        "/-/datasette-comments/api/thread/new",
        json={
            "type": "row",
            "database": "foo",
            "table": "bar",
            "rowids": "1",
            "comment": "lol #yo",
        },
        cookies=cookie_for_actor(datasette_with_plugin, "alex"),
    )
    assert response.status_code == 200
    assert ApiThreadNewResponse.model_validate(response.json())

    thread_id = response.json()["thread_id"]
    response = await datasette_with_plugin.client.get(
        "/-/datasette-comments/api/thread/comments/" + thread_id,
        cookies=cookie_for_actor(datasette_with_plugin, "alex"),
    )
    # TODO


class TestApiThreadNew:
    """Test the api/thread/new endpoint"""

    @pytest.mark.asyncio
    async def test_method_not_post_returns_405(self, datasette_with_plugin):
        """Test that non-POST methods return 405"""
        response = await datasette_with_plugin.client.get(
            "/-/datasette-comments/api/thread/new",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_row_type_valid(self, datasette_with_plugin):
        """Test creating a thread on a row"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Row comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "thread_id" in data

    @pytest.mark.asyncio
    async def test_row_type_compound_primary_key(self, datasette_with_plugin):
        """Test creating a thread on a row with compound primary key"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1,abc~2Fdef",
                "comment": "Compound key row comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    @pytest.mark.asyncio
    async def test_row_type_missing_rowids(self, datasette_with_plugin):
        """Test row type without rowids field returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "comment": "Comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400
        # Pydantic returns "Field required" error which gets mapped
        assert response.json()["message"]

    @pytest.mark.asyncio
    async def test_missing_comment_field(self, datasette_with_plugin):
        """Test that missing comment field returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={"type": "row", "database": "foo", "table": "bar", "rowids": "1"},
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_type_field(self, datasette_with_plugin):
        """Test that missing type field returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_extra_fields_ignored(self, datasette_with_plugin):
        """Test that extra fields are ignored and don't cause errors"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Comment",
                "extra_field": "should be ignored",
                "another_extra": 123,
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    @pytest.mark.asyncio
    async def test_comment_with_hashtags(self, datasette_with_plugin):
        """Test creating a thread with hashtags in the comment"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "This is a comment with #hashtag and #another_tag",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    @pytest.mark.asyncio
    async def test_comment_with_mentions(self, datasette_with_plugin):
        """Test creating a thread with mentions in the comment"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Hey @alice and @bob, check this out!",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    @pytest.mark.asyncio
    async def test_response_structure(self, datasette_with_plugin):
        """Test that the response has the correct structure"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Test comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()

        # Validate with Pydantic model
        validated = ApiThreadNewResponse.model_validate(data)
        assert validated.ok is True
        assert isinstance(validated.thread_id, str)
        assert len(validated.thread_id) > 0


class TestApiCommentNew:
    """Test the api/thread/comment/add endpoint"""

    @pytest.mark.asyncio
    async def test_method_not_post_returns_405(self, datasette_with_plugin):
        """Test that non-POST methods return 405"""
        response = await datasette_with_plugin.client.get(
            "/-/datasette-comments/api/thread/comment/add",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_add_comment_to_existing_thread(self, datasette_with_plugin):
        """Test adding a comment to an existing thread"""
        # First create a thread
        thread_response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Initial comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert thread_response.status_code == 200
        thread_id = thread_response.json()["thread_id"]

        # Now add a comment to that thread
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/comment/add",
            json={
                "thread_id": thread_id,
                "contents": "This is a follow-up comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    @pytest.mark.asyncio
    async def test_permissions(self, datasette_with_plugin):
        """Test that adding a comment without permission returns 403"""
        # Create a thread as alex
        thread_response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Initial comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        thread_id = thread_response.json()["thread_id"]

        # Try to add a comment as bob who lacks permission
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/comment/add",
            json={
                "thread_id": thread_id,
                "contents": "I should not be allowed to comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "bob"),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_thread_id_returns_400(self, datasette_with_plugin):
        """Test that missing thread_id field returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/comment/add",
            json={"contents": "Comment without thread_id"},
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_contents_returns_400(self, datasette_with_plugin):
        """Test that missing contents field returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/comment/add",
            json={"thread_id": "some_thread_id"},
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, datasette_with_plugin):
        """Test that invalid JSON returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/comment/add",
            content="not valid json",
            headers={"Content-Type": "application/json"},
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_multiple_comments_on_same_thread(self, datasette_with_plugin):
        """Test adding multiple comments to the same thread"""
        # Create a thread
        thread_response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Initial comment",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        thread_id = thread_response.json()["thread_id"]

        # Add first comment
        response1 = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/comment/add",
            json={
                "thread_id": thread_id,
                "contents": "First follow-up",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response1.status_code == 200
        assert response1.json()["ok"] is True

        # Add second comment
        response2 = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/comment/add",
            json={
                "thread_id": thread_id,
                "contents": "Second follow-up",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response2.status_code == 200
        assert response2.json()["ok"] is True
