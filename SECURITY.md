# Security

This is a portfolio project, but it follows practices you'd expect in a
production service.

## Built-in protections

- **Authentication**: upload and query endpoints require a shared-secret
  `X-API-Key` header, compared with `secrets.compare_digest` (constant-time,
  not `==`) to avoid a timing side-channel (`app/api/security.py`). Unset in
  local dev — a warning is logged at startup when that's the case; required
  in any internet-facing deployment.
- **Rate limiting, including failed auth**: per-IP limits on the endpoints
  that trigger paid LLM calls (`slowapi`'s `@limiter.limit(...)`,
  configurable via `RATE_LIMIT_UPLOAD` / `RATE_LIMIT_QUERY`), plus a
  custom `BlanketRateLimitMiddleware` (`app/core/rate_limit.py`) applied at
  the ASGI layer, before routing or dependency resolution — so requests
  with a missing/wrong API key are throttled too, not just successfully
  authenticated ones. This is a hand-rolled middleware rather than
  slowapi's own `SlowAPIMiddleware` on purpose: that middleware resolves
  the target handler by walking `app.routes`, which silently finds nothing
  (and therefore enforces nothing) under FastAPI's newer lazy
  router-inclusion internals — verified while building this, not assumed.
- **Path traversal protection on uploads**: the client-supplied filename is
  reduced to its basename (`Path(filename).name`) before touching the
  filesystem, and the resulting path is re-checked against the intended
  per-document directory before writing. A filename like
  `../../../etc/cron.d/x` cannot escape `storage/uploads/`.
- **Bounded upload reads**: files are read in capped chunks that abort as
  soon as the configured limit is exceeded, instead of buffering the full
  body first — a client can omit `Content-Length` (chunked
  transfer-encoding), so the limit is enforced against actual bytes read,
  not a client-reported header.
- **Deletion actually deletes**: `DELETE /documents/{id}` removes the DB
  rows *and* the stored file on disk, not just the database record.
- **Least privilege containers**: the Docker image runs as a non-root user;
  Postgres and Redis ports are bound to `127.0.0.1` in `docker-compose.yml`
  (not `0.0.0.0`) since neither the api nor worker containers need them
  published to the host network, and Redis has no authentication by default.
- **No debug tracebacks by default**: `DEBUG=false` is the shipped default —
  Starlette's debug mode returns full stack traces (file paths, source
  lines) in the HTTP response on unhandled errors.
- **No upstream error leakage**: 5xx errors from the AI provider are logged
  in full server-side but returned to API clients as a generic message —
  the raw provider error text isn't forwarded.
- **Prompt-injection–aware system prompt**: the RAG system prompt explicitly
  tells the model that retrieved document content is untrusted data, not
  instructions, and to ignore any commands embedded in it (see "Known
  limitations" below — this reduces, not eliminates, the risk).
- **Input validation**: strict Pydantic schemas at every API boundary, a
  file-extension allow-list, and a max upload size.
- **Secrets stay out of the image and the repo**: configuration is read from
  environment variables via `pydantic-settings`; `.env` is git-ignored and
  only `.env.example` (no real values) is committed.
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy` set on every response.
- **CORS**: disabled by default (server-to-server API); opt-in allow-list
  via `CORS_ORIGINS`.
- **Safe serialization**: Celery is configured for `json` only
  (`task_serializer`/`accept_content`), never the default `pickle`, which
  has a well-known deserialization-RCE history.
- **Dependency hygiene**: Dependabot keeps `pip`, Docker, and GitHub Actions
  dependencies current; CI runs `pip-audit` and CodeQL on every push.

## Known limitations

Documented on purpose, not omissions:

- **No per-user data isolation.** Auth is a single shared `API_KEY`, not
  per-user accounts — anyone with the key can read/query/delete any
  document. Fine for a personal/demo deployment; a real multi-tenant
  deployment needs proper user auth (see the README's "Posibles
  extensiones").
- **Indirect prompt injection is mitigated, not solved.** The system prompt
  instructs the model to treat retrieved content as inert data, which
  reduces but cannot fully eliminate the risk of a malicious document
  trying to manipulate the model's output — this is an open problem across
  the RAG/LLM industry, not something any single prompt fully closes.
- **Default DB/Redis credentials are dev-only.** They're safe as shipped
  because those ports are loopback-only in `docker-compose.yml`, but if you
  deploy Postgres or Redis reachable beyond that single host (Kubernetes,
  a separate managed instance, etc.), rotate `POSTGRES_PASSWORD` and enable
  Redis `requirepass` — port isolation alone won't protect you there.

## Reporting a vulnerability

This is a personal portfolio project without a dedicated security team.
If you find an issue, please open a GitHub issue or reach out directly
rather than exploiting it — happy to fix it promptly.
