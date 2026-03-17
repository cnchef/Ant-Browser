# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ant Browser is a Windows desktop browser management tool built with Wails (Go + React/TypeScript). It provides fingerprint browser instance isolation, proxy pool management, and Chrome core management for multi-account operations.

**Platform:** Windows 10/11 only
**Architecture:** Wails v2 desktop app with Go backend and React frontend

## Commands

### Development

```bash
# Start dev mode (recommended - uses bat/dev.bat)
bat\dev.bat

# Stop dev mode
bat\stop.bat

# Or use the unified Python service manager directly
python bat\service.py start    # Start dev server
python bat\service.py stop     # Stop dev server
python bat\service.py restart  # Restart dev server
python bat\service.py status   # Check server status

# Or directly with wails
wails dev

# Regenerate Wails bindings
wails generate module

# After regeneration, copy bindings
xcopy /E /I /Y frontend\wailsjs frontend\src\wailsjs
```

**Note:** `bat/service.py` is a cross-platform Python script (Windows/macOS/Linux) that handles dev server management. It includes duplicate process detection - if a Wails dev process is already running, it will prompt you to kill it and restart or cancel.

### Build

```bash
# Build frontend
cd frontend && npm run build

# Build Go backend
go build -o build/bin/ant-chrome.exe .

# Full production build
wails build
```

### Testing

```bash
# Run Go tests
go test ./...

# Run specific test
go test ./backend/internal/launchcode -run TestLaunchCodeService

# Run frontend tests (if configured)
cd frontend && npm test
```

### Dependencies

```bash
# Install/update Go dependencies
go mod tidy

# Install frontend dependencies
cd frontend && npm install
```

## Architecture

### High-Level Structure

```
┌─────────────────────────────────────────────────────────────┐
│                      Wails Application                       │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React/TypeScript)  │  Backend (Go)               │
│  - Vite + TailwindCSS         │  - Wails bindings           │
│  - Zustand state management   │  - SQLite database          │
│  - React Router               │  - Browser process manager  │
│  - Lucide icons               │  - Proxy managers           │
└─────────────────────────────────────────────────────────────┘
```

### Backend Modules (`backend/`)

| Module | Responsibility |
|--------|----------------|
| `app.go` | Main application struct, Wails bindings, lifecycle management |
| `internal/browser/` | Browser instance manager, profile/proxy/core DAOs |
| `internal/proxy/` | Xray/Clash/SingBox managers, speed testing, IP health |
| `internal/launchcode/` | Launch code service for quick instance startup |
| `internal/database/` | SQLite connection, migrations (versioned schema) |
| `internal/config/` | YAML configuration loading and saving |
| `internal/logger/` | Structured logging with rotation and method interception |
| `internal/tray/` | System tray integration |

### Frontend Modules (`frontend/src/modules/`)

| Module | Pages/Components |
|--------|------------------|
| `dashboard/` | Statistics overview, quick actions |
| `browser/` | Instance list, edit, proxy pool, core management (14 pages) |
| `profile/` | User profile, license management |
| `settings/` | Application settings |
| `charts/` | Data visualization with Recharts |

### Shared (`frontend/src/shared/`)

- `components/` - Reusable UI components (Button, Modal, Table, Form, etc.)
- `layout/` - App shell (Layout, Sidebar, Topbar)
- `theme/` - Dark/light theme system with CSS variables

### Data Flow

1. **Wails Bindings**: Go methods exported to frontend via `wails generate module`
   - Bindings generated to `frontend/wailsjs/`, copied to `frontend/src/wailsjs/`
   - Frontend imports from `src/wailsjs/go/main/App`

2. **Database**: SQLite with versioned migrations
   - Schema tracked in `schema_migrations` table
   - DAOs in `internal/browser/*_dao.go`
   - Current schema version: 5 (see `backend/internal/database/sqlite.go`)

3. **Configuration**: YAML-based (`config.yaml`)
   - Auto-created with defaults if missing
   - Runtime reload supported via `ReloadConfig()` API

## Key Concepts

### Browser Instance Lifecycle

Each browser instance has:
- Unique `profileId` (UUID)
- Isolated `userDataDir` for profile separation
- Optional `proxyConfig` (direct://, http://, or Clash URL)
- `fingerprintArgs` for chrome fingerprinting
- Optional `launchCode` for quick startup via Ctrl+K

### Proxy Architecture

- **Direct**: `direct://` - no proxy
- **HTTP/HTTPS**: `http://host:port` or `https://host:port`
- **Clash Subscription**: URL that returns Clash config
- **Bridge Mode**: Xray/SingBox creates local SOCKS5 bridge for complex protocols

### LaunchCode Service

- Generates unique codes per instance for quick startup
- Stored in `launch_codes` table
- Server listens on configurable port (default: auto-select)
- External tools can trigger instance launch via HTTP

### Path Resolution

- **Dev mode**: `appRoot` = project directory (CWD)
- **Production**: `appRoot` = directory containing `ant-chrome.exe`
- All relative paths resolved against `appRoot`

## Development Notes

### Wails Dev Mode

- Frontend served by Vite (default port 5218)
- Backend hot-reloads on Go file changes
- `bat/service.py` handles process management, port checking, and duplicate detection
- Use `bat/dev.bat` or `python bat\service.py start` to start
- Use `bat/stop.bat` or `python bat\service.py stop` to stop

### Database Migrations

To add new schema changes:
1. Add new `migration` entry to `backend/internal/database/sqlite.go`
2. Increment `version` number (must be sequential)
3. Use idempotent DDL statements
4. Never modify existing migrations - only append

### Proxy Testing

- Speed test uses multiple URLs with fallback
- Results cached in `browser_proxies.last_latency_ms`
- IP health check calls external IPPure API through proxy bridge

### Common Patterns

**Go Logger Usage:**
```go
log := logger.New("ModuleName")
log.Info("message", logger.F("key", value))
log.Error("message", logger.F("error", err))
```

**Wails Events (Frontend):**
```typescript
runtime.EventsOn('event-name', (data) => { /* handle */ })
runtime.EventsEmit('event-name', payload)
```

**DAO Pattern:**
```go
// Inject DAO into manager
mgr.ProfileDAO = browser.NewSQLiteProfileDAO(db.GetConn())
// Use with automatic fallback to config.yaml if nil
if mgr.ProfileDAO != nil {
    list, _ := mgr.ProfileDAO.List()
}
```

## Files to Know

| File | Purpose |
|------|---------|
| `wails.json` | Wails configuration (build, dev server, bindings output) |
| `config.yaml` | Application configuration |
| `bat/dev.bat` | Wrapper that calls `python bat\service.py start` |
| `bat/stop.bat` | Wrapper that calls `python bat\service.py stop` |
| `bat/service.py` | Cross-platform dev service manager (start/stop/restart/status) |
| `frontend/src/App.tsx` | Main React component with routing |
| `backend/app.go` | Core application logic and API bindings |
| `backend/internal/database/sqlite.go` | Schema migrations (add new versions here) |
