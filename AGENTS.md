# AGENTS.md

This file provides guidance to AI coding assistants when working with code in this repository.

## Project Overview

Home Assistant custom integration for displaying Too Good To Go (TGTG) surplus food item availability as sensors. Uses the [tgtg-python](https://github.com/ahivert/tgtg-python) library for API access.

## Development Commands

```bash
# Install dependencies (requires Python 3.8+)
scripts/setup
# OR: python3 -m pip install --requirement requirements.txt

# Run Home Assistant locally on port 8123 for testing
scripts/develop
# OR: hass -c . --debug

# Format code (required before PR)
black .
```

## Architecture

This is a **config flow integration** using modern Home Assistant patterns (2025+).

### Key Files

- `custom_components/toogoodtogo/__init__.py` - Entry point: sets up coordinator and forwards to platforms
- `custom_components/toogoodtogo/config_flow.py` - UI-based configuration with email magic link authentication
- `custom_components/toogoodtogo/coordinator.py` - Data update coordinator with pagination, rate limiting, and smart polling
- `custom_components/toogoodtogo/entity.py` - Base entity class extending CoordinatorEntity
- `custom_components/toogoodtogo/sensor.py` - Sensor platform using SensorEntityDescription pattern
- `custom_components/toogoodtogo/diagnostics.py` - Diagnostics support with sensitive field redaction
- `custom_components/toogoodtogo/manifest.json` - Component metadata and tgtg library dependency
- `custom_components/toogoodtogo/strings.json` - Translation strings (English)
- `custom_components/toogoodtogo/translations/` - Localized translations (en, de)

### Design Pattern

- Modern config flow integration with `async_setup_entry()` and `async_unload_entry()`
- `TGTGUpdateCoordinator` extends `DataUpdateCoordinator` for centralized data fetching
- `TGTGEntity` base class extends `CoordinatorEntity` for automatic state updates
- One `TGTGSensor` entity per TGTG item (from favorites or manually configured)
- Device grouping - all sensors grouped under a single device per TGTG account
- Uses `runtime_data` for coordinator storage (modern HA pattern)

### Polling Strategy

- Default: 15-minute polling interval
- Smart polling: 3-minute interval during sales windows (when items are likely available)
- API rate limiting: 500ms delay between API calls
- Adaptive: 1-hour delay on captcha/rate limit errors
- Pagination: Fetches ALL favorites pages (not just first 20)

### Sensor Attributes

Primary state is `items_available` (quantity). Extra attributes include:
- item_id, item_url
- item_price, original_value
- pickup_start, pickup_end
- soldout_timestamp
- orders_placed, total_quantity_ordered
- pickup_window_changed, cancel_until
- logo_url, cover_url
- latitude, longitude (pickup location)

## CI/CD

GitHub Actions run on push/PR:
- **Hassfest validation** - Home Assistant manifest validation
- **HACS validation** - Community Store compatibility
- **CodeQL** - Security analysis

## Known Limitations

- Favorites list only updated when integration reloads (requires reload when adding/removing favorites in TGTG app)
- Token refresh handled via reauth flow when tokens expire
