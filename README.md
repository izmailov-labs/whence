# whence

**Typed configuration that remembers where it came from.**

Every configuration library can tell you a value. `whence` can tell you *why*
it has that value — which file, which line, which profile, and what it
overrode.

```console
$ whence explain db.host --profile prod
db.host = "db.internal"
  <- config/app.prod.yaml:4:9 [profile=prod]
  shadowed:
      overrides                     - not set
      MYAPP_DB__HOST                - not set
      .env                          - not set
      config/app.yaml:2:9           = "localhost"
      <defaults>                    = "localhost"
```

Spring has this (`Origin`, `/actuator/env`), HOCON has it (`ConfigOrigin`), Rust's
`figment` has it (`Metadata`). Python has not — pydantic-settings' debug output
is top-level-only and unredacted, dynaconf has history but no line numbers, and
everything else discards provenance at the first merge.

`whence` is a **complement to pydantic, not a replacement**. Point it at a
pydantic model or a frozen dataclass; it does the layering, the provenance and
the diagnostics.

## Install

```console
pip install whence          # env, .env, TOML, JSON, .properties, XML
pip install whence[yaml]    # + YAML
```

The core has **no runtime dependencies**. That is a design constraint, not an
accident: every format but YAML is parsed on the standard library.

## Use

```python
from dataclasses import dataclass
from whence import Config, Secret, settings


@settings(prefix="db")
@dataclass(frozen=True, slots=True)
class Db:
    host: str = "localhost"
    port: int = 5432
    password: Secret | None = None


cfg = Config.load(app="myapp", profiles=["prod"])
db = cfg.bind(Db)

cfg.explain("db.host")  # the winner, and everything it shadowed
```

Loading is synchronous, and deliberately so. Configuration is read once,
before the application runs — there is no event loop at that point, so an
`await` would have nothing to yield to. A `Source` that reaches the network
blocks the startup it is already part of, which is exactly what starting up
means.

## What it does

| | |
|---|---|
| **Formats** | env vars, `.env`, TOML, JSON, YAML, Java `.properties`, XML |
| **Precedence** | seven named layers, `overrides > cli > env > .env > secrets-dir > files > defaults` |
| **Discovery** | explicit path → `$MYAPP_CONFIG` → project roots → per-user config dir → `pyproject.toml`, all configurable |
| **Profiles** | `app.prod.yaml` overlays, profile groups, and profiles never reorder sources |
| **Interpolation** | `${a.b}`, `${a.b:-default}`, `${?a.b}`, `${env:VAR}`, `${file:/run/secrets/x}` |
| **Secrets** | `Secret`, `_FILE` indirection, a sanitizer on every dump, reads gated by `unlock_secrets()` |
| **Binding** | frozen dataclasses on the stdlib; pydantic models when pydantic is installed |
| **Diagnostics** | batched errors carrying origin, and did-you-mean for unknown keys |

Exact `line:column` comes from YAML, `.env` and `.properties`. `tomllib`, `json`
and `ElementTree` expose no positions, so TOML, JSON and XML get file-level
origins — stated here rather than implied away.

## Reloading

There isn't any. To change configuration, redeploy.

`Config` is immutable and loaded once. A library that also owns a poll loop owns
a thread or an event loop, and the generational swap it needs is where every
prior art went wrong: .NET's `ChangeToken.OnChange` has fired **twice per save**
since 2017, Go viper's `WatchConfig` carries a documented data race, and koanf's
`Watch()` is not safe against concurrent reads. Each of those is a property of
changing an object other code is holding — so whence does not hold one.

What whence does guarantee is that a fresh `Config.load(...)` sees the current
state of the world, including through a **Kubernetes ConfigMap's `..data`
symlink**. kubelet republishes by pointing that symlink at a new directory, and
an inotify watch on the config *file* is bound to the old inode and goes
permanently deaf; re-reading resolves the symlink afresh. That is covered by a
test against real symlinks on a real Linux filesystem (`make test-docker`).

If you need a running process to pick up a change, call `Config.load(...)` again
on a schedule you own and swap your own pointer. It is a handful of lines, it
lives where your concurrency model already is, and whence stays out of it.

## Cross-platform

Config directories follow each platform's own convention: XDG on Linux,
`~/Library/Application Support` on macOS (plus XDG when you set it explicitly),
`%APPDATA%` and `%LOCALAPPDATA%` on Windows. Case-insensitive filesystems do not
produce phantom ambiguities, CRLF files parse, and every file is read as UTF-8
regardless of the platform's default encoding.

## Contributing

Pull requests are welcome. Fork the repository, branch off `main`, and open the PR against
`main`. CI runs on every pull request and every job is required, so run `make all` before
pushing: it is the local mirror of the CI gate, and a green run here is the cheapest way to
avoid a red one there.

```bash
make install     # once: sync the environment, install the pre-commit hooks
make all         # lint, typecheck, coverage, docs, build
```

The pre-commit hooks cover ruff and the lockfile on the way in; mypy is deliberately not among
them and is gated in CI instead, because it is slow enough that people start reaching for
`--no-verify`.

What CI adds on top of `make all`:

| Job | What it catches |
| --- | --- |
| `test` | The real matrix: Linux, macOS and Windows, at both ends of the supported Python range |
| `encoding` | Any `open()` or `read_text()` missing an explicit `encoding=` |
| `minimums` | Declared floors that are only ever tested at their latest versions |
| `no-deps` | A runtime import that quietly breaks the zero-dependency install |
| `build` | Broken packaging, a missing `py.typed`, a wheel that does not import |

The Python 3.15 leg is advisory until 3.15.0 ships; everything else must be green.

### What a reviewable PR looks like

- **A changelog entry** under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md), in the Keep a
  Changelog sections the file already uses. The version is bumped at release time, not here.
- **Annotated code, tests and examples included.** mypy runs `strict = true` over `src/`,
  `tests/` and `examples/` alike, and suppressions are specific: `# type: ignore[code]`, never
  bare.
- **Docstrings on public API.** The docs site generates its reference from them, and ruff's `D`
  rules (google convention) enforce them in `src/`.
- **A new runtime dependency is a decision, not a detail.** `dependencies = []` is the product
  claim, not a preference: every format but YAML is parsed on the standard library, and YAML
  lives behind the `whence[yaml]` extra. Open an issue before the PR. Dev tooling goes in
  `[dependency-groups]`, which is never published.
- **`uv.lock` committed** whenever a dependency changes; the `uv-lock` hook fails on drift.

Two rules exist because breaking them fails late and somewhere else. **Probe, never branch on
`sys.platform`** — case-insensitivity is a property of a directory, not a platform, and a name
that can be created is not always a name that round-trips. And **pass `encoding=` explicitly on
every read**: without it a bug appears only on a Windows code page, only for non-ASCII content,
and only in someone else's CI, which is what `make encoding` exists to prevent.

If a change touches mounts, musl, a read-only root or a non-UTF-8 locale, `make test-docker`
runs the six Linux scenarios CI cannot reproduce. Tests that need a real mount carry the
`container` marker and are excluded from the default run.

Anything large enough to have a design is worth an issue before the PR; small fixes can go
straight to one.

## License

MIT
