flags := ""

js:
  ./node_modules/.bin/esbuild \
    --bundle --minify --format=esm  --jsx-factory=h --jsx-fragment=Fragment {{flags}} \
    --out-extension:.js=.min.js \
    --out-extension:.css=.min.css \
    datasette_comments/frontend/targets/**/index.tsx \
    --target=safari12 \
    --outdir=datasette_comments/static

dev:
  DATASETTE_SECRET=abc123 watchexec --signal SIGKILL --restart --clear -e py,ts,js,html,css,sql -- \
    python3 -m datasette \
      --root \
      --plugins-dir=tests/basic_plugin/ \
      --metadata tests/basic_plugin/metadata.yaml \
      --internal internal.db \
      legislators.db fixtures.db internal.db big.db

test:
  pytest

format:
  black .
