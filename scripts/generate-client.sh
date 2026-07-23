#! /usr/bin/env bash

set -e
set -x

cd backend
uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../frontend/openapi.json
cd ..
bun run --filter frontend generate-client
bun scripts/normalize-generated-client-whitespace.mjs frontend/src/client
cd frontend
bunx biome ci --no-errors-on-unmatched --files-ignore-unknown=true src
