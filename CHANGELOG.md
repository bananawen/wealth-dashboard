# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Responsive UI redesign with Hermes-style blue theme.
- Dark/Light mode toggle with localStorage persistence.
- Area chart for portfolio history visualization.
- Stock scraper system for Taiwan and US markets.
- Admin monitoring page for database stats, scraper status, logs, and deployment status.
- Transaction form with stock autocomplete and calendar picker.
- Python logging system with FastAPI middleware.
- Frontend error interceptor and request logger.
- Conventional commits guidelines.

### Changed
- Updated `tailwind.config.js` with custom color theme.
- Improved mobile-first responsive layouts.
- Migrated portfolio history from line chart to area chart with gradient.

### Fixed
- iPhone/iPad responsive layout issues.
- Theme persistence across sessions.

## 2026-07-01

### Added
- Added `frontend/src/context/ThemeContext.test.tsx` to verify the theme menu can switch from dark to light without recursive failure.

### Changed
- Changed `frontend/src/context/ThemeContext.tsx` to alias the Redux `toggleTheme` action creator instead of shadowing it with a local callback name.
- Changed `frontend/src/test/setup.js` to provide a `window.matchMedia` mock for theme-related frontend tests.
- Rebuilt frontend production assets in `frontend/dist` after the theme toggle fix.

### Fixed
- Fixed the light-theme menu action doing nothing because `useTheme()` recursively called its own callback instead of dispatching the theme toggle action.

### Risk And Rollback
- Roll back by restoring the previous `frontend/src/context/ThemeContext.tsx` implementation and rebuilding the frontend bundle; the change is isolated to client-side theme switching.

### Next
- Verify the live LAN site switches immediately between light and dark themes on both desktop and iPhone.

## 2026-07-01

### Changed
- Changed `frontend/src/index.css` light-theme variables from pure white to a warm gray-white palette to reduce glare while keeping the existing finance-tool layout and blue accent.
- Rebuilt frontend production assets in `frontend/dist` after finalizing the warm gray-white light theme.

### Fixed
- Fixed the light theme feeling overly harsh on mobile by softening the background, panel, card, border, and text contrast in light mode.

### Risk And Rollback
- Roll back by restoring the previous `:root` color variables in `frontend/src/index.css` and rebuilding the frontend bundle; the change is isolated to light-theme presentation.

### Next
- Review the live light theme across `/overview`, `/holdings`, `/transactions`, and `/admin`, then fine-tune only local contrast if any specific panel still feels too bright.

## 2026-07-01

### Changed
- Changed `frontend/src/index.css` to add theme-level `panel`, `input`, and `card-shadow` variables for both light and dark modes.
- Changed the shared `.card`, `.card-hover`, `.state-panel`, and `.input-field` styles so cards separate more clearly from page backgrounds in both themes.
- Changed dark-mode secondary/background/card values to create more visible depth between the page canvas and data panels.
- Rebuilt frontend production assets in `frontend/dist` after the cross-theme card-depth update.

### Fixed
- Fixed weak card hierarchy in both light and dark themes by separating panel backgrounds, borders, and shadows more clearly from the base page background.

### Risk And Rollback
- Roll back by restoring the previous theme variables and shared component styles in `frontend/src/index.css`, then rebuild the frontend bundle; the change is isolated to presentation depth and contrast.

### Next
- Review the live site in both themes and only do page-specific contrast tuning if a particular screen still feels flat.

## 2026-07-01

### Changed
- Changed `frontend/src/pages/AdminPage.tsx` so the scraper tab grid, left control cards, and right data cards all opt into `min-w-0` shrinking behavior on mobile.
- Changed the scraper scheduler status badges to wrap instead of forcing one-line width on narrow screens.
- Changed the upcoming-job rows in the scraper tab so long job ids and trigger strings truncate or wrap instead of widening the card.
- Rebuilt frontend production assets in `frontend/dist` after the Admin scraper mobile overflow fix.

### Fixed
- Fixed horizontal overflow on the Admin scraper tab where card content width could exceed the iPhone viewport and push the page sideways.

### Risk And Rollback
- Roll back by restoring the previous `renderScraper()` layout classes in `frontend/src/pages/AdminPage.tsx`, then rebuild the frontend bundle; the change is isolated to Admin scraper mobile layout behavior.

### Next
- Recheck the live Admin scraper tab on iPhone and only tighten specific table/card sections further if any single block still overflows.

## 2026-06-30

### Added
- Added `backend/tests/test_portfolio_performance_fallback.py` to lock in portfolio-performance reconstruction when `portfolio_snapshots` is empty.

