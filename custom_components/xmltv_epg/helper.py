"""tvxml_epg helper functions."""

import re
from typing import Literal, assert_never

from .const import ChannelSensorMode
from .model import TVChannel


def normalize_for_entity_id(s: str) -> str:
    """
    Normalize a string for usage in an entity_id.

    Example:
    - s = 'FR: WDR (Münster)'
    => "tf1seriesfilms_fr"

    :param s: The string to normalize.
    :return: The normalized string.

    """
    original = s

    # lower case
    s = s.lower()

    # special replacement rules
    replacements = {
        # replace umlauts with their respective digraphs
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        # '+' is replaced with ' plus '.
        "+": " plus ",
    }
    for umlaut, replacement in replacements.items():
        s = s.replace(umlaut, replacement)

    # replace "delimiting characters" and spaces with underscores
    for c in " -.:":
        s = s.replace(c, "_")

    # remove all non-alphanumeric characters except underscores
    s = "".join(c if c.isalnum() or c == "_" else "" for c in s)

    # trim underscores from start and end
    s = s.strip("_")

    # collapse all occurrences of multiple underscores into a single one
    s = re.sub("_+", "_", s)

    if not s:
        raise ValueError(
            f"cannot normalize {original!r} into a valid entity_id fragment"
        )

    return s


def program_get_normalized_identification(
    channel: TVChannel,
    mode: ChannelSensorMode,
    kind: Literal["program_sensor", "program_image", "channel_icon"],
) -> tuple[str, str]:
    """
    Return normalized identification information for a sensor for the given channel and upcoming status.

    The identification information consists of the sensor entity_id and the translation_key.
    For the entity_id, the channel id is normalized and cleaned up to form a valid entity_id.

    Example:
    - channel_id = 'FR: My Channel 1'
    - mode = 'current'
    - kind = 'program_sensor'
    => ('program_current', 'sensor.fr_my_channel_1_program_current')

    - channel_id = "FR: My Channel 1'
    - mode = 'upcoming'
    - kind = 'program_image'
    => ('program_image_upcoming', 'image.fr_my_channel_1_program_image_upcoming')

    - channel_id = "FR: My Channel 1'
    - mode = 'primetime'
    - kind = 'program_image'
    => ('program_image_primetime', 'image.fr_my_channel_1_program_image_primetime')

    - channel_id = "FR: My Channel 1'
    - mode = (don't care)
    - kind = 'channel_icon'
    => ('channel_icon', 'image.fr_my_channel_1_icon')

    :param channel: The TV channel.
    :param mode: The sensor operating mode.
    :param kind: entity type to create id for
    :return: (translation_key, entity_id) tuple.

    """
    match kind:
        case "program_sensor":
            translation_key = f"program_{mode}"
            entity_id = (
                f"sensor.{normalize_for_entity_id(channel.id)}_{translation_key}"
            )
        case "program_image":
            translation_key = f"program_image_{mode}"
            entity_id = f"image.{normalize_for_entity_id(channel.id)}_{translation_key}"
        case "channel_icon":
            translation_key = "channel_icon"
            entity_id = f"image.{normalize_for_entity_id(channel.id)}_icon"
        case _:
            assert_never(kind)

    return translation_key, entity_id
