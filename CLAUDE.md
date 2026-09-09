# whence — working notes

Typed configuration that remembers where it came from: layered loading from env, `.env`, TOML,
JSON, YAML, `.properties` and XML, with full provenance. **Zero runtime dependencies.**

A **single-package repository** (uv >= 0.12): the repository root *is* the package. It was
extracted from the `validia.dev` uv workspace, where it lived at `libs/whence`; the sibling
packages `franca` and `validia` stayed behind.

## Commands

```bash
make install     # uv sync --group dev --group docs + pre-commit install
make lint        # ruff check + ruff format --check
make fmt         # ruff check --fix + ruff format
make typecheck   # mypy (strict)
make test        # pytest
make cov         # pytest --cov (fail_under=90)
make encoding    # fail on any read missing an explicit encoding=
make test-docker # the Linux scenarios CI cannot reproduce (see below)
make docs        # mkdocs build --strict
make build       # uv build + twine check
make all         # everything CI runs
```

Run one test: `uv run pytest tests/test_whence_config.py::test_load_is_synchronous`
One container scenario: `make test-docker-one S=musl`

## Cross-platform testing

Three layers, because no single one is enough and each covers what the others cannot.

| Layer | Covers | Cannot cover |
| --- | --- | --- |
| **Seams** (`_platform.flavour`, `WindowsEnviron` in the tests) | Windows and macOS *semantics* from any runner: path flavour, environment case-folding, config-directory conventions | Real filesystem behaviour |
| **CI matrix** (`.github/workflows/ci.yml`) | The three real operating systems, at both ends of the Python range | Container mounts, musl, non-UTF-8 locales |
| **Docker** (`make test-docker`) | musl, a POSIX locale, a read-only root, an unprivileged user, a real `/run/secrets` tmpfs, a live Kubernetes ConfigMap symlink swap | macOS and Windows -- neither runs in a Linux container |

Tests needing a real mount carry the `container` marker and are excluded from the default run;
`make test-docker` supplies `WHENCE_CONTAINER=1` and the mounts.

Two rules that keep the matrix honest. **Probe, never branch on `sys.platform`** —
case-insensitivity is a property of a directory, not a platform, and a name that can be created
is not always a name that round-trips. And **every read passes `encoding=` explicitly**:
`make encoding` turns a missing one into an error, because otherwise it only fails on a Windows
code page, only for non-ASCII content, and only in someone else's CI.

## Conventions

- **Layout is `src/`.** Tests import the *installed* package (`--import-mode=importlib`), not
  the working tree.
- **Tooling configuration lives once, in `pyproject.toml`.** Ruff, mypy, pytest and coverage are
  configured there alongside the packaging metadata; there is no second config file.
- **mypy is `strict = true` and covers `tests/` and `examples/` too.** New code lands annotated;
  do not add `disallow_untyped_defs = false` or blanket `ignore_missing_imports`. Suppressions
  must be specific: `# type: ignore[code]`, never bare.
- **Loading is synchronous, deliberately.** Configuration is read once, before the application
  runs, so there is no event loop for an `await` to yield to. This is enforced, not merely
  intended — ruff `TID251` bans `import asyncio` in `src/`; tests and `examples/` are exempt
  because an application drives its own loop.
- **Runtime dependencies are inherited by every consumer.** `dependencies = []` is the product
  claim: every format but YAML is parsed on the standard library, and YAML is the single
  exception, behind the `whence[yaml]` extra. Dev tooling goes in `[dependency-groups]`, which
  is not published. The `no-deps` CI job installs the wheel with nothing else and imports it.
- **Ruff is pinned exactly** (`ruff==0.16.6`). It has no 1.0 and does not follow semver below
  it, so a floating version would silently change the lint gate. The `select` list is explicit
  for the same reason — ruff 0.16 grew its *default* set from 59 to 413 rules.
- **Docstrings are load-bearing**: the docs site generates the API reference from them via
  mkdocstrings, and ruff's `D` rules (google convention) enforce them in `src/`.
- **Public API** is whatever `src/whence/__init__.py` lists in `__all__`. Everything else is
  internal and may change without a major bump.

## Release

One package, so tags are plain: `vX.Y.Z`.

Version is static in `pyproject.toml`; `__version__` reads it back at runtime via
`importlib.metadata`. To release: bump the version, write the `CHANGELOG.md` entry, tag
`vX.Y.Z`, push the tag. `release.yml` verifies the tag against `pyproject.toml`, builds, and
publishes via PyPI Trusted Publishing (OIDC — there is no API token in this repo).

Two constraints worth remembering: the **trusted publisher must be configured on PyPI before
the first tag** (owner `izmailov-labs`, repository `whence`, workflow `release.yml`,
environment `pypi`), and **PyPI rejects new files added to a release older than 14 days**, so
everything for a version ships in one run.
