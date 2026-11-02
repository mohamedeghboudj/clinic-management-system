# CodeQL investigation: secret scanner reporting

Date: 2 November 2026. Reported by M2 on PR #5, commit `4758422`.
Finding: [CodeQL alert #1](https://github.com/mohamedeghboudj/clinic-management-system/security/code-scanning/1),
`py/clear-text-logging-sensitive-data`, high/security severity 7.5.

## Evidence and assessment

The PR-specific SARIF analysis `2071661215` for `refs/pull/5/merge` traces
`SecretsCollection()` at line 18 through `list(...)`/iteration to `filename`
at line 27 and the reporting f-string at line 28. It does not show an access to
the candidate's plaintext value.

In pinned `detect-secrets==1.5.0`, `PotentialSecret.type` is the detector's
classification string, `line_number` is location metadata and `filename` is the
path. Actual candidate plaintext is stored separately as `secret_value`.
The old reporting expression accessed metadata only. M2's assessment is correct:
this is a false positive for logging the actual candidate value, caused by
conservative sensitivity propagation from the collection to its metadata.

## Change and verification

CI now prints only `Secret scan: N candidate(s)`. It does not render finding
objects, values, hashes, paths, line numbers or classifications. Candidate details
are inspected locally. The scan inputs, detector settings and nonzero exit status
when candidates exist are unchanged. This follows the same count-only direction
already present on M4's clinical branch (`40a838c`).

Two tests use the real scanner in temporary workspaces: a synthetic keyword
candidate still produces exit status 1 with count-only output, and a clean file
produces status 0. The metadata-output test fails on the original code and passes
after the reporting loop is removed. No candidate is allowlisted by this change;
the security query and workflows remain enabled.

Final verification is the fresh PR CodeQL analysis after publication; an alert's
automatic fixed state is distinct from dismissing it manually. This note records
the investigation without changing alert state through an administrative bypass.

Reference: [CodeQL query guidance](https://codeql.github.com/codeql-query-help/python/py-clear-text-logging-sensitive-data/).
