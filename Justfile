default: frontend test

# Type generation
types-routes:
  uv run python -c 'from datasette_comments.router import router; import json;print(json.dumps(router.openapi_document_json()))' \
    | npx --prefix datasette_comments/frontend openapi-typescript > datasette_comments/frontend/src/generated/api.d.ts

types-pagedata:
  uv run python -c "exec(open('scripts/typegen-pagedata.py').read())"
  for f in datasette_comments/frontend/src/page_data/*_schema.json; do \
    npx --prefix datasette_comments/frontend json2ts "$f" > "${f%_schema.json}.types.ts"; \
  done

types:
  just types-routes
  just types-pagedata

# Frontend building
frontend:
  cd datasette_comments/frontend && [ -d node_modules ] || npm install
  cd datasette_comments/frontend && npx vite build

frontend-dev:
  cd datasette_comments/frontend && npx vite --port 5179

# Development servers
dev *flags:
  DATASETTE_SECRET=abc123 \
    uv run \
      --with datasette-debug-gotham \
      --with datasette-sidebar \
      datasette \
      --plugins-dir examples \
      -s permissions.datasette-comments-access.id '*' \
      -s permissions.datasette-sidebar-access.id '*' \
      -s permissions.profile_access.id '*' \
      --internal internal.db \
      legislators.db fixtures.db internal.db big.db \
      {{flags}}

dev-with-hmr *flags:
  DATASETTE_COMMENTS_VITE_DEV=http://localhost:5179/ \
  watchexec \
    --stop-signal SIGKILL \
    -e py,html \
    --ignore '*.db' \
    --restart \
    --clear -- \
    just dev {{flags}}

test *options:
  uv run python -m pytest {{options}}

format:
  black .
