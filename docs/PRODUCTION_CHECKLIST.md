# Production Checklist

## Security

- Use a managed secret store.
- Enforce TLS and secure proxy headers.
- Apply rate limits to login and write endpoints.
- Add refresh-token revocation and device sessions.
- Add fine-grained record ownership checks.
- Encrypt sensitive backups and document storage.

## Reliability

- Run multiple stateless API replicas.
- Configure PostgreSQL backups and recovery tests.
- Use Redis persistence only for workloads that require it.
- Add health, readiness, and dependency checks.
- Configure retries and dead-letter handling for background jobs.

## Observability

- Structured JSON logs with request ID and actor ID.
- Metrics for request latency, error rates, occupancy, collection, and queue depth.
- Distributed tracing for external provider integrations.
- Alerts for failed payments, queue buildup, and database saturation.

## Delivery

- Run tests and migration validation in CI.
- Build immutable container images.
- Apply migrations as a controlled release step.
- Use staged environments and rollback procedures.
