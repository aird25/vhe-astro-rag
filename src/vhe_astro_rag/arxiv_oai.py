from pathlib import Path
import xml.etree.ElementTree as ET

import requests

BASE_URL = "https://oaipmh.arxiv.org/oai"
USER_AGENT = "vhe-astro-rag/0.1 (mailto:343157785+aird25@users.noreply.github.com)"
TIMEOUT_SECONDS = 60
OAI_NS = {"oai": "http://www.openarchives.org/OAI/2.0/"}


class OAIPMHError(Exception):
    """Raised when an OAI-PMH response contains an <error> element."""


def fetch_page(params: dict[str, str], out_path: Path) -> requests.Response:
    """
    Send an OAI-PMH request and save the raw response body.

    The response body is written as bytes, without any decoding or
    modification. Any HTTP error, including 503, raises an exception;
    retry handling is not implemented yet.

    Args:
        params: OAI-PMH query parameters, e.g.
            {"verb": "ListRecords", "metadataPrefix": "arXivRaw"}.
        out_path: File where the raw XML response will be written.

    Returns:
        The response object, so the caller can inspect status and headers.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(
        BASE_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    out_path.write_bytes(response.content)
    return response


def check_oai_error(root: ET.Element) -> None:
    """
    Raise OAIPMHError if an OAI-PMH response contains an <error> element.

    Args:
        root: Root element of a parsed OAI-PMH response.

    Raises:
        OAIPMHError: If the response reports a protocol error.
    """
    error = root.find("oai:error", OAI_NS)
    if error is not None:
        code = error.get("code", "unknown")
        message = (error.text or "").strip()
        raise OAIPMHError(f"{code}: {message}")


def get_resumption_token(root: ET.Element) -> str | None:
    """
    Return the resumptionToken of an OAI-PMH list response.

    The token is returned exactly as received, since the protocol
    requires sending it back unmodified.

    Args:
        root: Root element of a parsed OAI-PMH response.

    Returns:
        The token, or None if there are no more pages.
    """
    element = root.find("*/oai:resumptionToken", OAI_NS)
    if element is None or not (element.text or "").strip():
        return None
    return element.text
