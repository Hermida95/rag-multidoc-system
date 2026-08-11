# Security

This is a portfolio project, but it follows practices you'd expect in a
production service:

## Built-in protections

- **Authentication**: upload and query endpoints require a shared-secret
  `X-API-Key` header (`app/api/security.py`). Unset in local dev; required
  in any internet-facing deployment.
- **Rate limiting**: per-IP limits on the endpoints that trigger paid LLM
  calls (`slowapi`, configurable via `RATE_LIMIT_UPLOAD` / `RATE_LIMIT_QUERY`).
- **Input validation**: strict Pydantic schemas at every API boundary, file
  type allow-list, and a max upload size enforced before the file touches disk.
- **Least privilege**: the Docker image runs as a non-root user; the API
  container never needs write access outside `storage/uploads`.
- **Secrets stay out of the image and the repo**: configuration is read from
  environment variables via `pydantic-settings`; `.env` is git-ignored and
  only `.env.example` (no real values) is committed.
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy` set on every response.
- **CORS**: disabled by default (server-to-server API); opt-in allow-list
  via `CORS_ORIGINS`.
- **Dependency hygiene**: Dependabot keeps `pip` and GitHub Actions
  dependencies current; CI runs `pip-audit` and CodeQL on every push.

## Reporting a vulnerability

This is a personal portfolio project without a dedicated security team.
If you find an issue, please open a GitHub issue or reach out directly
rather than exploiting it — happy to fix it promptly.
