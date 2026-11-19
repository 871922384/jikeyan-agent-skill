"""Local (non-server) capability tools: fail closed without credentials."""

from __future__ import annotations

import pytest


def test_reference_tools_require_contact_email() -> None:
    from jikeyan_mcp.local_search import references

    with pytest.raises(ValueError):
        references.require_contact_email("")


def test_topic_collision_requires_contact_email() -> None:
    from jikeyan_mcp.local_search import topic_collision

    with pytest.raises(ValueError):
        topic_collision.require_contact_email("not-an-email")
