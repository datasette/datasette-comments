frontend:
  cd datasette_comments/frontend && npx vite build

frontend-dev:
  cd datasette_comments/frontend && npx vite --port 5179

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
