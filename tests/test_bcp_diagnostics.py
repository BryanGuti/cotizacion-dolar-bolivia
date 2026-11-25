import socket
import ssl
from unittest.mock import MagicMock, Mock, patch

import requests

from scraper import diagnose_bcp
from scraper.config import SOURCES
from scraper.sources.bcp import REQUEST_HEADERS, REQUEST_TIMEOUT_SECONDS


def test_diagnostic_checks_network_layers_and_safe_http_headers(capsys):
    connection = Mock()
    tls_connection = MagicMock()
    tls_connection.__enter__.return_value = tls_connection
    tls_connection.version.return_value = "TLSv1.3"
    context = Mock()
    context.wrap_socket.return_value = tls_connection
    response = Mock(
        status_code=200,
        headers={
            "Content-Type": "text/html",
            "Content-Length": "2048",
            "Set-Cookie": "private-session=value",
        },
    )

    with patch.object(
        diagnose_bcp.socket,
        "getaddrinfo",
        return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("192.0.2.1", 443))
        ],
    ), patch.object(
        diagnose_bcp.socket, "create_connection", return_value=connection
    ) as create_connection, patch.object(
        diagnose_bcp.ssl, "create_default_context", return_value=context
    ), patch.object(
        diagnose_bcp.requests, "get", return_value=response
    ) as http_get:
        diagnose_bcp.diagnose_bcp_connection()

    output = capsys.readouterr().out
    assert "DNS resolution succeeded: 1 address(es)." in output
    assert "TCP connection succeeded." in output
    assert "TLS handshake succeeded: TLSv1.3." in output
    assert "HTTP response status: 200." in output
    assert "Response Content-Type: text/html" in output
    assert "Set-Cookie" not in output
    assert "private-session" not in output
    create_connection.assert_called_once_with(
        ("www.bcp.com.bo", 443),
        timeout=diagnose_bcp.DIAGNOSTIC_CONNECT_TIMEOUT_SECONDS,
    )
    http_get.assert_called_once_with(
        SOURCES["bcp"]["url"],
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
        stream=True,
    )
    response.close.assert_called_once()
    connection.close.assert_called_once()


def test_diagnostic_distinguishes_dns_tcp_tls_and_http_failures(capsys):
    with patch.object(
        diagnose_bcp.socket,
        "getaddrinfo",
        side_effect=socket.gaierror("name resolution failed"),
    ), patch.object(
        diagnose_bcp.socket,
        "create_connection",
        side_effect=ConnectionResetError("peer reset TCP connection"),
    ), patch.object(
        diagnose_bcp.requests,
        "get",
        side_effect=requests.ConnectionError("TLS connection reset"),
    ):
        diagnose_bcp.diagnose_bcp_connection()

    output = capsys.readouterr().out
    assert "DNS resolution failed: gaierror." in output
    assert "TCP connection failed: ConnectionResetError." in output
    assert "HTTP request failed before a response: ConnectionError." in output


def test_diagnostic_reports_tls_handshake_failure(capsys):
    connection = Mock()
    context = Mock()
    context.wrap_socket.side_effect = ssl.SSLError("handshake reset")

    with patch.object(
        diagnose_bcp.socket,
        "getaddrinfo",
        return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("192.0.2.1", 443))
        ],
    ), patch.object(
        diagnose_bcp.socket, "create_connection", return_value=connection
    ), patch.object(
        diagnose_bcp.ssl, "create_default_context", return_value=context
    ), patch.object(
        diagnose_bcp.requests,
        "get",
        side_effect=requests.ConnectionError("TLS connection reset"),
    ):
        diagnose_bcp.diagnose_bcp_connection()

    output = capsys.readouterr().out
    assert "TCP connection succeeded." in output
    assert "TLS handshake failed: SSLError." in output
    assert "HTTP request failed before a response: ConnectionError." in output
    assert "handshake reset" not in output
