# Operations and recovery runbook

Status: foundation procedures and deployment design. No live service/database
has been deployed; backend host, managed DB project/region and operational owners
must be recorded before Week 2 connectivity work. Never invent production URLs,
credentials or backup availability from a free-tier name.

## Development startup

Use the fresh Python 3.14 Conda environment and README commands. Unit tests and
foundation demo are offline; no .env is required. When adapters begin, provide
explicit backend environment settings and CA material through the deployment
secret store. Only the backend has database credentials/signing keys. Desktops
receive API URL/timeouts/locale and short-lived session material.

## Runtime health and failure states

STARTING validates configuration, API/schema compatibility and dependencies.
READY serves normal work. DEGRADED disables only affected optional services and
labels stale/polling freshness. DISCONNECTED blocks authoritative writes.
MAINTENANCE/RECOVERING block readiness during upgrade/restore. STOPPING bounds
in-flight work, rolls back uncommitted writes and releases resources. Liveness is
separate from database readiness; no automatic retry loop is implemented yet.

For connection failures, preserve safe error/correlation evidence, identify which
dependency failed, respect request deadlines and retry only safe reads or same-key
commands. A lost payment acknowledgment requires command-status lookup before
another posting. Remote draft autosave protects only acknowledged saves.

During an internet outage, staff follow the clinic's approved manual downtime
procedure and later reconcile entries; there is no offline write queue or local
patient DB. The clinic must choose the manual procedure before actual operation.

## Logs, audit and investigation

Operational logs rotate in a caller-selected local text/JSON location; they omit
clinical text, secrets, arbitrary message arguments and exception values. Correlation
IDs are restricted operational data, not metrics labels. Audit records are separate
immutable access/business facts persisted with writes; real DB append-only grants,
sensitive-read audit and mandatory audit failure policy remain M2/adapter work.

Use operation/outcome counts, p50/p95 timings, pool wait, socket lag/reconnects,
readiness/outage duration and backup age. Do not copy production records into an
issue or developer fixture while diagnosing a failure.

## Migration and release procedure — implement with persistence

1. Record compatible code/API/schema range and obtain verified remote backup.
2. Apply reviewed migrations once in an isolated remote staging database using a
   separate migration role. Desktops never run migrations.
3. Exercise references/clinic isolation, two-connection overlap/payment races and
   rollback behavior. Confirm old/new application compatibility for expansion.
4. Apply compatible expansion, migrate data, deploy/recheck, then contract only
   after old consumers are retired. Keep rollback code/schema compatibility clear.
5. If health fails, halt rollout; roll back code only to compatible schema, otherwise
   use the tested restore path. Never improvise destructive down-migrations.

## Backups and remote restore drill — required in Week 4

M1 coordinates automation/runbook; M2 checks restricted access/key separation;
M3/M4/M5 reconcile restored scheduling/history/finance. Select a managed backup
capability or remote job; verify actual plan features. Daily and pre-migration
encrypted backups need off-project retention, backup-age/failure alerts and keys
stored separately. Attachment objects/provider auth may require separate backup.
No database server needs installation on a clinic computer.

Restore into an isolated remote target, then check schema, counts, references,
clinical history, invoice/net-payment totals, grants and audit continuity. Revoke
old sessions as necessary, redirect clients deliberately and verify readiness.
Record start/end times, last recoverable transaction and reconciliation results.
Do not test restoration destructively against production.

Initial demo objectives from the blueprint are recovery point <=24h and recovery
time <=2h; these are unmeasured targets, not guarantees. The clinic must approve
acceptable real data-loss/outage limits. A JSONL portability export with snapshot,
schema/version/checksum manifest is not a complete database/provider backup.
