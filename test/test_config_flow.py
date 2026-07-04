"""Test xmltv_epg config and options flow."""

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xmltv_epg.api import (
    XMLTVClientCommunicationError,
    XMLTVClientError,
)
from custom_components.xmltv_epg.const import (
    DOMAIN,
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

from .const import MOCK_TV_GUIDE_NAME, MOCK_TV_GUIDE_URL


# note: need to bypass integration setup to avoid hass actually trying to setup the entry, which would
# interfere with counters on xmltv_client_get_data
async def test_config_flow_user_step_ok(
    hass, bypass_integration_setup, mock_xmltv_client_get_data
):
    """Test that the 'user' config step correctly creates a config entry."""
    # initialize the config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # check that the first step is a 'form'
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # if a user were to enter 'http://example.com/epg.xml' and submit the form
    # it would result in this call. The import (download + parse) runs as a
    # background task shown as a progress step.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: MOCK_TV_GUIDE_URL},
    )
    assert result["type"] == FlowResultType.SHOW_PROGRESS
    assert result["step_id"] == "import"
    assert result["progress_action"] == "import_guide"

    # once the import task finishes, the entry is created directly with all
    # channels imported (channel selection is done later from the options)
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])

    # to test the connection, a XMLTVClient should be created and
    # the async_get_data method should be called
    mock_xmltv_client_get_data.assert_called_once()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_TV_GUIDE_NAME
    assert result["data"] == {CONF_HOST: MOCK_TV_GUIDE_URL}
    # no explicit channel selection stored => every channel is exposed
    assert result["options"] == {}
    assert result["result"]


async def test_config_flow_user_step_aborts_on_duplicate(
    hass, bypass_integration_setup, mock_xmltv_client_get_data
):
    """Test that the 'user' config step aborts when the source is already configured."""
    # an entry with the same host already exists
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: MOCK_TV_GUIDE_URL}, entry_id="EXISTING"
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # submitting the same host should abort the flow
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: MOCK_TV_GUIDE_URL},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    # the connection test should not even be attempted for a duplicate
    mock_xmltv_client_get_data.assert_not_called()


async def test_config_flow_user_step_handles_error(
    hass, bypass_integration_setup, mock_xmltv_client_get_data
):
    """Test that the 'user' config step correctly handles errors in _test_connection."""
    # initialize the config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # check that the first step is a 'form'
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # raise an communication exception when doing the connection test
    mock_xmltv_client_get_data.side_effect = XMLTVClientCommunicationError(
        "MOCK client communication error"
    )

    # input a "invalid" url.
    # Since the client is mocked to raise an exception, the actual
    # url entered does not matter. The import runs as a progress step first.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: MOCK_TV_GUIDE_URL},
    )
    assert result["type"] == FlowResultType.SHOW_PROGRESS

    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])

    # back on the 'user' step, but now with a 'connection' error
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "connection"}

    # raise a generic exception when doing the connection test
    mock_xmltv_client_get_data.side_effect = XMLTVClientError(
        "MOCK client communication error"
    )

    # input a "invalid" url.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: MOCK_TV_GUIDE_URL},
    )
    assert result["type"] == FlowResultType.SHOW_PROGRESS

    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])

    # back on the 'user' step, but now with a 'unknown' error
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "unknown"}


async def test_option_flow_init_step_ok(hass, mock_xmltv_client_get_data):
    """Test that the 'init' options step correctly creates a config entry."""
    # create a new MockConfigEntry and add to HASS, bypassing the config flow
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: MOCK_TV_GUIDE_URL}, entry_id="MOCK"
    )
    entry.add_to_hass(hass)

    # the options flow lists channels from the loaded coordinator, so the entry
    # must be fully set up (not bypassed) for its runtime_data to be available
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # the first step should be a 'form' with id 'init'
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # options are grouped into display sections; submit values accordingly
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "channels": {
                OPT_SELECTED_CHANNELS: ["mock 1", "mock 2"],
            },
            "update": {
                OPT_UPDATE_INTERVAL: 24,
            },
            "programs": {
                OPT_ENABLE_CURRENT_SENSOR: True,
                OPT_ENABLE_UPCOMING_SENSOR: False,
                OPT_ENABLE_PRIMETIME_SENSOR: False,
                OPT_PROGRAM_LOOKAHEAD: 10,
                OPT_PRIMETIME_TIME: "20:00:00",
            },
            "images": {
                OPT_ENABLE_CHANNEL_ICONS: True,
                OPT_ENABLE_PROGRAM_IMAGES: True,
            },
        },
    )

    # the flow should finish and store the options flattened (not nested)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        OPT_SELECTED_CHANNELS: ["mock 1", "mock 2"],
        OPT_UPDATE_INTERVAL: 24,
        OPT_ENABLE_CURRENT_SENSOR: True,
        OPT_ENABLE_UPCOMING_SENSOR: False,
        OPT_ENABLE_PRIMETIME_SENSOR: False,
        OPT_PROGRAM_LOOKAHEAD: 10,
        OPT_PRIMETIME_TIME: "20:00:00",
        OPT_ENABLE_CHANNEL_ICONS: True,
        OPT_ENABLE_PROGRAM_IMAGES: True,
    }
