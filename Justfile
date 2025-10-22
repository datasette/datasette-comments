flags := ""

js:
  ./node_modules/.bin/esbuild \
    --bundle --minify --format=esm  --jsx-factory=h --jsx-fragment=Fragment {{flags}} \
    --out-extension:.js=.min.js \
    --out-extension:.css=.min.css \
    datasette_comments/frontend/targets/**/index.tsx \
    --target=safari12 \
    --outdir=datasette_comments/static

dev2:
  DATASETTE_SECRET=abc123 \
    uv run \
      --with-editable ".[test]" \
      datasette -p 8005 \
      --root \
      --plugins-dir=tests/basic_plugin/ \
      --config tests/basic_plugin/metadata.yaml \
      --internal internal.db \
      tmp.db

dev-watch *options:
  DATASETTE_SECRET=abc123 \
  watchexec \
    --stop-signal SIGKILL \
    --ignore '*.db' \
    --ignore '*.db-journal' \
    --ignore '*.db-wal' \
    --restart \
    --clear -- \
      just dev2 {{options}}

dev:
  DATASETTE_SECRET=abc123 \
    uv run --with-editable ".[test]" datasette -p 8005 \
      --root \
      --plugins-dir=tests/basic_plugin/ \
      --config tests/basic_plugin/metadata.yaml \
      --internal internal.db \
      tmp.db
# watchexec --signal SIGKILL --clear -e py,ts,js,html,css,sql --
# legislators.db fixtures.db internal.db big.db

test:
  uv run \
    --with-editable '.[test]' \
    pytest

test-watch:
  watchexec \
    --stop-signal SIGKILL \
    --ignore '*.db' \
    --ignore '*.db-journal' \
    --ignore '*.db-wal' \
    --restart \
    --clear -- \
      just test

format:
  black .
