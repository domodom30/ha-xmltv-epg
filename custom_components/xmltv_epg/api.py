"""XMLTV Client."""

from __future__ import annotations

import asyncio
import gzip
import io
import lzma
import socket
import zipfile
from logging import Logger

import aiohttp
from pydantic import ValidationError

from .model import TVGuide

# Timeout for establishing the connection and receiving the response headers.
# The response body itself is read without a timeout, as EPG files may be large.
REQUEST_TIMEOUT = 30  # seconds


class XMLTVClientError(Exception):
    """Exception to indicate a general API error."""


class XMLTVClientCommunicationError(XMLTVClientError):
    """Exception to indicate a communication error."""


class XMLTVClient:
    """XMLTV Client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        url: str,
        logger: Logger | None = None,
    ) -> None:
        """XMLTV Client."""
        self._session = session
        self._url = url
        self.__logger = logger

    async def async_get_data(self) -> TVGuide:
        """Fetch XMLTV Guide data."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(url=self._url)
            response.raise_for_status()

            content_type = response.content_type
            content_encoding = response.headers.get("Content-Encoding", None)
            url = str(response.url)
            raw = await response.read()

            if self.__logger:
                self.__logger.debug(
                    "Decoding response from %s: content-type=%s, content-encoding=%s",
                    url,
                    content_type,
                    content_encoding,
                )

            loop = asyncio.get_running_loop()
            guide = await loop.run_in_executor(
                None, self._decode_and_parse, raw, content_type, url
            )
            if guide is None:
                raise XMLTVClientError(
                    "Failed to parse TV Guide data",
                )

            return guide
        except XMLTVClientError as exception:
            raise exception
        except asyncio.TimeoutError as exception:
            raise XMLTVClientCommunicationError(
                "Timeout fetching xmltv data: " + exception.__str__(),
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise XMLTVClientCommunicationError(
                "Error fetching xmltv data: " + exception.__str__(),
            ) from exception
        except ValidationError as exception:
            raise XMLTVClientError(
                "Error parsing xmltv data: " + exception.__str__()
            ) from exception
        except Exception as exception:
            raise XMLTVClientError(
                "Unknown error fetching xmltv data: " + exception.__str__()
            ) from exception

    def _decode_and_parse(self, raw: bytes, content_type: str, url: str) -> TVGuide:
        """
        Decode the raw response bytes and parse them into a TVGuide.

        Runs in an executor thread: it must stay purely synchronous (no async /
        event-loop access) as it performs the CPU-heavy decompression and parsing.
        """
        xml_bytes = self._decode_bytes(raw, content_type, url)
        return TVGuide.from_xml_streaming(xml_bytes)

    def _decode_bytes(self, raw: bytes, content_type: str, url: str) -> bytes:
        """Decode the raw (already read) response bytes into XML bytes."""
        decode_fn = None
        if content_type in ["text/xml", "application/xml"]:

            def decode_plain() -> bytes:
                return raw

            decode_fn = decode_plain

        elif (
            content_type
            in [
                "application/gzip",
                "application/x-gzip",
            ]
            or "xml.gz" in url
        ):
            # xml.gz, XML compressed with gzip
            def decode_gzip() -> bytes:
                return gzip.decompress(raw)

            decode_fn = decode_gzip

        elif content_type in ["application/x-xz"] or "xml.xz" in url:

            def decode_xz() -> bytes:
                return lzma.decompress(raw)

            decode_fn = decode_xz

        elif content_type in ["application/zip"] or "xml.zip" in url:

            def decode_zip() -> bytes:
                with io.BytesIO(raw) as iofile, zipfile.ZipFile(iofile, "r") as zip:
                    namelist = zip.namelist()
                    i = 0

                    if len(namelist) == 0:
                        raise XMLTVClientError("zip archive is empty")
                    if len(namelist) > 1:
                        for ix, name in enumerate(namelist):
                            if name.endswith(".xml"):
                                i = ix
                                break

                        if self.__logger:
                            self.__logger.warning(
                                "zip archive contains multiple files (%s), using i=%d",
                                namelist,
                                i,
                            )

                    with zip.open(namelist[i]) as xml_file:
                        return xml_file.read()

            decode_fn = decode_zip
        else:
            raise XMLTVClientError(
                f"Don't know how to handle content type '{content_type}' (from {url})",
            )

        try:
            return decode_fn()
        except Exception as decode_exception:
            if self.__logger:
                self.__logger.debug(
                    "Failed to decode xml data using expected method, using raw bytes as text. Error: %s",
                    decode_exception,
                )

            return raw
