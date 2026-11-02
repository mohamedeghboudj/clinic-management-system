# Security

This is a development foundation using synthetic data. No live clinic backend,
remote database, authentication system, backup system or patient data is deployed.

Do not place credentials or patient information in public issues, logs, PRs,
fixtures, screenshots or repository files. Report a suspected vulnerability to
the repository owner through a private channel; a dedicated reporting address
has not been supplied, so none is invented here. Rotate exposed credentials at
their provider, restrict access and assess affected data before deleting evidence.

## Implemented controls

- Domain/application imports point inward; the desktop cannot import server
  settings or persistence adapters.
- Explicit configuration; credentials omitted from default settings repr.
  Remote PostgreSQL TLS verification is required; no local database fallback.
- Operational JSON logging drops arbitrary messages, argument values, exception
  messages and traceback source/locals. Only registered labels and stack
  locations remain. Audit data is separate and restricted by design.
- Secret scanning, dependency audits, CodeQL workflow and pinned new Actions.
- Reviewed repository policy for two approvals, no force pushes, stale-review
  dismissal, code-owner review, read-only workflow tokens and push protection.
  Actual activation is tracked in `docs/M1_PROGRESS.md`; a policy file alone
  does not enforce settings.

The retained Telegram workflow references `appleboy/telegram-action@master`.
It is the explicit legacy exception required to preserve your workflow unchanged;
the Actions allowlist retains it. A future change to pin or fix that workflow
requires its own reviewed task. No bot token/chat secret has been read or changed.

## Required before real deployment

M2's server-side identity and per-request/record/field authorization; session
revocation; immutable audit persistence; least-privilege database grants; actual
remote concurrency tests; private attachments; tested backups/restoration; clinic
retention/hosting policy; operational ownership and downtime procedures. No UI
button or shared desktop database credential can provide those guarantees.
