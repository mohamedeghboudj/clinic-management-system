# GitHub administration and preservation

Repository: `mohamedeghboudj/clinic-management-system`, public, default branch main.
Initial inspection found main unprotected and no rulesets. M3 `SamirKor` and M5
`ayyoubbouchama` both have write access. M2/M4 have not joined; their review and
testing duties stay pending, not silently reassigned.

The original Telegram notification blob is preserved:
`b81663a6e5b4611129f05367b7da406867fb4c06`. Its original filename, contents and
secret references remain unchanged. The old nonempty charter was archived outside
the application folder; prior scaffold/history remains recoverable in Git.

## Prepared configuration

`.github/repository-policy.json` describes squash-only PR merges, branch deletion
after merge, two approvals, stale-review dismissal, code-owner/last-push approval,
strict required CI, conversation resolution, admin enforcement and no force pushes.
It also configures read-only workflow tokens without bot PR approval, selected
Actions (including the retained Telegram exception), dependency alerts/fixes and
secret scanning/push protection. New workflows pin action commit SHAs.

The GitHub plugin supports contents/PR work but exposes no administration-write
tool. Local SSH authentication is unavailable; public HTTPS fetch works. An
administration credential was supplied through the authenticated CLI; the
prepared policy is now applied and its full readback matches on 1 November.
No token is requested in chat, read from the plugin's private storage or committed.

For future inspection or reviewed policy changes using authenticated GitHub CLI:

```powershell
python -m scripts.configure_github            # inspect exact public policy
python -m scripts.configure_github --apply    # explicit settings mutations
python -m scripts.configure_github --check    # verify current remote enforcement
```

The script also accepts a privately supplied GH_TOKEN environment value, never
printing or persisting it. It validates the fixed authorized repository and admin
permission before writes. Settings changes are sequential; if a provider permission
or plan rejects one, report the actual partial state and rerun/check after resolving
it. A checked-in settings file by itself does not configure GitHub.

Do not enable a global SHA-only Actions restriction that breaks the preserved
Telegram action at `@master`; any change to that user-owned workflow is separate.
Do not weaken approvals because M2/M4 are absent. No PR auto-approval, auto-merge,
direct main push, visibility change or release deployment is included.

References: [protected-branch API](https://docs.github.com/en/rest/branches/branch-protection),
[Actions permissions API](https://docs.github.com/en/rest/actions/permissions),
[Actions security guidance](https://docs.github.com/en/actions/reference/security/secure-use).