### Changed
- Changed `backend/app/services/portfolio_service.py` so `/portfolio/performance` can rebuild a historical net-value series from transaction history and stored price history when snapshots are missing.
- Changed the rebuilt series to keep today's endpoint anchored to `get_summary()` so the chart reflects the current portfolio value instead of stopping at the last stored market close.
- Changed `backend/app/main.py` to register the `/prices` router so frontend holding-detail charts can actually fetch local historical price series.
- Changed `frontend/src/components/StatusBar.tsx`, `frontend/src/components/DashboardLayout.tsx`, and `frontend/src/hooks/useDashboardState.ts` so shared dashboard chrome only calls `/api/admin/*` endpoints for admin users.
- Changed `frontend/src/components/dashboard/HoldingsSection.tsx` to fetch per-symbol local price history and draw the holding chart from daily historical closes through the current date instead of only plotting transaction dates.
- Changed `frontend/vite.config.js` to normalize `dist` permissions as part of the Vite build pipeline itself, reducing the chance of another nginx static-file `403` after direct builds.

### Fixed
- Fixed the overview net-value chart showing only a single "today" point for accounts that have transactions and price history but no `portfolio_snapshots` rows.
- Fixed holding-detail history requests returning `404 Not Found` because the backend had a `prices` router file but had never mounted it into the FastAPI app.
- Fixed repeated frontend `403` responses for non-admin users by skipping shared admin status/version queries outside the admin role.
- Fixed nginx `403 Forbidden` on `/` after a direct local build left `frontend/dist` unreadable to the web server; restored web-readable `755/644` permissions on deployed static files.
- Fixed the holdings detail chart so symbols with local price history now show a daily value curve instead of staying pinned to purchase dates only.
- Fixed the holdings detail chart state messaging by explicitly labeling when the UI has to fall back to transaction points because local price history is missing.

### Risk And Rollback
- Roll back by removing the fallback-history path in `backend/app/services/portfolio_service.py` and restarting the backend; existing snapshot-backed accounts are otherwise unaffected.

### Next
- Restart the backend service and verify `/overview` range switches (`week`, `month`, `year`, `all`) on the live LAN site.
- Keep using `npm run build` instead of invoking `vite build` directly so the permission-normalization step for `frontend/dist` always runs.

## 2026-06-29

### Added
- Added `asset_class` to transaction create/update/list flows, CSV/Excel import parsing, and admin transaction export so allocation data can be modeled separately from trading strategy categories.
- Added `backend/migrations/023_transactions_asset_class.sql` and backend test coverage for asset-class normalization/import parsing.
- Added `backend/scripts/asset_class_backfill.py` as a dry-run-first backfill utility for existing transactions with missing `asset_class`.
- Added `sector` to transaction create/update/list flows, CSV/Excel import parsing, and admin transaction export using a hybrid model for stock industries plus ETF-type labels.
- Added `backend/migrations/024_transactions_sector.sql` and `backend/scripts/sector_symbol_map.py` as the first maintainable base for sector tagging.

### Changed
- Changed `frontend/src/components/AddTransactionForm.tsx` to collect both transaction strategy category and asset class, and updated the import template/documentation accordingly.
- Changed `frontend/src/components/dashboard/HoldingsSection.tsx` to summarize holdings by asset class instead of repeating market and currency allocation views.
- Changed the holdings allocation area to show current allocation only; target allocation and deviation reminders are temporarily disabled pending a follow-up rules discussion.
- Changed `frontend/src/components/dashboard/TransactionsSection.tsx` to surface the selected asset class on transaction rows.
- Changed `backend/scripts/README.md` to document the new asset-class backfill workflow and safety model.
- Changed `frontend/src/components/AddTransactionForm.tsx` and `frontend/src/components/dashboard/TransactionsSection.tsx` to show `sector` alongside `asset_class`, while only allowing sector selection for equity assets.

### Fixed
- Fixed the structural mismatch where target allocation logic mixed market buckets with transaction-type buckets, which made the guidance hard to trust.
- Fixed the missing second-layer classification gap for equity holdings by separating stock-industry / ETF-type tagging from the coarse asset-class bucket.
- Fixed inconsistent scraper backfill windows by making new-symbol and auto-backfill paths start from the earliest BUY date instead of mixing 1990 and 1-year defaults.
- Fixed Taiwan symbol normalization so `00631` is canonicalized to `00631L`, market inference accepts Taiwan suffix symbols, and price history writes use the canonical symbol instead of the raw input.
- Fixed Taiwan suffix normalization to use official market listings: exact listed symbols are preserved, unique `digits -> digits+suffix` cases auto-normalize, and ambiguous suffix bases are left unchanged instead of guessed.
- Changed the transaction form success message and import guidance so users are explicitly told when a Taiwan symbol has been auto-normalized with a suffix.

