"""XMLTV Entity class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.xmltv_epg.model.program import TVProgram

from .const import DOMAIN, ChannelSensorMode
from .coordinator import XMLTVDataUpdateCoordinator
from .model import TVChannel, TVGuide


class XMLTVEntity(CoordinatorEntity[XMLTVDataUpdateCoordinator]):
    """XMLTV Entity class."""

    coordinator: XMLTVDataUpdateCoordinator

    def __init__(
        self, coordinator: XMLTVDataUpdateCoordinator, channel: TVChannel | None
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        guide: TVGuide = coordinator.data

        if guide.name is not None:
            self._attr_attribution = f"Data provided by {guide.name}"

        if channel is not None:
            device_info = DeviceInfo(
                identifiers={(DOMAIN, channel.id)},
                name=channel.display_name,
                manufacturer=guide.name,
                model="TV Channel",
                entry_type=DeviceEntryType.SERVICE,
            )

            # configuration_url must be a valid http(s) URL or the device
            # registry rejects it, so only set it when the guide URL qualifies.
            url = guide.url
            if url is not None and url.startswith(("http://", "https://")):
                device_info["configuration_url"] = url

            self._attr_device_info = device_info

    async def async_added_to_hass(self) -> None:
        """
        Populate the entity state as soon as it is added.

        CoordinatorEntity only pushes state on subsequent coordinator updates,
        so the initial value is written here from the already-fetched data.
        """
        await super().async_added_to_hass()
        self._handle_coordinator_update()


class XMLTVProgramEntity(XMLTVEntity):
    """XMLTV Entity with Program information."""

    _channel: TVChannel
    _program: TVProgram | None
    _mode: ChannelSensorMode

    def __init__(
        self,
        coordinator: XMLTVDataUpdateCoordinator,
        channel: TVChannel,
        mode: ChannelSensorMode,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, channel)

        self._channel = channel
        self._program = None
        self._mode = mode

    def _update_from_coordinator(self) -> bool:
        """
        Update channel and program data from the coordinator.

        Note: To be called from _handle_coordinator_update.

        :return: True if program data was updated, False if channel could not be found.
        """
        channel = self.coordinator.data.get_channel(self._channel.id)
        if channel is None:
            self._program = None
            return False

        self._channel = channel

        # get program based on mode
        if self._mode == ChannelSensorMode.CURRENT:
            self._program = channel.get_current_program(self.coordinator.current_time)
        elif self._mode == ChannelSensorMode.NEXT:
            self._program = channel.get_next_program(self.coordinator.current_time)
        elif self._mode == ChannelSensorMode.PRIMETIME:
            self._program = channel.get_current_program(self.coordinator.primetime_time)
        else:
            raise ValueError(
                f"Unsupported mode: {self._mode}. Please report this issue."
            )

        return True
