from __future__ import annotations

import socket
from typing import Any

import pytest

ALLOWED_HOSTS = {"127.0.0.1", "::1", "localhost"}


class NetworkBlockedError(RuntimeError):
    pass


def _host_of(address: Any) -> str:
    if isinstance(address, tuple) and address:
        return str(address[0])

    return str(address)


def _blocked(host: str) -> NetworkBlockedError:
    return NetworkBlockedError(
        f"test attempted a network connection to {host}; "
        "use an injected MockTransport instead"
    )


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    real_connect = socket.socket.connect
    real_getaddrinfo = socket.getaddrinfo

    def guarded_connect(self: socket.socket, address: Any) -> Any:
        host = _host_of(address)

        if host not in ALLOWED_HOSTS:
            self.close()

            raise _blocked(host)

        return real_connect(self, address)

    def guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        if str(host) not in ALLOWED_HOSTS:
            raise _blocked(str(host))

        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
