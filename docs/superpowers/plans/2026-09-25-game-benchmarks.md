# Game evidence and React FPS implementation plan

Goal: Expand measured game coverage and persist reviewed observations plus clearly separate graphics predictions in the existing SQLite database.
Architecture: Keep native estimation and recommendations intact; ingest validated source rows transactionally, read the persisted snapshot with JSON fallback, and mount React disclosure islands beneath both FPS charts.
Tech stack: Python, SQLite, existing React 18 UMD, Playwright.
Spec: User requests in this conversation (game evidence, icons, expanded games, collapsed DLSS/FG).

- [x] Add isolated database persistence/revision tests, implement evidence and prediction tables.
- [x] Extend reviewed B2G table mapping and add verified chart observations; retain source conditions and reject changed/ambiguous charts.
- [x] Add seven games and official icons; refresh actual data and official NVIDIA feature support.
- [x] Keep hardware/game support guards, select closest measured rendering configuration; store calculated scenarios separately.
- [x] Add accessible React disclosure to AI and custom FPS, lifecycle cleanup, responsive layout.
- [x] Run Python/JS regression tests, desktop/mobile browser interactions and console checks; document actual coverage and limitations.
