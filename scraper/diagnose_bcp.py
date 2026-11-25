"""Print network-layer diagnostics for the configured BCP HTTPS source."""

import socket
import ssl
from urllib.parse import urlsplit

import requests

from scraper.config import SOURCES
from scraper.sources.bcp import REQUEST_HEADERS, REQUEST_TIMEOUT_SECONDS


DIAGNOSTIC_CONNECT_TIMEOUT_SECONDS = 10
SAFE_RESPONSE_HEADERS = (
    "Content-Type",
    "Content-Length",
    "Retry-After",
    "Server",
    "Date",
)


def diagnose_bcp_connection() -> None:
    """Check DNS, TCP, TLS, and HTTP without printing response content."""

    url = SOURCES["bcp"]["url"]
    parsed_url = urlsplit(url)
    hostname = parsed_url.hostname
    port = parsed_url.port or 443

    if not hostname:
        print("BCP diagnostic: configured URL has no hostname.")
        return

    print(f"BCP diagnostic target: {parsed_url.scheme}://{hostname}:{port}/")

    try:
        addresses = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        print(f"DNS resolution failed: {type(exc).__name__}.")
    else:
        unique_addresses = {address[4][0] for address in addresses}
        print(f"DNS resolution succeeded: {len(unique_addresses)} address(es).")

    try:
        connection = socket.create_connection(
            (hostname, port),
            timeout=DIAGNOSTIC_CONNECT_TIMEOUT_SECONDS,
        )
    except OSError as exc:
        print(f"TCP connection failed: {type(exc).__name__}.")
    else:
        print("TCP connection succeeded.")
        try:
            context = ssl.create_default_context()
            with context.wrap_socket(
                connection,
                server_hostname=hostname,
            ) as tls_connection:
                print(
                    "TLS handshake succeeded: "
                    f"{tls_connection.version() or 'protocol unknown'}."
                )
        except (OSError, ssl.SSLError) as exc:
            print(f"TLS handshake failed: {type(exc).__name__}.")
        finally:
            connection.close()

    print("Starting one HTTP probe with the BCP scraper headers.")
    try:
        response = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            stream=True,
        )
    except requests.RequestException as exc:
        print(f"HTTP request failed before a response: {type(exc).__name__}.")
        return

    try:
        print(f"HTTP response status: {response.status_code}.")
        for header in SAFE_RESPONSE_HEADERS:
            value = response.headers.get(header)
            if value:
                print(f"Response {header}: {value}")
    finally:
        response.close()


if __name__ == "__main__":
    diagnose_bcp_connection()
