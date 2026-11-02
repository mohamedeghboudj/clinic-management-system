# ADR 0002: Identity and Security

## Status

Proposed — pending team review and approval.

## Date

2026-11-02

## Context

The Clinic Management System handles sensitive patient, clinical, staff, and financial information.

The system must provide secure authentication and clinic-scoped authorization while ensuring that users can access only the resources and data fields permitted by their roles and responsibilities.

The application uses a Python desktop client communicating with a backend API. The backend is responsible for authentication, authorization, session management, and enforcement of access rules.

The desktop client must not be treated as a trusted security boundary.

## Decision 1: Clinic-scoped memberships and roles

User roles are assigned through a clinic membership rather than directly to a Person or StaffProfile.

The system defines these roles:

- OWNER
- MANAGER
- DOCTOR
- NURSE
- SECRETARY

A user may have multiple roles within a clinic.

A StaffProfile does not automatically grant application access. The user must have an account and an appropriate clinic membership.

A user's permissions must be evaluated in the context of the selected clinic membership.

### Consequences

- The same account can have different roles in different clinics.
- Staff employment and application access remain separate concepts.
- Authorization must verify the active clinic membership.
- Role changes must be performed through authorized server-side use cases.

## Decision 2: Explicit permission and scope checks

Authorization is based on explicit permissions, access scopes, and permitted data fields.

The defined permissions include:

- PATIENT_READ and PATIENT_WRITE
- APPOINTMENT_READ and APPOINTMENT_WRITE
- CLINICAL_READ and CLINICAL_WRITE
- PRESCRIBE
- BILLING_READ and BILLING_WRITE
- PAYMENT_RECORD and PAYMENT_REVERSE
- FINANCE_REPORT
- STAFF_MANAGE
- ROLE_MANAGE

The defined access scopes are:

- CLINIC
- ASSIGNED
- OWN

The AccessPolicy evaluates the authenticated Principal, requested Permission, and trusted ResourceContext.

Unknown permissions and unmatched grants must be denied.

An empty permitted-field set is not a wildcard.

### Consequences

- Authorization decisions are explicit and testable.
- Clinic isolation is enforced by the backend.
- Field-level restrictions can be applied to sensitive responses.
- Client-supplied ownership, assignments, or roles must never be trusted.

## Decision 3: No automatic OWNER bypass for clinical information

The OWNER role does not automatically bypass clinical-data restrictions.

Clinical information requires explicit authorization based on the applicable permission, scope, resource context, and permitted fields.

### Consequences

- Administrative ownership does not automatically imply clinical access.
- Clinical information remains subject to field-level authorization.
- Access-policy tests must include attempts to bypass clinical restrictions using OWNER privileges.

## Decision 4: Password storage and hashing

The system stores an encoded password hash rather than a plaintext password.

UserAccount contains a password_hash field. The password hash must not appear in ordinary object representations, API responses, or logs.

The application defines a PasswordHasher port with these operations:

- hash(password: str) -> str
- verify(password: str, encoded_hash: str) -> bool
- needs_rehash(encoded_hash: str) -> bool

An Argon2 adapter is planned for the infrastructure implementation.

The concrete cryptographic implementation is outside the Week 1 domain-model work.

### Consequences

- Plaintext passwords are never persisted.
- Password hashing can be tested independently through its application port.
- The infrastructure layer will provide the concrete Argon2 implementation.

## Decision 5: Authentication sessions and invalidation

A Session stores:

- Account identifier.
- Authentication version.
- Refresh-token hash.
- Creation timestamp.
- Expiration timestamp.
- Optional revocation timestamp.

Raw refresh tokens must never be stored.

A session is valid only when it has not expired, has not been revoked, and its authentication version matches the current account authentication version.

Security-sensitive account changes must invalidate affected sessions.

The UserAccount model provides session invalidation through its authentication version.

### Consequences

- Previously issued sessions can be invalidated after security changes.
- Session validation must compare authentication versions.
- Session persistence and token handling will be implemented in later application and infrastructure work.

## Decision 6: Trusted authentication context

The backend constructs a Principal only after verifying the account, session, and clinic membership.

The Principal represents the authenticated request context.

It must not be accepted as trusted data directly from request JSON.

ResourceContext contains trusted resource facts loaded by the server, including clinic identity, patient identity, assigned staff identifiers, and available fields.

### Consequences

- The backend remains responsible for establishing identity and resource ownership.
- Client input cannot grant itself access to another patient's records.
- Authorization depends on server-verified facts.

## Decision 7: Security auditing

Security-sensitive actions must produce audit records.

Audit entries include the clinic, actor when known, action, resource information, outcome, timestamp, correlation identifier, and optional reason code.

Audit records are append-only.

Reason codes should be used instead of free-form clinical narratives.

Failed authentication may have no known actor.

### Consequences

- Security-sensitive activity can be reviewed.
- Audit records can be correlated across application operations.
- Audit records must not expose passwords, raw tokens, or unnecessary clinical information.

## Decision 8: Separation of Week 1 and later implementation

Week 1 defines the domain models, application ports, contracts, security rules, and tests.

Later implementation work will provide:

- Concrete password hashing.
- Authentication and authorization use cases.
- Token generation and validation.
- Session persistence.
- Database adapters.
- API authentication and authorization integration.
- Desktop authentication screens.

No real token generation, login endpoints, or database authentication adapters are introduced as part of this Week 1 decision.

## Alternatives considered

### Trusting the desktop client

Rejected.

The desktop application is not a trusted security boundary. The backend must verify identity, membership, permissions, scope, and resource ownership.

### Assigning roles directly to Person

Rejected.

Roles belong to clinic memberships. A person may have different roles in different clinics, and employment does not automatically grant application access.

### Storing plaintext passwords or refresh tokens

Rejected.

Only encoded password hashes and refresh-token hashes are stored.

### Giving OWNER unrestricted access

Rejected.

OWNER does not automatically bypass clinical-data restrictions.

## Unresolved decisions requiring team approval

The following decisions are not finalized by this ADR:

1. The default permission grants for each role.
2. The access scope and permitted fields associated with each grant.
3. The initial clinic OWNER account creation process.
4. Password reset and account recovery procedures.
5. The exact session-revocation behavior following role changes.
6. Login throttling and recovery behavior.
7. Duplicate-patient registration handling.

These decisions must be reviewed and approved by the team before being treated as final system behavior.

## Consequences and implementation requirements

- Authorization must deny by default.
- Clinic isolation must be enforced by backend queries and use cases.
- Clinical information requires explicit authorization.
- Disabled accounts and invalid sessions must not authenticate.
- Passwords and refresh tokens must never be stored in plaintext.
- Security-sensitive changes must invalidate affected sessions when required.
- Audit records must not contain secrets.
- Security behavior must have independent tests.

## References

- Week 1 — Member Implementation Guide.
- Clinic Management System Meeting and Delivery Blueprint.
- docs/permissions.md.
- docs/design/people-access.md.