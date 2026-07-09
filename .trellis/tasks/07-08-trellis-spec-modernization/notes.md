# Notes

## 2026-07-09 Ant Design adoption pilot

- Implemented Ant Design as a gradual complex-component layer for the React frontend.
- Added `AntdProvider` under `frontend/src/app/providers/` and wrapped the app in `frontend/src/main.tsx`.
- Used `/rules` as the pilot page by moving the thick route implementation into `frontend/src/platform/docs/pages/RulesPage.tsx`; the route entry now stays thin.
- Added ADR `docs/adr/0001-use-ant-design-for-complex-admin-components.md`.
- Updated frontend Trellis specs with the Ant Design boundary, provider placement rule, and quality gate notes.
- Kept existing shadcn/ui flows intact and did not add `@ant-design/pro-components`; npm reports its peer range is `antd` `^4.24.15 || ^5.11.2`, not Ant Design 6.

Validation:

- `bun run build` from `frontend/` passed.
- Targeted Biome check for touched frontend files passed with no fixes.
- `git diff --check` passed.
- `npm ls antd --depth=0` reports `antd@6.5.0`.
- `bun install --lockfile-only` later succeeded and updated root `bun.lock`; the lockfile now includes `antd@6.5.0` and Ant Design dependencies.
- Read-only full Biome CI still fails on pre-existing repository issues: `biome.json` schema version mismatch and missing SVG titles under `frontend/public/assets/images/`.

## 2026-07-09 PM2 frontend dev startup fix

- Symptom: `pm2 start fsft-frontend-dev` repeatedly restarted and stopped with `SyntaxError: Unexpected token ':'` from `NPM.CMD:1`.
- Root cause: on Windows, PM2 resolved `script: "npm"` to `NPM.CMD` and used the default Node interpreter, so Node tried to parse the `.cmd` wrapper text (`:: Created by npm...`) as JavaScript.
- Fix: local `ecosystem.config.js` now starts the frontend through `cmd /c bun run dev --host 0.0.0.0` and sets `interpreter: "none"`; the backend entry also uses `interpreter: "none"` for the same binary-command reason.
- Validation: recreated `fsft-frontend-dev` with PM2; `pm2 describe` reports `script path = C:\WINDOWS\SYSTEM32\CMD.EXE`, `script args = /c bun run dev --host 0.0.0.0`, `interpreter = none`, `unstable restarts = 0`; `http://127.0.0.1:5173/` and `/rules` both returned 200.
