# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Responsive UI redesign with Hermes-style blue theme
- Dark/Light mode toggle with localStorage persistence
- Area chart for portfolio history visualization
- Stock scraper system (Taiwan + US markets)
- Admin monitoring page (database stats, scraper status, logs)
- Transaction form with stock autocomplete and calendar picker
- Python logging system with FastAPI middleware
- Frontend error interceptor and request logger
- Conventional commits guidelines

### Changed
- Updated tailwind.config.js with custom color theme
- Improved mobile-first responsive layouts
- Migrated from line chart to area chart with gradient

### Fixed
- iPhone/iPad responsive layout issues
- Theme persistence across sessions

## [1.0.0] - 2024-05-26

### Added
- Initial project structure
- Frontend (React + Vite + Tailwind)
- Backend (FastAPI + PostgreSQL)
- Authentication system (JWT)
- Portfolio management (holdings, transactions)
- Basic dashboard with summary stats