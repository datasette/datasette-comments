# Plan: datasette-comments as Shared Comments Infrastructure

## Context

datasette-kanban and datasette-town both need comments on their own resources (tickets, queries), with their own permission models. Rather than each plugin reimplementing comments, datasette-comments becomes shared infrastructure: one set of tables, one API, reusable web components, with permission checks delegated back to the owning plugin.

## Architecture Overview

```
datasette-comments (shared infra)
  ├── Storage: internal db tables (threads, comments, reactions)
  ├── API: /-/datasette-comments/api/*
  ├── Web components: <datasette-comment-thread>
  ├── Hookspec: datasette_comments_target_providers
  └── Permission delegation: provider.check_permission()

datasette-kanban (consumer)
  ├── Implements: KanbanTicketCommentProvider (target_type="kanban-ticket")
  ├── Embeds: <datasette-comment-thread target-type="kanban-ticket" target-id="42">
  └── Removes: own comment/reaction tables, routes, components

datasette-town (consumer)
  ├── Implements: TownQueryCommentProvider (target_type="town-query")
  └── Embeds: <datasette-comment-thread target-type="town-query" target-id="abc123">
```

## 1. Schema Change (datasette-comments)

**File:** `datasette_comments/internal_migrations.py`

Add migration: `ALTER TABLE datasette_comments_threads ADD COLUMN target_id TEXT`
Add index on `(target_type, target_id)`.

Existing `target_type` column already holds strings like "database", "table", "row". It now also accepts plugin-defined values like "kanban-ticket", "town-query". The new `target_id` column holds an opaque string identifier. For plugin targets, the existing `target_database/table/row_ids/column` columns are NULL.

## 2. CommentTargetProvider Protocol + Hookspec

**New file:** `datasette_comments/providers.py`

```python
class CommentTargetProvider(Protocol):
    target_type: str  # "kanban-ticket", "town-query", etc.

    async def check_permission(self, datasette, actor, target_id, action) -> bool:
        """action is "read" or "write"."""

    async def get_mentionable_users(self, datasette, target_id, prefix) -> list[dict] | None:
        """Return mentionable users for this target, or None for global fallback."""

    async def get_target_label(self, datasette, target_id) -> str | None:
        """Human-readable label for activity feeds."""

    async def get_target_url(self, datasette, target_id) -> str | None:
        """URL path for linking to the target."""

    single_thread: bool  # True = one flat thread per target, False = multiple threads allowed
```

**File:** `datasette_comments/hookspecs.py` -- add:

```python
@hookspec
def datasette_comments_target_providers(datasette):
    """Return list of CommentTargetProvider instances."""
```

**File:** `datasette_comments/__init__.py` -- collect providers at startup into a `{target_type: provider}` registry.

## 3. Permission Delegation

**File:** `datasette_comments/router.py`

Refactor `check_permission` to be target-aware:
- For built-in targets (database/table/row/etc): use existing `datasette-comments-access` / `datasette-comments-readonly` actions
- For plugin targets: look up provider by `target_type`, call `provider.check_permission()`
- Routes that receive `thread_id` or `comment_id` look up the thread's target first

## 4. API Changes

**File:** `datasette_comments/routes/api.py`

- **`thread_new`**: Accept `target_id` in request body for plugin targets
- **New `threads_by_target`**: `POST /threads/by_target` with `{target_type, target_id}` -- generic replacement for table_view/row_view for plugin targets
- **`autocomplete_mentions`**: Accept optional `target_type` + `target_id` params, delegate to provider's `get_mentionable_users()`
- **`activity_search`**: For plugin targets, call provider's `get_target_label()` + `get_target_url()` instead of resolving database/table/row labels

## 5. Web Component

**New file:** `datasette_comments/frontend/src/web_components/comment_thread.tsx`

Wraps existing `Thread` Preact component as `<datasette-comment-thread>` using `preact-custom-element` (already a dependency, already used for `<profile-comments>`).

**Attributes:**
| Attribute | Required | Description |
|-----------|----------|-------------|
| `target-type` | yes | e.g. "kanban-ticket", "town-query" |
| `target-id` | yes | opaque identifier |
| `author-json` | yes | JSON Actor for current user |
| `readonly` | no | hides write UI |
| `single-thread` | no | collapses to one thread (for kanban-style flat comments) |

**Events:** `thread-created`, `thread-resolved`, `comment-added`

**New Vite entry** in `frontend/vite.config.ts`:
```
comment_thread: "src/web_components/comment_thread.tsx"
```

**CSS/JS delivery:** datasette-comments exposes a Python helper that consuming plugins call to get the vite entry HTML for this bundle.

## 6. Kanban Integration

**File:** `datasette_kanban/__init__.py`
- Add `datasette-comments` as dependency
- Implement `datasette_comments_target_providers` hook returning `KanbanTicketCommentProvider`
- Provider maps ticket_id -> board_id, checks `kanban-edit-board` (write) / `kanban-view-board` (read)

**File:** `frontend/src/pages/ticket_detail/TicketDetailPage.svelte`
- Replace `CommentItem.svelte` + comment form with `<datasette-comment-thread target-type="kanban-ticket" target-id={ticketId}>`

**Remove:**
- `datasette_kanban_comments` + `datasette_kanban_reactions` tables (after migration)
- `routes/api_comments.py`, `routes/api_reactions.py`
- `CommentItem.svelte`
- Comment/reaction methods from `internal_db.py`

**Data migration:** Kanban migration that copies existing comments/reactions into shared tables with `target_type="kanban-ticket"`.

## 7. Town Integration

**File:** `datasette_town/__init__.py`
- Add `datasette-comments` as dependency
- Implement `datasette_comments_target_providers` hook returning `TownQueryCommentProvider`
- Provider checks `datasette-town-view` (read) / `datasette-town-edit` (write)

**File:** `frontend/src/pages/query_detail/QueryDetailPage.svelte`
- Add `<datasette-comment-thread target-type="town-query" target-id={queryId}>`

## 8. Town Permissions Improvement

Town's current `permission_resources_sql` approach (SQL UNIONs for owner/shared/public) is actually the correct pattern per datasette core's current API. The "hackiness" is minor -- the `can_edit` flag in shares is a pragmatic shortcut. The main improvement would be:
- Extract the permission SQL into a dedicated module (currently inline in `__init__.py`)
- Use datasette's `also_requires` chain more explicitly so view->edit->manage cascading is clearer
- For comment permissions: `town-view` gates reading comments, `town-edit` gates writing comments -- this maps cleanly

## Implementation Order

1. **datasette-comments core** (no breaking changes): schema migration, provider protocol, hookspec, registry, refactored permission checks, new API endpoints
2. **Web component**: new Preact custom element, vite entry, CSS/JS helper
3. **Kanban integration**: provider, migration, swap frontend
4. **Town integration**: provider, add frontend

## Resolved Decisions

- **Comment format**: Keep simple text + @mentions/#tags/URLs. No markdown. Kanban's existing markdown comments get stored as plain text (the markup will show as-is, which is fine).
- **Threading model**: Provider decides. The provider protocol includes a `single_thread: bool` property. When `True`, the web component creates/shows one thread per target. When `False` (default), multiple threads are allowed. Kanban and town use `single_thread=True`. Datasette-native targets keep multi-thread behavior.

## Verification

- Run `just test` in datasette-comments after core changes
- Verify existing content_script injection still works on table/row pages
- Test web component in isolation with a test HTML page
- Run `just test` in datasette-kanban after integration
- Manually verify: create kanban ticket, leave comment via web component, check permissions with different actors
- Run `just test` in datasette-town after integration
