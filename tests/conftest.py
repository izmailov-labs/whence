"""Shared fixtures.

The autouse fixture below is the single most important piece of hygiene in a
test suite for a configuration library: without it, a maintainer who happens to
have `MYAPP_DB__HOST` exported in their shell gets different results than CI,
and the difference shows up as an unrelated test failing.
"""

import os
from collections.abc import Iterator, Mapping
from unittest import mock

import pytest

# Captured at import, before any test has had a chance to empty os.environ.
# A handful of checks are deliberately about the *real* machine, and on Windows
# there is no pwd fallback: with USERPROFILE and LOCALAPPDATA cleared, the home
# directory is genuinely unknowable rather than merely unset.
_REAL_ENVIRON: Mapping[str, str] = dict(os.environ)


@pytest.fixture(autouse=True)
def clean_env() -> Iterator[None]:
    """Run every test against a completely empty process environment."""
    with mock.patch.dict(os.environ, clear=True):
        yield


@pytest.fixture
def real_environ() -> Mapping[str, str]:
    """The process environment as it stood before `clean_env` emptied it."""
    return _REAL_ENVIRON