## 2026-06-27

### Added
- Added `deploy/wealth-backend.service` to track the FastAPI backend systemd unit.
- Added `deploy/nginx-wealth.conf` to track the LAN Nginx reverse proxy and frontend static file configuration.
- Added `deploy/README.md` with frontend build, backend systemd, Nginx site, verification, and rollback commands.
- Added `AUTH_MODEL.md` to document the single-user deployment model, owner account rule, and system-management access boundary.
- Added `SINGLE_USER_SCHEMA_AUDIT_2026-06-28.md` to classify which multi-user-era schema pieces are still active, legacy, or priority cleanup targets.
- Added `CURRENT_STATE_RUNBOOK.md` as the current operational entrypoint for deployment, schema, auth, and verification steps.
- Added Audit Log quick date filters for `今天`, `7 天`, `30 天`, and `全部`.
- Added Audit Log clear-filter action and current date range summary.
- Added Dashboard logout action that clears the local token and returns to `/login`.
- Added Dashboard mobile holding summary cards.
- Added mobile card styling for Dashboard transaction rows.
- Added route-level Dashboard sections: `/overview`, `/holdings`, `/transactions`, and `/transactions/new`.
- Added dedicated page entry files for `Overview`, `Holdings`, `Transactions`, and `Add Transaction`.
- Added `frontend/src/components/DashboardLayout.tsx` for the shared dashboard header, status bar, and route navigation shell.
- Added `frontend/src/hooks/useDashboardState.ts` for shared dashboard query/state/action handling.
- Added `frontend/src/types/dashboard.ts` to centralize dashboard-specific view and sort types.
- Added `frontend/src/components/ConfirmDialog.tsx` for app-owned confirmation dialogs.
- Added `frontend/src/components/InlineNotice.tsx` for in-page dashboard notices.
- Added `frontend/src/components/dashboard/HoldingsSection.tsx` and `frontend/src/components/dashboard/TransactionsSection.tsx` to split major dashboard work areas.
- Added `frontend/src/components/dashboard/shared.ts` and `frontend/src/components/dashboard/DashboardStatCard.tsx` for shared dashboard formatting, labels, and stat cards.
- Added `frontend/src/components/dashboard/OverviewPerformanceSection.tsx` for the overview performance chart area.
- Added `frontend/src/components/ChangePasswordForm.tsx` so the password-change workflow can be reused in both page and dialog contexts.

