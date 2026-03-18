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
  cd datasette_comments/frontend && npx vite build

frontend-dev:
  cd datasette_comments/frontend && npx vite --port 5179

# Development servers
dev:
  DATASETTE_COMMENTS_VITE_DEV=http://localhost:5179/ \
  DATASETTE_SECRET=abc123 watchexec --signal SIGKILL --restart --clear -e py,html,sql -- \
    uv run python -m datasette \
      --root \
      --plugins-dir=tests/basic_plugin/ \
      --metadata tests/basic_plugin/metadata.yaml \
      --internal internal.db \
      legislators.db fixtures.db internal.db big.db

dev-with-hmr:
  DATASETTE_COMMENTS_VITE_DEV=http://localhost:5179/ \
  DATASETTE_SECRET=abc123 watchexec --signal SIGKILL --restart --clear -e py,html,sql -- \
    uv run python -m datasette \
      --root \
      --plugins-dir=tests/basic_plugin/ \
      --metadata tests/basic_plugin/metadata.yaml \
      --internal internal.db \
      legislators.db fixtures.db internal.db big.db

test *options:
  uv run python -m pytest {{options}}

format:
  black .
