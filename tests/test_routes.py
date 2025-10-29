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


class TestApiTableViewThreads:
    """Test the api/threads/table_view endpoint"""

    @pytest.mark.asyncio
    async def test_method_not_post_returns_405(self, datasette_with_plugin):
        """Test that non-POST methods return 405"""
        response = await datasette_with_plugin.client.get(
            "/-/datasette-comments/api/threads/table_view",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_retrieve_table_threads(self, datasette_with_plugin):
        """Test retrieving threads for a table view"""
        # Create a thread first
        thread_response = await datasette_with_plugin.client.post(
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
        assert thread_response.status_code == 200

        # Now retrieve threads for the table
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/threads/table_view",
            json={
                "database": "foo",
                "table": "bar",
                "rowids": ["1"],
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "data" in data

    @pytest.mark.asyncio
    async def test_permissions(self, datasette_with_plugin):
        """Test that viewing threads without permission returns 403"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/threads/table_view",
            json={
                "database": "foo",
                "table": "bar",
                "rowids": ["1"],
            },
            cookies=cookie_for_actor(datasette_with_plugin, "bob"),
        )
        assert response.status_code == 403


class TestApiRowViewThreads:
    """Test the api/threads/row_view endpoint"""

    @pytest.mark.asyncio
    async def test_method_not_post_returns_405(self, datasette_with_plugin):
        """Test that non-POST methods return 405"""
        response = await datasette_with_plugin.client.get(
            "/-/datasette-comments/api/threads/row_view",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_retrieve_row_threads(self, datasette_with_plugin):
        """Test retrieving threads for a row view"""
        # Create a thread first
        thread_response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Test comment on row",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert thread_response.status_code == 200

        # Now retrieve threads for that specific row
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/threads/row_view",
            json={
                "database": "foo",
                "table": "bar",
                "rowids": "1",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "data" in data
        assert "row_threads" in data["data"]

    @pytest.mark.asyncio
    async def test_permissions(self, datasette_with_plugin):
        """Test that viewing threads without permission returns 403"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/threads/row_view",
            json={
                "database": "foo",
                "table": "bar",
                "rowids": "1",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "bob"),
        )
        assert response.status_code == 403


class TestApiCommentReactions:
    """Test the api/reactions/<comment_id> endpoint"""

    @pytest.mark.asyncio
    async def test_get_reactions_for_comment(self, datasette_with_plugin):
        """Test retrieving reactions for a specific comment"""
        # First create a thread with a comment
        thread_response = await datasette_with_plugin.client.post(
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
        assert thread_response.status_code == 200
        thread_id = thread_response.json()["thread_id"]

        # Get the comment ID from the thread
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert comments_response.status_code == 200
        comments = comments_response.json()["comments"]
        assert len(comments) > 0
        comment_id = comments[0]["id"]

        # Add a reaction to the comment
        await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": comment_id,
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )

        # Now retrieve reactions for that comment
        response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/reactions/{comment_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "reactions" in data
        assert len(data["reactions"]) == 1
        assert data["reactions"][0]["reaction"] == "👍"
        assert data["reactions"][0]["reactor_actor_id"] == "alex"

    @pytest.mark.asyncio
    async def test_get_reactions_empty_list(self, datasette_with_plugin):
        """Test retrieving reactions for a comment with no reactions"""
        # Create a thread with a comment
        thread_response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/thread/new",
            json={
                "type": "row",
                "database": "foo",
                "table": "bar",
                "rowids": "1",
                "comment": "Test comment without reactions",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        thread_id = thread_response.json()["thread_id"]

        # Get the comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]

        # Get reactions (should be empty)
        response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/reactions/{comment_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "reactions" in data
        assert len(data["reactions"]) == 0

    @pytest.mark.asyncio
    async def test_get_reactions_multiple_reactions(self, datasette_with_plugin):
        """Test retrieving multiple reactions on a comment"""
        # Create a thread
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]

        # Get comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]

        # Add multiple reactions
        reactions_to_add = ["👍", "❤️", "🎉"]
        for reaction in reactions_to_add:
            await datasette_with_plugin.client.post(
                "/-/datasette-comments/api/reaction/add",
                json={
                    "comment_id": comment_id,
                    "reaction": reaction,
                },
                cookies=cookie_for_actor(datasette_with_plugin, "alex"),
            )

        # Get all reactions
        response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/reactions/{comment_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert len(data["reactions"]) == 3
        reaction_emojis = [r["reaction"] for r in data["reactions"]]
        assert set(reaction_emojis) == set(reactions_to_add)

    @pytest.mark.asyncio
    async def test_get_reactions_nonexistent_comment(self, datasette_with_plugin):
        """Test retrieving reactions for a non-existent comment"""
        response = await datasette_with_plugin.client.get(
            "/-/datasette-comments/api/reactions/nonexistent_comment_id",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert len(data["reactions"]) == 0

    @pytest.mark.asyncio
    async def test_response_structure(self, datasette_with_plugin):
        """Test that the response has the correct structure"""
        # Create a thread and add a reaction
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]

        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]

        await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": comment_id,
                "reaction": "🔥",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )

        # Get reactions and validate structure
        response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/reactions/{comment_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        assert "ok" in data
        assert data["ok"] is True
        assert "reactions" in data
        assert isinstance(data["reactions"], list)
        
        if len(data["reactions"]) > 0:
            reaction = data["reactions"][0]
            assert "reactor_actor_id" in reaction
            assert "reaction" in reaction
            assert isinstance(reaction["reactor_actor_id"], str)
            assert isinstance(reaction["reaction"], str)


class TestApiReactionAdd:
    """Test the api/reaction/add endpoint"""

    @pytest.mark.asyncio
    async def test_method_not_post_returns_405(self, datasette_with_plugin):
        """Test that non-POST methods return 405"""
        response = await datasette_with_plugin.client.get(
            "/-/datasette-comments/api/reaction/add",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_add_reaction_to_comment(self, datasette_with_plugin):
        """Test adding a reaction to a comment"""
        # Create a thread and get comment_id
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]
        
        # Get the comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]
        
        # Add a reaction
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": comment_id,
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    @pytest.mark.asyncio
    async def test_missing_comment_id_returns_400(self, datasette_with_plugin):
        """Test that missing comment_id field returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_reaction_returns_400(self, datasette_with_plugin):
        """Test that missing reaction field returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": "some_comment_id",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, datasette_with_plugin):
        """Test that invalid JSON returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            content="not valid json",
            headers={"Content-Type": "application/json"},
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_multiple_reactions_same_comment(self, datasette_with_plugin):
        """Test adding multiple reactions to the same comment"""
        # Create a thread and get comment_id
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]
        
        # Get the comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]
        
        # Add first reaction
        response1 = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": comment_id,
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response1.status_code == 200
        
        # Add second reaction
        response2 = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": comment_id,
                "reaction": "❤️",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response2.status_code == 200
        
        # Verify both reactions exist
        reactions_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/reactions/{comment_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        data = reactions_response.json()
        assert len(data["reactions"]) == 2

    @pytest.mark.asyncio
    async def test_response_structure(self, datasette_with_plugin):
        """Test that the response has the correct structure"""
        # Create a thread and get comment_id
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]
        
        # Get the comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]
        
        # Add a reaction
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": comment_id,
                "reaction": "🎉",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate with Pydantic model
        from datasette_comments.contract import ApiReactionAddResponse
        validated = ApiReactionAddResponse.model_validate(data)
        assert validated.ok is True

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, datasette_with_plugin):
        """Test that unauthenticated requests return 401"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": "some_comment_id",
                "reaction": "👍",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_emoji_reactions(self, datasette_with_plugin):
        """Test adding various emoji reactions"""
        # Create a thread and get comment_id
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]
        
        # Get the comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]
        
        # Test various emoji reactions
        emojis = ["👍", "👎", "❤️", "🎉", "😄", "🚀"]
        for emoji in emojis:
            response = await datasette_with_plugin.client.post(
                "/-/datasette-comments/api/reaction/add",
                json={
                    "comment_id": comment_id,
                    "reaction": emoji,
                },
                cookies=cookie_for_actor(datasette_with_plugin, "alex"),
            )
            assert response.status_code == 200
        
        # Verify all reactions exist
        reactions_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/reactions/{comment_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        data = reactions_response.json()
        assert len(data["reactions"]) == len(emojis)
        reaction_set = {r["reaction"] for r in data["reactions"]}
        assert reaction_set == set(emojis)


class TestApiReactionRemove:
    """Test the api/reaction/remove endpoint"""

    @pytest.mark.asyncio
    async def test_method_not_post_returns_405(self, datasette_with_plugin):
        """Test that non-POST methods return 405"""
        response = await datasette_with_plugin.client.get(
            "/-/datasette-comments/api/reaction/remove",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_remove_reaction_from_comment(self, datasette_with_plugin):
        """Test removing a reaction from a comment"""
        # Create a thread and get comment_id
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]
        
        # Get the comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]
        
        # Add a reaction
        await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": comment_id,
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        
        # Remove the reaction
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/remove",
            json={
                "comment_id": comment_id,
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        # Verify reaction was removed
        reactions_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/reactions/{comment_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert len(reactions_response.json()["reactions"]) == 0

    @pytest.mark.asyncio
    async def test_missing_comment_id_returns_400(self, datasette_with_plugin):
        """Test that missing comment_id field returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/remove",
            json={
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_reaction_returns_400(self, datasette_with_plugin):
        """Test that missing reaction field returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/remove",
            json={
                "comment_id": "some_comment_id",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, datasette_with_plugin):
        """Test that invalid JSON returns 400"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/remove",
            content="not valid json",
            headers={"Content-Type": "application/json"},
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, datasette_with_plugin):
        """Test that unauthenticated requests return 401"""
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/remove",
            json={
                "comment_id": "some_comment_id",
                "reaction": "👍",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_remove_nonexistent_reaction(self, datasette_with_plugin):
        """Test removing a reaction that doesn't exist (should succeed silently)"""
        # Create a thread and get comment_id
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]
        
        # Get the comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]
        
        # Try to remove a reaction that was never added
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/remove",
            json={
                "comment_id": comment_id,
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_response_structure(self, datasette_with_plugin):
        """Test that the response has the correct structure"""
        # Create a thread and get comment_id
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]
        
        # Get the comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]
        
        # Add and then remove a reaction
        await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={
                "comment_id": comment_id,
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/remove",
            json={
                "comment_id": comment_id,
                "reaction": "👍",
            },
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate with Pydantic model
        from datasette_comments.contract import ApiReactionRemoveResponse
        validated = ApiReactionRemoveResponse.model_validate(data)
        assert validated.ok is True

    @pytest.mark.asyncio
    async def test_remove_one_of_multiple_reactions(self, datasette_with_plugin):
        """Test removing one reaction when multiple exist"""
        # Create a thread and get comment_id
        thread_response = await datasette_with_plugin.client.post(
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
        thread_id = thread_response.json()["thread_id"]
        
        # Get the comment ID
        comments_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/thread/comments/{thread_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        comment_id = comments_response.json()["comments"][0]["id"]
        
        # Add multiple reactions
        await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={"comment_id": comment_id, "reaction": "👍"},
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/add",
            json={"comment_id": comment_id, "reaction": "❤️"},
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        
        # Remove one reaction
        response = await datasette_with_plugin.client.post(
            "/-/datasette-comments/api/reaction/remove",
            json={"comment_id": comment_id, "reaction": "👍"},
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        assert response.status_code == 200
        
        # Verify the other reaction still exists
        reactions_response = await datasette_with_plugin.client.get(
            f"/-/datasette-comments/api/reactions/{comment_id}",
            cookies=cookie_for_actor(datasette_with_plugin, "alex"),
        )
        reactions_data = reactions_response.json()
        assert len(reactions_data["reactions"]) == 1
        assert reactions_data["reactions"][0]["reaction"] == "❤️"