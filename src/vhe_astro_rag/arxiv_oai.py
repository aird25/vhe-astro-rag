from pathlib import Path
import time
import xml.etree.ElementTree as ET

import requests

BASE_URL = "https://oaipmh.arxiv.org/oai"
USER_AGENT = "vhe-astro-rag/0.1 (mailto:343157785+aird25@users.noreply.github.com)"
TIMEOUT_SECONDS = 60
OAI_NS = {"oai": "http://www.openarchives.org/OAI/2.0/"}
DELAY_SECONDS = 3


class OAIPMHError(Exception):
    """Raised when an OAI-PMH response contains an <error> element."""


def fetch_page(
    params: dict[str, str],
    out_path: Path,
) -> requests.Response:
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


def check_oai_error(
    root: ET.Element,
) -> None:
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


def get_resumption_token(
    root: ET.Element,
) -> str | None:
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


def download_set(
    set_spec: str,
    out_dir: Path,
    metadata_prefix: str = "arXivRaw",
    max_pages: int | None = None,
) -> list[Path]:
    """
    Download every page of an OAI-PMH ListRecords response for one set.

    Pages are saved as page_0001.xml, page_0002.xml, ... in out_dir,
    waiting DELAY_SECONDS between requests.

    Args:
        set_spec: OAI-PMH set, e.g. "physics:astro-ph:HE".
        out_dir: Directory where the raw pages will be written.
        metadata_prefix: Metadata format to request.
        max_pages: Stop after this many pages (for testing); None for all.

    Returns:
        Paths of the saved pages, in download order.

    Raises:
        OAIPMHError: If a response reports a protocol error.
    """
    params = {"verb": "ListRecords", "set": set_spec, "metadataPrefix": metadata_prefix}
    paths = []
    page = 1
    while True:
        out_path = out_dir / f"page_{page:04d}.xml"
        response = fetch_page(params, out_path)
        root = ET.fromstring(response.content)
        check_oai_error(root)
        paths.append(out_path)

        token = get_resumption_token(root)
        if token is None:
            break
        if max_pages is not None and page >= max_pages:
            break

        params = {"verb": "ListRecords", "resumptionToken": token}
        page += 1
        time.sleep(DELAY_SECONDS)
    return paths
