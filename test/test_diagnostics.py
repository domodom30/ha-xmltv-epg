"""Test xmltv_epg diagnostics."""

from homeassistant.const import CONF_HOST
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xmltv_epg.const import DOMAIN
from custom_components.xmltv_epg.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .const import MOCK_TV_GUIDE_NAME, MOCK_TV_GUIDE_URL


async def test_config_entry_diagnostics(hass, mock_xmltv_client_get_data):
    """Test config entry diagnostics, including redaction of the source URL."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: MOCK_TV_GUIDE_URL},
        entry_id="MOCK",
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    # the source URL must be redacted
    assert diagnostics["entry"]["data"][CONF_HOST] == "**REDACTED**"

    # guide meta information is exposed
    assert diagnostics["guide"]["name"] == MOCK_TV_GUIDE_NAME
    assert diagnostics["guide"]["channel_count"] == 3
    assert diagnostics["guide"]["program_count"] == 9