### Changed
- Installed `/etc/systemd/system/wealth-backend.service` and enabled backend startup at boot.
- Moved backend runtime management from manual uvicorn process to systemd.
- Bound backend to `127.0.0.1:8000`; Nginx `/api` remains the LAN-facing proxy.
- Established the single-user deployment rule that the first registered account is treated as the administrator account after re-login.
- Pruned SQLite user records down to the owner account and one current Codex test account; removed older test users and their related SQLite transaction/holding rows after taking a local backup.
- Removed the unused `stock_info` SQLite table after confirming it was empty and had no active backend or frontend references.
- Removed the deprecated `accounts` active surface: dropped the SQLite `accounts` table, removed `account_id` from active transaction/holding schema, removed the `/accounts` router, and rewrote `snapshot.py` to use accountless holdings data.
- Marked older audit/test/migration documents as historical snapshots so outdated PostgreSQL and `accounts` references are less likely to be mistaken for current runtime truth.
- Reworked `frontend/src/pages/AdminPage.tsx` into tabbed work areas: `總覽`, `資料庫`, `價格與爬蟲`, and `Audit Log`.
- Condensed the Admin overview page for mobile, keeping only key health, database, scheduler, audit log, price source, and recent run status.
- Moved detailed scraper and Audit Log tables out of the Admin overview and into their dedicated tabs.
- Made Audit Log date inputs responsive to avoid mobile overflow.
- Added explicit owner/admin status hints in the Dashboard and Admin headers so the single-user deployment model is visible after login.
- Dashboard system-management shortcut now appears only when the owner token carries the `admin` role.
- Clarified the app as a single-user deployment: `admin` only gates system-management tools for the owner account, not separate user personas.
- Updated deployment notes to state the single-user assumption and how to verify the owner account role in SQLite.
- Corrected the canonical SQLite verification path in `deploy/README.md` from the repo-root `wealth.db` copy to the active `backend/wealth.db`.
- Optimized frontend loading by switching route pages to `React.lazy`/`Suspense` and splitting Vite output into dedicated vendor chunks for charts and icons plus a shared vendor chunk.
- Changed Dashboard section switching from local tab state to URL-based navigation.
- Changed `/` to redirect to `/overview` for a clearer default landing page.
- Changed `App.tsx` routing to point at dedicated page components instead of binding every route directly to `DashboardPage`.
- Changed `DashboardPage.tsx` to consume shared layout and state modules instead of owning the full shell and state lifecycle directly.
- Changed `DashboardPage.tsx` to delegate holdings and transactions rendering to section components.
- Changed transaction delete flow from browser `confirm` to an in-app confirmation dialog.
- Changed transaction undo action to execute directly without a browser confirmation prompt.
- Changed dashboard delete/undo failures from browser `alert` dialogs to in-page notices.
- Changed the overview performance chart block into a dedicated section component and limited it to the overview page.
- Changed the top-right dashboard header actions from separate icon buttons into a single operations menu.
- Changed the top-left dashboard title into a home link that routes back to `/overview`.
- Changed `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/ChangePasswordPage.tsx`, and `frontend/src/components/AddTransactionForm.tsx` to use the in-page notice style instead of mixed feedback patterns.
- Changed transaction add/edit and import feedback to use the same inline notice language as the dashboard.
- Changed dashboard "修改密碼" from a route jump into an in-page modal dialog layered over the current screen.
- Changed `frontend/src/pages/ChangePasswordPage.tsx` to reuse the shared password-change form component instead of owning a separate implementation.
- Changed `/change-password` to redirect back to `/overview`, keeping the dialog as the primary password-change entrypoint.
- Tightened shared mobile layout widths in `frontend/src/index.css`, `frontend/src/components/StatusBar.tsx`, and `frontend/src/components/DashboardLayout.tsx` to stop iPhone 14 Pro horizontal overflow.
- Changed `frontend/src/components/DashboardLayout.tsx` and `frontend/src/components/AddTransactionForm.tsx` so the add-transaction symbol autocomplete dropdown can render above the page content again.
- Cleaned stale `setError` calls in `frontend/src/components/AddTransactionForm.tsx` and routed field-clearing feedback through the existing inline notice flow.
- Changed add-transaction autocomplete ranking to prioritize symbols from the user's real transaction history before fallback ticker suggestions.
- Changed the transaction-list filter query in `frontend/src/components/dashboard/TransactionsSection.tsx` from a plain text input into a symbol autocomplete with mobile-safe suggestion rendering.
- Changed the transaction filter suggestion policy to rank current holdings first, then previously traded but fully closed symbols, and removed generic fallback tickers from that screen.
- Changed the transaction filter date-range layout in `frontend/src/components/dashboard/TransactionsSection.tsx` to stack cleanly on mobile and constrain native date input width.
- Changed the Audit Log date-range layout in `frontend/src/pages/AdminPage.tsx` to use full-width stacked labels on mobile instead of inline compact labels.
- Changed `frontend/src/components/DatePicker.tsx` into the shared date-selection path for add-transaction, transaction filters, and Audit Log filters, including clearable empty-state support for filter use cases.
- Restored static frontend file permissions under `frontend/dist` after a restrictive local build umask caused the deployed nginx site to lose read access.
- Changed the transaction and Audit Log filter defaults so the end-date field initializes to the current local day and resets back to today when filters are cleared.
- Changed `frontend/package.json` so `npm run build` now forces a web-readable output umask and normalizes `frontend/dist` permissions after each build.
- Changed the transaction and Audit Log default date window from open-ended to the last 30 days, including reset behavior.
- Changed login and password input styling so authentication fields have clearer borders, background contrast, and focus visibility on mobile and dark surfaces.
- Removed the standalone `frontend/src/pages/ChangePasswordPage.tsx` page from the active app flow.
- Removed the unused legacy `frontend/src/components/Header.tsx` that still pointed at the old password-change route.
- Rebuilt frontend production assets in `frontend/dist` after UI changes.

