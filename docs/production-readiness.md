# Production readiness

This phase prepares Kiko for a controlled production launch. It does **not** deploy anything,
create infrastructure, contact providers or use real credentials.

## Service-level objectives

Initial objectives apply after a two-week measurement period with at least 20 completed samples
per workflow metric:

| Signal                 | Objective     | Alert threshold                            |
| ---------------------- | ------------- | ------------------------------------------ |
| API availability       | 99.9% monthly | readiness fails for 2 minutes              |
| API 5xx rate           | below 1%      | above 2% for 5 minutes                     |
| API read p95           | below 500 ms  | above 750 ms for 10 minutes                |
| Supervisor completion  | at least 99%  | below 97% over 30 minutes                  |
| Agent completion       | at least 98%  | below 95% over 30 minutes                  |
| Tool execution success | at least 99%  | below 97% over 30 minutes                  |
| Backup recovery point  | 24 hours      | latest verified backup older than 26 hours |
| Recovery time          | 4 hours       | restore rehearsal exceeds 3 hours          |

Error-budget policy: at 50% monthly budget consumption, pause non-critical releases; at 100%,
freeze releases except incident fixes until reliability returns inside the objective.

## Observability

Every HTTP response has a validated/generated `X-Request-ID`, and access logs are structured JSON
with a bounded route template, status and duration. Security headers are applied centrally. The
Prometheus text endpoint is `/metrics`; production configuration refuses to start without
`OBSERVABILITY_METRICS_TOKEN`. Scrapers send `Authorization: Bearer <token>` over the private
network. Metrics are per process, so the monitoring system must sum across replicas.

Alert additionally on outbox exhaustion, stale/running executions, Celery queue age, database
connections, Redis availability, OAuth failures, disk pressure and certificate expiry. Logs and
metrics must never contain request bodies, OAuth states, credentials or provider payloads.

## Preflight configuration

`APP_ENV=production` activates fail-fast checks:

- secure cookies and HTTPS web origins;
- fail-closed authentication rate limiting;
- an explicit trusted-host allowlist;
- non-default database credentials;
- authenticated metrics;
- a real AI provider.

Keep GitHub, Codex, Email and Calendar disabled until their separate least-privilege credentials,
allowlists and worker isolation have been reviewed. Run `python -m app.scripts.run_policy_evaluations`
and `python -m app.scripts.evaluate_production --window-days 30` before every release decision.
An insufficient sample is not a passing result.

## Backup and recovery

Run backups from an isolated operations job with PostgreSQL client tools and encrypted storage:

```bash
python -m app.scripts.backup_database /secure-staging/kiko-YYYYMMDD.dump
```

The command creates a custom-format dump and SHA-256 sidecar without placing the password in the
process arguments. Upload both files to versioned, encrypted, access-logged object storage; apply
a 30-day retention policy and a separate deletion role.

Restore only into an empty, isolated target first:

```bash
python -m app.scripts.restore_database /secure-staging/kiko-YYYYMMDD.dump \
  --confirm-database kiko_restore_test
```

The exact target database name and checksum are mandatory. Quarterly, restore the latest backup,
run `alembic current`, exercise `/ready`, authenticate a synthetic operator and record actual RPO,
RTO and evidence. Never treat “backup job succeeded” as proof of recoverability.

## Deployment runbook

1. Confirm the release SHA, green CI, one Alembic head and a clean dependency/secret scan.
2. Confirm a recent verified backup and the rollback owner.
3. Build immutable API/Web images, scan them and pin the approved image digests.
4. Run `alembic upgrade head` as a single release job. Application replicas must not race migrations.
5. Start API, worker and outbox replicas with integrations disabled; require `/ready` before traffic.
6. Send a canary slice, verify error/latency/queue signals, then increase traffic gradually.
7. Enable integrations one at a time only after account allowlists and approval paths are verified.
8. Run a synthetic command through planning, approval and a non-external GREEN tool.

Rollback application images first. Database downgrade is allowed only when the migration is proven
reversible and no newer writes would be lost; otherwise roll forward. Stop workers before any
schema restore. A production restore requires incident-commander approval and a current backup.

## Load, reliability, cost and quality evaluation

For local or isolated staging only:

```bash
python -m app.scripts.load_smoke --requests 500 --concurrency 20
```

Remote targets are refused unless the operator supplies `--allow-remote`; that flag is authorization,
not a recommendation to load-test production. The production evaluator reads aggregate run data and
reports success rates, p95 latency, model cost per currency and sample sufficiency. The versioned
policy-quality suite verifies risk escalation and critical-agent assignment. Before launch, add a
human-labelled domain set for answer correctness and hallucination rate; deterministic guardrails
alone do not establish model quality.

## Incident response

Declare severity and commander, preserve request/correlation IDs, disable affected integrations,
pause automations if propagation is possible, and rotate exposed credentials. Do not delete audit
records. Communicate timestamps and verified impact, restore service through the smallest reversible
change, then write a blameless review with follow-up owners. For suspected cross-workspace access,
take retrieval offline immediately and preserve database/audit snapshots for investigation.

## Launch blockers outside this repository

- provisioned and patched runtime hosts or orchestrator;
- managed/private PostgreSQL and Redis with tested failover;
- DNS, TLS, firewall and private service networking;
- secret manager and rotation procedure;
- encrypted backup storage plus a completed restore rehearsal;
- metrics/log collection and alert routing with named on-call owners;
- staging load test and measured capacity;
- legal/privacy review, retention policy and user support procedure.

Until these are evidenced, the repository is code-ready for staging validation, not approved for a
production deployment.
