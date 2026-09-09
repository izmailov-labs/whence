# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-09-08

### Added

- Provenance spine: `Origin`, `Tracked`, and a merge that records what each
  value shadowed.
- `Source` protocol with a `SourceChain` supporting name-addressed
  insertion, plus environment, `.env`, file, mapping and secrets-directory
  sources.
- Format loaders for TOML, JSON, `.properties` and XML on the standard library,
  and YAML behind the `whence[yaml]` extra. YAML, `.env` and `.properties`
  carry exact line and column numbers.
- `Discovery`: a declarative five-step search chain over explicit paths,
  `$APP_CONFIG`, project roots, per-user config directories and
  `pyproject.toml`, with cross-platform directory conventions.
- `Config` with `get`, `require`, `explain`, `dump`, `bind` and `with_fallback`.
- Interpolation with `${a.b}`, `${a.b:-default}`, `${?a.b}`, `${env:VAR}` and
  `${file:/path}`, resolved lazily after the merge.
- Profiles, profile groups, and the invariant that profiles never reorder
  sources.
- Binding to frozen dataclasses (standard library) and to pydantic models when
  pydantic is installed, with batched errors that carry origins.
- `Secret`, `unlock_secrets()`, `_FILE` indirection and a sanitizer applied to
  every dump.
- `@settings` and `@from_config` decorators.
- `ArgvSource`, reading `--set key=value` out of `sys.argv`.
- `RelativePath`, a path resolved against the file that declared it rather than
  the process working directory -- possible only because values carry origins.
- A `whence` CLI: `explain`, `dump` and `discovery`.

### Design notes

- **Loading is synchronous, and there is no reload.** Configuration is read once
  before the application runs, where there is no event loop for an `await` to
  yield to. Reload was cut with it: a poll loop means whence owning a thread or a
  loop and mutating a generation other code holds, which is precisely where
  .NET's `ChangeToken`, viper's `WatchConfig` and koanf's `Watch()` each went
  wrong. A process that must pick up a change calls `Config.load(...)` again on a
  schedule it owns.

### Stability

- The public API is whatever `whence.__init__` lists in `__all__`. From this
  release on it follows semantic versioning: anything else is internal, and a
  breaking change to the public surface requires a 2.0.0.

[Unreleased]: https://github.com/izmailov-labs/whence/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/izmailov-labs/whence/releases/tag/v1.0.0