### Fixed
- Fixed backend startup failure caused by stale ORM imports in `backend/app/services/transaction_service.py`.
- Fixed login/register outage caused by the backend process being stopped.
- Fixed Admin redirect caused by an older owner token carrying `role=user`.
- Fixed the backend admin-gate error message to say `需要系統管理權限`, matching the single-user owner model.
- Fixed global horizontal page overflow on iPhone 14 Pro by removing body-level side safe-area padding and constraining shared dashboard containers.
- Fixed missing symbol autocomplete dropdown on `/transactions/new` caused by shared layout clipping and fragile dropdown interaction handling.
- Fixed unstable suggestion ordering by removing an older autocomplete effect that could override the new history-first ranking.
- Fixed missing symbol suggestions on the transaction filter screen by wiring autocomplete to the correct `/transactions` search field instead of only the add-transaction form.
- Fixed transaction-filter suggestion relevance by aligning the dropdown with portfolio state rather than showing broad generic symbols.
- Fixed horizontal overflow in the transaction-page date filters on iPhone by separating the date inputs into their own responsive sub-grid.
- Fixed horizontal overflow in Admin Audit Log date filters on iPhone by removing the inline `起/迄` grid layout and switching to stacked labels.
- Fixed the remaining iOS date-picker overflow risk by replacing native date inputs on transaction and Audit Log filters with the shared custom DatePicker interaction.
- Fixed nginx `403 Forbidden` on the LAN homepage by correcting `frontend/dist` directory and file permissions back to web-readable defaults.
- Fixed inconvenient empty end-date defaults in transaction and Audit Log filters by aligning them with the common "through today" use case.
- Fixed the recurring post-build nginx `403 Forbidden` regression by making the frontend build step publish `dist` with `755/644` permissions even when the shell umask is `0077`.
- Fixed overly broad initial filter ranges by setting transaction and Audit Log pages to open on a practical recent-history window.
- Fixed low discoverability of the login username/password fields by strengthening the field chrome instead of relying on subtle background contrast alone.
- Reduced repeated deployment uncertainty by documenting Nginx and systemd deployment files in the repo.

### Risk And Rollback
- Backend systemd rollback: run `sudo systemctl disable --now wealth-backend.service`, then manually start backend with `/home/lewis/wealth/backend/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Nginx rollback: restore a known-good `/etc/nginx/sites-available/wealth`, then run `sudo nginx -t` and `sudo systemctl reload nginx`.
- Owner access rollback: change the first owner account role back to `user` in the `users` table if system-management access should be removed.
- SQLite user-prune rollback: restore `/tmp/backend-wealth-before-user-prune-2026-06-27.db` over `backend/wealth.db` before restarting the backend.
- SQLite `stock_info` rollback: restore `/tmp/backend-wealth-before-stock-info-drop-2026-06-28.db` over `backend/wealth.db` before restarting the backend.
- SQLite accountless rollback: restore `/tmp/backend-wealth-before-accounts-drop-2026-06-28.db` over `backend/wealth.db` before restarting the backend.

### Next
- If Nginx changes are needed, update `deploy/nginx-wealth.conf` first, then copy it into `/etc/nginx/sites-available/wealth` and run `sudo nginx -t`.
- Replace browser `confirm` dialogs with app-owned confirmation modals.
- Refine `/overview` into a tighter mobile-first command summary after validating the separated routes on phone.
- Continue splitting holdings and transactions rendering blocks into smaller section components once the shared shell/state refactor is stable.

## 2026-06-26

### Added
- Added `frontend/src/components/UIState.tsx` with shared `SemanticBadge`, `LoadingState`, `EmptyState`, `ErrorState`, and `DataTimestamp`.

### Changed
- Added shared state panel and badge tone styles to `frontend/src/index.css`.
- Updated Dashboard, Admin, Login, Change Password, Transaction Form, and Status Bar states to use shared UI rules.
- Reordered Dashboard information hierarchy: summary KPIs first, then holdings/allocation, net value chart, and transaction workspace.
- Added empty state handling to the Dashboard holdings area.
- Added sortable holdings table headers with market value descending as the default sort.
- Added price status badges, selected-row highlighting, stock unit display, and sort summary to the holdings table.
- Updated selected holding detail panel to follow the sorted default symbol.
- Reworked the transaction tab into a transaction workspace.
- Added transaction workspace actions for add transaction, clear filters, and undo.
- Added transaction badges for total rows, profitable rows, losing rows, and visible rows.
- Reworked transaction rows into a clearer layered layout with buy/sell badges, category labels, edit hint, and fee/tax/realized gain details.

### Next
- Continue reducing `alert`/`confirm` usage and refine transaction add/edit flow.

## [1.0.0] - 2024-05-26

### Added
- Initial project structure.
- Frontend with React, Vite, and Tailwind.
- Backend with FastAPI and PostgreSQL.
- JWT authentication system.
- Portfolio management for holdings and transactions.
- Basic dashboard with summary stats.
