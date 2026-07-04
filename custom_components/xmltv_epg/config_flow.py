"""Adds config flow for XMLTV."""

import asyncio

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import XMLTVClient, XMLTVClientCommunicationError, XMLTVClientError
from .const import (
    DEFAULT_ENABLE_CHANNEL_ICONS,
    DEFAULT_ENABLE_CURRENT_SENSOR,
    DEFAULT_ENABLE_PRIMETIME_SENSOR,
    DEFAULT_ENABLE_PROGRAM_IMAGES,
    DEFAULT_ENABLE_UPCOMING_SENSOR,
    DEFAULT_PRIMETIME_TIME,
    DEFAULT_PROGRAM_LOOKAHEAD,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
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
from .model import TVGuide

# Option-flow display sections. These only group fields visually; the selected
# values are flattened back into a single options dict before being stored.
SECTION_UPDATE = "update"
SECTION_PROGRAMS = "programs"
SECTION_IMAGES = "images"
SECTION_CHANNELS = "channels"


def _channel_select_options(guide: TVGuide) -> list[selector.SelectOptionDict]:
    """Build the multi-select options (one per channel) from a guide."""
    return [
        selector.SelectOptionDict(value=channel.id, label=channel.display_name)
        for channel in sorted(guide.channels, key=lambda c: c.display_name)
    ]


def _channel_select_selector(guide: TVGuide) -> selector.SelectSelector:
    """Build a multi-select channel selector from a guide."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=_channel_select_options(guide),
            multiple=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
            custom_value=False,
        )
    )


class XMLTVFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for XMLTV."""

    VERSION = 1

    _host: str | None = None
    _import_task: asyncio.Task[None] | None = None
    _guide: TVGuide | None = None
    _import_error: str | None = None

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            self._host = user_input[CONF_HOST]
            return await self.async_step_import()

        return self._show_user_form()

    def _show_user_form(
        self, errors: dict[str, str] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the data source URL form."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=self._host,
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.URL),
                    )
                }
            ),
            errors=errors or {},
        )

    async def async_step_import(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Download and parse the guide, showing a progress indicator.

        The import (download + decompression + parsing) can take tens of seconds
        for large guides, so it runs as a background task while the frontend shows
        a progress spinner instead of a frozen, unresponsive form.
        """
        if self._import_task is None:
            self._import_error = None
            # eager_start=False guarantees the progress step is shown even when the
            # import completes very quickly, keeping the flow behaviour deterministic.
            self._import_task = self.hass.async_create_task(
                self._async_do_import(), eager_start=False
            )

        if not self._import_task.done():
            return self.async_show_progress(
                step_id="import",
                progress_action="import_guide",
                progress_task=self._import_task,
            )

        self._import_task = None
        next_step_id = "finish" if self._import_error is None else "retry"
        return self.async_show_progress_done(next_step_id=next_step_id)

    async def _async_do_import(self) -> None:
        """Run the connection test; store the guide or the error to report."""
        if self._host is None:
            # Should not happen: the user step always sets the host first.
            self._import_error = "unknown"
            return
        try:
            self._guide = await self._test_connection(url=self._host)
        except XMLTVClientCommunicationError as exception:
            LOGGER.error(exception)
            self._import_error = "connection"
        except XMLTVClientError as exception:
            LOGGER.exception(exception)
            self._import_error = "unknown"

    async def async_step_finish(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Create the entry once the guide has been imported.

        All channels are imported by default; the selection can be narrowed later
        from the integration options. Storing no explicit selection keeps every
        channel exposed and automatically picks up channels added to the guide.
        """
        guide = self._guide
        if guide is None:
            # Should not happen: the import succeeded before reaching this step.
            return self._show_user_form(errors={"base": "unknown"})

        return self.async_create_entry(
            title=guide.name or "",
            data={CONF_HOST: self._host},
            options={},
        )

    async def async_step_retry(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Re-show the URL form with the error after a failed import."""
        return self._show_user_form(errors={"base": self._import_error or "unknown"})

    async def _test_connection(self, url: str) -> TVGuide:
        """Validate connection and return the fetched guide."""
        client = XMLTVClient(
            session=async_create_clientsession(self.hass),
            url=url,
            logger=LOGGER,
        )
        guide = await client.async_get_data()
        if not guide:
            raise XMLTVClientCommunicationError("No data received")

        return guide

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get options flow handler."""
        return XMLTVOptionsFlowHandler()


class XMLTVOptionsFlowHandler(config_entries.OptionsFlow):
    """XMLTV options flow."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the XMLTV options."""
        if user_input is not None:
            # Options are grouped into sections for display, but stored flat so
            # the rest of the integration keeps reading them without changes.
            data: dict = {}
            for section_values in user_input.values():
                data.update(section_values)
            return self.async_create_entry(data=data)

        options = self.config_entry.options
        guide: TVGuide = self.config_entry.runtime_data.data
        # Default to all channels when no explicit selection is stored yet.
        selected_channels = options.get(
            OPT_SELECTED_CHANNELS, [channel.id for channel in guide.channels]
        )
        data_schema = vol.Schema(
            {
                vol.Required(SECTION_CHANNELS): section(
                    vol.Schema(
                        {
                            vol.Required(
                                OPT_SELECTED_CHANNELS,
                                default=selected_channels,
                            ): _channel_select_selector(guide),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Required(SECTION_UPDATE): section(
                    vol.Schema(
                        {
                            vol.Required(
                                OPT_UPDATE_INTERVAL,
                                default=options.get(
                                    OPT_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                                ),
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=1,
                                    step=1,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Required(SECTION_PROGRAMS): section(
                    vol.Schema(
                        {
                            vol.Required(
                                OPT_ENABLE_CURRENT_SENSOR,
                                default=options.get(
                                    OPT_ENABLE_CURRENT_SENSOR,
                                    DEFAULT_ENABLE_CURRENT_SENSOR,
                                ),
                            ): selector.BooleanSelector(),
                            vol.Required(
                                OPT_ENABLE_UPCOMING_SENSOR,
                                default=options.get(
                                    OPT_ENABLE_UPCOMING_SENSOR,
                                    DEFAULT_ENABLE_UPCOMING_SENSOR,
                                ),
                            ): selector.BooleanSelector(),
                            vol.Required(
                                OPT_ENABLE_PRIMETIME_SENSOR,
                                default=options.get(
                                    OPT_ENABLE_PRIMETIME_SENSOR,
                                    DEFAULT_ENABLE_PRIMETIME_SENSOR,
                                ),
                            ): selector.BooleanSelector(),
                            vol.Required(
                                OPT_PROGRAM_LOOKAHEAD,
                                default=options.get(
                                    OPT_PROGRAM_LOOKAHEAD, DEFAULT_PROGRAM_LOOKAHEAD
                                ),
                            ): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    step=1,
                                    mode=selector.NumberSelectorMode.BOX,
                                )
                            ),
                            vol.Required(
                                OPT_PRIMETIME_TIME,
                                default=options.get(
                                    OPT_PRIMETIME_TIME, DEFAULT_PRIMETIME_TIME
                                ),
                            ): selector.TimeSelector(),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Required(SECTION_IMAGES): section(
                    vol.Schema(
                        {
                            vol.Required(
                                OPT_ENABLE_CHANNEL_ICONS,
                                default=options.get(
                                    OPT_ENABLE_CHANNEL_ICONS,
                                    DEFAULT_ENABLE_CHANNEL_ICONS,
                                ),
                            ): selector.BooleanSelector(),
                            vol.Required(
                                OPT_ENABLE_PROGRAM_IMAGES,
                                default=options.get(
                                    OPT_ENABLE_PROGRAM_IMAGES,
                                    DEFAULT_ENABLE_PROGRAM_IMAGES,
                                ),
                            ): selector.BooleanSelector(),
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
