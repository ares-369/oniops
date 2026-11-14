# Security

## Reporting a vulnerability

Please report vulnerabilities privately, through the repository's
[private security advisory](https://github.com/ares-369/oniops/security/advisories/new) feature, not in
a public issue. Include steps to reproduce and the version or commit.

OniOps is maintained by one person in spare time, so responses are best-effort: I aim to acknowledge a
report within a week and keep you updated on a fix. Reporters are credited in the changelog unless they
prefer otherwise.

## Supported versions

OniOps is beta software. Fixes go into the latest release only.

## More

- [docs/threat-model.md](docs/threat-model.md): trust boundaries and the defences in code.
- [Known limitations](README.md#known-limitations) in the README.

Deployment advice:

- Serve it behind a TLS-terminating reverse proxy when it is reachable beyond `127.0.0.1`.
- Use a dedicated, least-privilege attack host for the SSH runner, with key-based login and
  `known_hosts` verification (`tofu` or `strict`).
- Keep `.env` and `secrets/` readable only by the service user.
