# Modernize datasette-comments to fullstack pattern

## Phase 1: Backend Restructuring
- [x] 1.1 Add dependencies to pyproject.toml
- [x] 1.2 Create page_data.py (Pydantic models)
- [x] 1.3 Create router.py
- [x] 1.4 Create internal_db.py
- [x] 1.5 Create routes/api.py
- [x] 1.6 Create routes/pages.py
- [x] 1.7 Slim down __init__.py
- [x] 1.8 Tests pass

## Phase 2: Vite Build System
- [x] 2.1 Restructure frontend/ directory
- [x] 2.2 Create vite.config.ts
- [x] 2.3 Create frontend/package.json
- [x] 2.4 Update activity_view.html template
- [x] 2.5 Update content script injection hooks
- [x] 2.6 Update Justfile
- [x] 2.7 Remove root-level package.json, tsconfig.json, old esbuild output

## Phase 3: Type Safety — API Pipeline
- [x] 3.1 Add OpenAPI spec generation
- [x] 3.2 Create typed openapi-fetch client
- [ ] 3.3 Replace hand-written Api class
- [ ] 3.4 Delete old lib/api.ts

## Phase 4: Type Safety — Page Data Pipeline
- [x] 4.1 Create scripts/typegen-pagedata.py
- [x] 4.2 Add Justfile recipe for page data types
- [x] 4.3 Create frontend/src/lib/page_data.ts
- [x] 4.4 Update frontend entry points to use typed page data
- [x] 4.5 Combined types recipe

## Phase 5: Improved Tests
- [ ] 5.1 Expand API test coverage
- [ ] 5.2 Update test fixtures
- [ ] 5.3 Verify content script injection
- [ ] 5.4 Keep Playwright tests for E2E
