# XMLTV EPG

[![GitHub Release](https://img.shields.io/github/release/domodom30/ha-xmltv-epg)](https://github.com/domodom30/ha-xmltv-epg/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![installation_badge](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.xmltv_epg.total)

_Integration to add [XMLTV][xmltv_wiki] EPG (Electronic Program Guide) data to Home Assistant._

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/A1V11ZZTPI)

## Features

- Import an XMLTV guide from any direct URL, including compressed files (`.gz`, `.xz`, `.zip`).
- Memory-efficient streaming parser: large national guides (tens of thousands of programs) are parsed without exhausting RAM.
- Pick exactly which channels are exposed as entities during setup and later from the options.
- Per-channel program sensors (optional):
  - **Current Program**
  - **Upcoming Program**
  - **Prime-Time Program** (configurable time of day)
- Per-channel image entities (optional):
  - **Channel Icon**
  - **Current / Upcoming / Prime-Time Program Image**
- A **Last Update** diagnostic sensor per guide.
- Built-in **diagnostics** for troubleshooting (source URL is redacted).
- Available in English, French.

## Installation

### HACS (recommended)

1. Add `https://github.com/domodom30/ha-xmltv-epg` as a custom repository, choose `Integration` as Category and add.
2. In the HACS UI, search for `XMLTV EPG` and install it.
3. Restart Home Assistant.
4. In the HA UI go to **Settings → Devices & Services**, click **+ Add Integration** and search for **XMLTV EPG**.

### Manual

1. Using the tool of choice open the directory for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory there, you need to create it.
3. In the `custom_components` directory create a new folder called `xmltv_epg`.
4. Download _all_ the files from the `custom_components/xmltv_epg/` directory in this repository.
5. Place the files you downloaded in the new directory you created.
6. Restart Home Assistant.
7. In the HA UI go to **Settings → Devices & Services**, click **+ Add Integration** and search for **XMLTV EPG**.

## Configuration

Configuration is done entirely through the UI.

1. Enter the **XMLTV Source URL** — a direct link to the guide file (compressed files are supported).
2. The integration downloads and parses the guide (a progress indicator is shown; this can take a while for large guides).
3. Select which **channels** you want to expose as entities.

After the initial setup, open the integration **options** to adjust settings, grouped into sections:

| Section | Setting | Description |
| --- | --- | --- |
| **Channels** | Channels | Which channels get sensor/image entities. |
| **Update** | Update Interval (hours) | How often the guide is re-downloaded from the source. |
| **Programs** | Current / Upcoming / Prime-Time sensors | Enable the per-channel program sensors. |
| **Programs** | Current Program Lookahead (minutes) | Treat a program as "current" this many minutes before it starts. |
| **Programs** | Prime-Time Program Time | Time of day used for the prime-time sensor. |
| **Images** | Channel Icons / Program Images | Enable the per-channel image entities. |

> Tip: to keep the number of entities manageable, only select the channels you actually
> need and consider disabling the "enable newly added entities" option in system settings.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the list of notable changes.

## Contributions are welcome!

If you want to contribute to this project, please read the [Contribution guidelines](CONTRIBUTING.md).

## Credits

This project is a fork of [shadow578/homeassistant_xmltv-epg](https://github.com/shadow578/homeassistant_xmltv-epg).

***

[xmltv_wiki]: https://wiki.xmltv.org/index.php/XMLTVFormat
