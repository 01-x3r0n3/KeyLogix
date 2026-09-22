from __future__ import annotations

from keylogix.constants import IMPLEMENTATION_VERSION, SCHEMA_ENVIRONMENT
from keylogix.environment import collect_environment, git_revision


def test_collect_environment():
    env = collect_environment()
    assert env["schema"] == SCHEMA_ENVIRONMENT
    assert env["implementation_version"] == IMPLEMENTATION_VERSION
    assert "platform" in env
    assert "system" in env
    assert "python_version" in env
    assert "security_product" in env
    assert env["security_product"]["present"] is False


def test_git_revision_handling():
    rev = git_revision()
    assert isinstance(rev, str)
    assert len(rev) > 0
