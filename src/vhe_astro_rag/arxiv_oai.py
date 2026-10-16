from pathlib import Path

import requests

BASE_URL = "https://oaipmh.arxiv.org/oai"
USER_AGENT = "vhe-astro-rag/0.1 (mailto:343157785+aird25@users.noreply.github.com)"
TIMEOUT_SECONDS = 60


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
