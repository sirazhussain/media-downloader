"""Keep URL-validation tests offline: every hostname resolves to a public IP."""

import socket

import pytest


@pytest.fixture(autouse=True)
def _public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(host, port, *args, **kwargs):  # type: ignore[no-untyped-def]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr("app.core.security.socket.getaddrinfo", fake_getaddrinfo)
