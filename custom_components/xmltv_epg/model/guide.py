"""Module defining the TVGuide model for XMLTV EPG data."""

import contextlib
import io
from typing import Any

from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]
from pydantic_core import ValidationError
from pydantic_xml import BaseXmlModel, attr, element, xml_field_validator
from pydantic_xml.element.element import XmlElementReader

from custom_components.xmltv_epg.model.omit_on_error_validator import (
    parse_list_omit_on_error,
)

from .channel import TVChannel
from .program import TVProgram

# XMLTV root <tv> attribute -> TVGuide field, used by streaming parsing.
_ROOT_ATTR_TO_FIELD = {
    "source-info-name": "source_name",
    "source-info-url": "source_url",
    "generator-info-name": "generator_name",
    "generator-info-url": "generator_url",
}


class TVGuide(BaseXmlModel, tag="tv", search_mode="ordered"):
    """Represents a TV Guide containing channels and their programs."""

    source_name: str | None = attr(name="source-info-name", default=None)
    """Name of the source that provided the epg data, if available."""

    source_url: str | None = attr(name="source-info-url", default=None)
    """URL of the source that provided the epg data, if available."""

    generator_name: str | None = attr(name="generator-info-name", default=None)
    """Name of the program that generated the xmltv data, if available."""

    generator_url: str | None = attr(name="generator-info-url", default=None)
    """URL of the program that generated the xmltv data, if available."""

    channels: list[TVChannel] = element(tag="channel", default_factory=list)
    """List of all TV channels defined in this guide."""

    programs: list[TVProgram] = element(tag="programme", default_factory=list)
    """List of all TV programs defined in this guide."""

    @xml_field_validator("channels")
    @classmethod
    def _omit_invalid_channels(
        cls, element: XmlElementReader, field_name: str
    ) -> list[TVChannel]:
        """Omit invalid items from channels lists while parsing."""
        return parse_list_omit_on_error(element, TVChannel, cls.__xml_search_mode__)

    @xml_field_validator("programs")
    @classmethod
    def _omit_invalid_programs(
        cls, element: XmlElementReader, field_name: str
    ) -> list[TVProgram]:
        """Omit invalid items from programs lists while parsing."""
        return parse_list_omit_on_error(element, TVProgram, cls.__xml_search_mode__)

    @classmethod
    def from_xml_streaming(cls, xml_bytes: bytes) -> "TVGuide":
        """
        Parse XMLTV data incrementally to keep peak memory bounded.

        The inherited whole-document ``from_xml`` builds the entire lxml tree AND
        the full pydantic object graph at once. On large guides (full French EPG
        ~90 MB XML, ~117k programmes) this peaks around 2.6 GB and OOM-kills
        memory-constrained Home Assistant hosts. Here we iterate with lxml
        ``iterparse``, validate one ``<channel>`` / ``<programme>`` at a time and
        free each element right after, so peak memory drops by ~5x with identical
        results. Invalid items are omitted, matching the ``from_xml`` behaviour.
        """
        channels: list[TVChannel] = []
        programs: list[TVProgram] = []
        root_attrs: dict[str, str] = {}

        context = etree.iterparse(
            io.BytesIO(xml_bytes),
            events=("start", "end"),
            tag=("tv", "channel", "programme"),
        )
        for event, elem in context:
            if elem.tag == "tv":
                if event == "start":
                    # Capture root attributes before children are cleared away.
                    root_attrs = dict(elem.attrib)
                continue
            if event != "end":
                continue

            with contextlib.suppress(ValidationError):
                if elem.tag == "channel":
                    channels.append(TVChannel.from_xml_tree(elem))
                else:
                    programs.append(TVProgram.from_xml_tree(elem))

            # Release the processed element and its already-seen previous siblings
            # so the in-memory tree never grows to the full document.
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        del context

        root_fields = {
            field: root_attrs[attr_name]
            for attr_name, field in _ROOT_ATTR_TO_FIELD.items()
            if attr_name in root_attrs
        }
        return cls(channels=channels, programs=programs, **root_fields)

    @property
    def name(self) -> str | None:
        """
        Get the name of the guide.

        :return: generator_name, source_name, or None, depending on availability

        """
        return self.generator_name or self.source_name

    @property
    def url(self) -> str | None:
        """
        Get the info URL for the guide.

        :return: generator_url, source_url, or None, depending on availability

        """
        return self.generator_url or self.source_url

    def model_post_init(self, __context: Any) -> None:  # noqa: PYI063
        """Hooks post-initialization to cross-link channels and programs."""
        # Index channels by id once so cross-linking stays O(programs + channels).
        # A linear get_channel() per program is O(programs * channels) and holds the
        # GIL for seconds on large guides (full French EPG), starving the event loop.
        channels_by_id = {channel.id: channel for channel in self.channels}
        for program in self.programs:
            channel = channels_by_id.get(program.channel_id)
            if channel is not None:
                channel._link_program(program)  # noqa: SLF001
                program._link_channel(channel)  # noqa: SLF001

        # sort each channel's programs once, after all links are established
        for channel in self.channels:
            channel._sort_programs()  # noqa: SLF001

    def get_channel(self, channel_id: str) -> TVChannel | None:
        """Get channel by ID."""
        return next((c for c in self.channels if c.id == channel_id), None)
