# Implementation Plan - Fix IPRoyal Proxy Authentication

This plan outlines the steps to resolve the 407 Proxy Auth Required errors when using IPRoyal GEO proxies in TG Tools.

## Problem Statement
IPRoyal GEO proxies require specific parameterized credentials. The current implementation sometimes fails to parse these correctly or passes them to Telethon in a way that triggers authentication failures.

## Proposed Changes

### 1. Database Model Update
- [x] Modify `Proxy` model in `backend/models.py` to include explicit fields: `host`, `port`, `username`, `password`.
- [ ] Ensure the SQLite database is updated with these new columns.

### 2. Unified Proxy Utility
- [x] Update `backend/core/proxy_utils.py` with:
    - `parse_proxy_string`: Support both URL and `host:port:user:pass` formats.
    - `build_proxy_config`: A single source of truth for generating Telethon tuples, Requests configs, and masked logging details.

### 3. API Router Updates
- [x] Update `backend/routers/proxies.py`:
    - `create_proxy`: Parse incoming URLs and populate the new explicit fields.
    - `test_proxy`: Use `requests` with `PySocks` for the standalone test (more reliable for SOCKS5 than `httpx`).

### 4. Telethon Integration
- [x] Update `backend/core/session_manager.py`:
    - Use `build_proxy_config` to get the Telethon-compatible tuple.
    - Improve logging to show masked credentials and exact proxy parameters used.

## Verification Steps
1. Run the migration script to update the database schema.
2. Manually test adding a proxy via the updated API.
3. Verify that the proxy test (using `requests`) passes.
4. Verify that a Telethon connection attempt using the proxy succeeds.
