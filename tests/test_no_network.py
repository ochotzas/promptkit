from __future__ import annotations

import re
import socket

import pytest

from tests.conftest import NetworkBlockedError


def test_guard_blocks_outbound_connections() -> None:
    with pytest.raises(NetworkBlockedError, match="network connection"):
        socket.create_connection(("api.openai.com", 443), timeout=2)


def test_guard_names_the_host() -> None:
    with pytest.raises(NetworkBlockedError, match=re.escape("api.anthropic.com")):
        socket.create_connection(("api.anthropic.com", 443), timeout=2)


def test_guard_allows_localhost() -> None:
    caught: Exception | None = None

    try:
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    except OSError as e:
        caught = e

    assert not isinstance(caught, NetworkBlockedError)
