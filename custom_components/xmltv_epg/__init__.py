"""
Custom integration to integrate XMLTV EPG data with Home Assistant.

For more details about this integration, please refer to
https://github.com/shadow578/homeassistant_xmltv-epg
"""

from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import XMLTVClient
from .const import (
    DEFAULT_ENABLE_CHANNEL_ICONS,
    DEFAULT_ENABLE_CURRENT_SENSOR,
    DEFAULT_ENABLE_PRIMETIME_SENSOR,
    DEFAULT_ENABLE_PROGRAM_IMAGES,
    DEFAULT_ENABLE_UPCOMING_SENSOR,
    DEFAULT_PRIMETIME_TIME,
    DEFAULT_PROGRAM_LOOKAHEAD,
    DEFAULT_UPDATE_INTERVAL,
    LOGGER,
    OPT_ENABLE_CHANNEL_ICONS,
    OPT_ENABLE_CURRENT_SENSOR,
    OPT_ENABLE_PRIMETIME_SENSOR,
    OPT_ENABLE_PROGRAM_IMAGES,
    OPT_ENABLE_UPCOMING_SENSOR,
    OPT_PRIMETIME_TIME,
    OPT_PROGRAM_LOOKAHEAD,
    OPT_SELECTED_CHANNELS,
    OPT_UPDATE_INTERVAL,
)
from .coordinator import XMLTVConfigEntry, XMLTVDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.IMAGE,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: XMLTVConfigEntry) -> bool:
    """Set up this integration using UI."""
    entry.runtime_data = coordinator = XMLTVDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        client=XMLTVClient(
            session=async_get_clientsession(hass),
            url=entry.data[CONF_HOST],
            logger=LOGGER,
        ),
        update_interval=entry.options.get(OPT_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        lookahead=entry.options.get(OPT_PROGRAM_LOOKAHEAD, DEFAULT_PROGRAM_LOOKAHEAD),
        enable_current_sensor=entry.options.get(
            OPT_ENABLE_CURRENT_SENSOR, DEFAULT_ENABLE_CURRENT_SENSOR
        ),
        enable_upcoming_sensor=entry.options.get(
            OPT_ENABLE_UPCOMING_SENSOR, DEFAULT_ENABLE_UPCOMING_SENSOR
        ),
        enable_primetime_sensor=entry.options.get(
            OPT_ENABLE_PRIMETIME_SENSOR, DEFAULT_ENABLE_PRIMETIME_SENSOR
        ),
        enable_channel_icon=entry.options.get(
            OPT_ENABLE_CHANNEL_ICONS, DEFAULT_ENABLE_CHANNEL_ICONS
        ),
        enable_program_image=entry.options.get(
            OPT_ENABLE_PROGRAM_IMAGES, DEFAULT_ENABLE_PROGRAM_IMAGES
        ),
        primetime_time=entry.options.get(OPT_PRIMETIME_TIME, DEFAULT_PRIMETIME_TIME),
        selected_channels=entry.options.get(OPT_SELECTED_CHANNELS),
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # listen for updates to the config entry to re-setup it
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: XMLTVConfigEntry) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: XMLTVConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
