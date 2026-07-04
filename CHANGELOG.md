# Changelog

[![GitHub Release](https://img.shields.io/github/release/domodom30/ha-xmltv-epg)](https://github.com/domodom30/ha-xmltv-epg/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![installation_badge](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.xmltv_epg.total)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/A1V11ZZTPI)

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0]

### Changed

- Migrated entry storage to `entry.runtime_data` with a typed `XMLTVConfigEntry`,
  replacing the manual `hass.data[DOMAIN]` bookkeeping.
- Grouped the options flow into collapsible sections (Channels, Update, Programs, Images).
- Simplified `TVProgram.channel`: the linked channel is now initialised to `None` in
  `model_post_init` instead of being detected via a hard-coded name-mangled attribute.


## [2.0.0]

### Added

- XMLTV guide import from any direct URL, with support for `.gz`, `.xz` and `.zip`
  compressed files.
- Memory-efficient streaming parser (`TVGuide.from_xml_streaming`) that keeps peak memory
  bounded on very large national guides.
- Channel selection during setup and from the options, so only the wanted channels are
  exposed as entities.
- Optional per-channel program sensors: Current, Upcoming and Prime-Time (with a
  configurable prime-time time of day and a "current program" lookahead).
- Optional per-channel image entities: Channel Icon and Current / Upcoming / Prime-Time
  Program Image.
- A per-guide **Last Update** diagnostic sensor.
- Config-entry **diagnostics** with the source URL redacted.
- French translation, alongside the existing English translations.

### Changed

- Rebuilt the XMLTV model layer on top of `pydantic` / `pydantic-xml` for strict,
  validated parsing.

---

Project maintained by [@domodom30](https://github.com/domodom30) —
fork of [shadow578/homeassistant_xmltv-epg](https://github.com/shadow578/homeassistant_xmltv-epg).

