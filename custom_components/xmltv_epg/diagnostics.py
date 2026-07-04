"""Diagnostics support for XMLTV EPG."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import XMLTVConfigEntry

# The source URL may embed private tokens or credentials.
TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: XMLTVConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    guide = coordinator.data

    last_update = coordinator.last_update_time

    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update": last_update.isoformat() if last_update is not None else None,
        },
        "guide": {
            "name": guide.name,
            "channel_count": len(guide.channels),
            "program_count": len(guide.programs),
        },
    }
