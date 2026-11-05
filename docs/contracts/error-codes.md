# Error codes

`ClinicError` subclasses separate categories; `code` and `message_key` identify a
stable failure without embedding its technical cause. Optional details are copied
and read-only; callers must restrict them to reviewed non-sensitive facts. Default
exception string/repr omits details. Never log an exception message containing
patient input or credential-bearing driver text.

| Code | Category / meaning |
| --- | --- |
| INVALID_VALUE | ValidationError: invalid local value or envelope shape. |
| INVALID_CONFIGURATION | ConfigurationError: startup settings invalid/missing. |
| STALE_VERSION | ConcurrencyError: expected aggregate version no longer matches. |
| APPOINTMENT_OVERLAP | ConflictError: reserved doctor/room time conflicts. |
| INVALID_TRANSITION | InvalidTransitionError: prohibited lifecycle move. |
| ACCESS_DENIED | PermissionDeniedError: clinic/action/record scope denied. |
| PAYMENT_EXCEEDS_BALANCE | ValidationError: allocation exceeds unpaid invoice debt. |
| IDEMPOTENCY_KEY_REUSED | ConflictError: same command key with a different payload. |
| DUPLICATE_EFFECT | ConflictError: duplicate event/audit identifier in the fake transaction. |
| DEPENDENCY_UNAVAILABLE | DependencyUnavailableError: required service unreachable. |
| PERSISTENCE_FAILURE | PersistenceError: storage failed; technical cause stays chained. |
| UNEXPECTED_FAILURE | API's future safe generic 500/correlation response. |

NotFoundError and AuthenticationError are also defined. Feature owners publish
their specific codes before relying on them as client behavior. Empty search
results return a typed empty page; optional lookups return None. No bare except,
silent catches or return codes replacing failed business commands.

Future mapping: validation 422; unauthenticated 401; denied 403 (or a deliberate
non-disclosing 404); missing 404; conflicts/stale state 409; dependency 503;
unexpected 500. API code must implement/test this mapping before deployment.
