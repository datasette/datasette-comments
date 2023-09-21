flags := ""

js:
  ./node_modules/.bin/esbuild \
    --bundle --minify --format=esm  --jsx-factory=h --jsx-fragment=Fragment {{flags}} \
    --out-extension:.js=.min.js \
    datasette_comments/frontend/targets/content_script.tsx \
    datasette_comments/frontend/targets/debug.tsx \
    --outdir=datasette_comments/static

dev:
  DATASETTE_SECRET=abc123 watchexec --signal SIGKILL --restart --clear -e py,ts,js,html,css,sql -- \
    python3 -m datasette --root legislators.db fixtures.db --plugins-dir=tests/basic_plugin/ --internal internal.db

test:
  pytest

format:
  black .
