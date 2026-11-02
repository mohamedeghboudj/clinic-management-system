# Permissions and Access Control

## 1. Purpose

This document describes the Week 1 permissions and access-control design for the Clinic Management System.

The system must ensure that users can access only the clinics, actions, resources, and data fields they are authorized to access.

Access control is enforced by the backend. The desktop application must never be treated as a trusted source of permissions or ownership information.

## 2. Roles

The system defines the following roles:

| Role | Description |
|---|---|
| OWNER | Clinic owner |
| MANAGER | Clinic manager |
| DOCTOR | Doctor |
| NURSE | Nurse |
| SECRETARY | Secretary |

Roles belong to a clinic membership, not directly to a Person, StaffProfile, or DoctorProfile.

A StaffProfile does not automatically grant application access. A user must have an account and an appropriate clinic membership.

A user may have multiple roles within a clinic.

## 3. Permissions

The Week 1 specification defines these permissions:

| Permission | Intended action |
|---|---|
| PATIENT_READ | Read patient information |
| PATIENT_WRITE | Create or modify patient information |
| APPOINTMENT_READ | Read appointment information |
| APPOINTMENT_WRITE | Create or modify appointments |
| CLINICAL_READ | Read clinical information |
| CLINICAL_WRITE | Create or modify clinical information |
| PRESCRIBE | Create prescriptions |
| BILLING_READ | Read billing information |
| BILLING_WRITE | Create or modify billing information |
| PAYMENT_RECORD | Record payments |
| PAYMENT_REVERSE | Reverse payments |
| FINANCE_REPORT | Access financial reports |
| STAFF_MANAGE | Manage staff information |
| ROLE_MANAGE | Manage clinic membership roles |

Unknown permissions must always be denied.

## 4. Access scopes

Each role grant defines an access scope.

| Scope | Meaning |
|---|---|
| CLINIC | Access within the authorized clinic |
| ASSIGNED | Access to resources assigned to the authenticated staff member |
| OWN | Access to resources belonging to the authenticated user |

The backend must verify the requested scope against trusted resource information.

For example, doctor assignment must be resolved by the server using trusted data. The client must not declare that a doctor is assigned to a patient or appointment.

## 5. Role-permission matrix

The Week 1 specification lists the roles and permissions but does not provide a final mapping between them.

Therefore, the default role-permission matrix remains **pending team approval**.

Before implementation, the team must agree on:

- Which permissions each role receives.
- Which access scope applies to each permission.
- Which data fields are available for each grant.
- Whether a role may have different grants in different clinics.

No default grants should be invented during implementation.

## 6. Field-level authorization

Authorization must consider both the requested action and the requested data fields.

A RoleGrant contains:

- `role: Role`
- `permission: Permission`
- `scope: AccessScope`
- `fields: frozenset[str]`

An empty field set is not a wildcard.

Permissions that do not operate on data fields must use explicit action-only rules.

The backend must determine which fields are available to the authenticated user before returning sensitive information.

A response must not expose unauthorized fields simply because they are required by a response DTO.

## 7. Clinic isolation

Every clinic-specific access decision must verify the clinic context.

A user must not access another clinic's patients, appointments, staff, billing records, or other clinic-owned resources without an authorized membership and matching clinic context.

Repository queries must include the relevant clinic identifier where required.

The client must not be trusted to establish clinic membership or resource ownership.

## 8. Clinical information restrictions

Clinical information requires explicit authorization.

The OWNER role must not automatically bypass clinical-data restrictions.

Access to clinical information must be determined by the applicable permission, scope, resource context, and permitted fields.

The system must preserve finalized clinical notes. Corrections must be handled through amendments rather than silently overwriting finalized notes.

## 9. Account and membership restrictions

The backend must verify that:

- The user account is enabled.
- The clinic membership is active.
- The authenticated session is valid.
- The session's authentication version matches the current account authentication version.
- The requested action is permitted for the user's clinic membership.
- The requested resource belongs to the correct clinic and satisfies the required scope.

Disabling an account or changing security-sensitive account information must invalidate affected sessions.

Role changes must be authorized by a server-side use case. The server must invalidate affected sessions when required.

## 10. Session security

Sessions must store a hash of the refresh token, never the raw refresh token.

A session must have:

- An account identifier.
- An authentication version.
- A refresh-token hash.
- A creation timestamp.
- An expiry timestamp.
- An optional revocation timestamp.

A session is valid only if it has not expired, has not been revoked, and its authentication version matches the current account version.

## 11. Password security

Passwords must never be stored in plaintext.

The UserAccount model stores only an encoded password hash.

The application will define a PasswordHasher port. The concrete Argon2 implementation belongs to the later infrastructure work.

Password hashes must not appear in API responses, logs, or ordinary object representations.

Password replacement and session invalidation must follow the security rules defined by the application.

## 12. Audit requirements

Security-sensitive actions must be auditable.

Audit entries should identify:

- The clinic.
- The actor, when known.
- The action.
- The resource type and identifier, when available.
- The outcome.
- The occurrence timestamp.
- The correlation identifier.
- An optional reason code.

Audit records must be append-only. They should use reason codes rather than free-form clinical narratives.

Failed authentication may have no known actor.

## 13. Authorization failure behavior

The access policy must deny access when no applicable grant matches.

The backend must raise `PermissionDeniedError` when an action or requested field is not authorized.

The system must not treat missing permissions, unknown grants, invalid scopes, or missing trusted resource information as permission to proceed.

## 14. Implementation boundary

### Week 1

- Define roles, permissions, scopes, grants, and access-policy contracts.
- Define account, membership, principal, resource-context, and session models.
- Document security requirements and unresolved decisions.
- Test policy behavior using independent tests and controlled in-memory data where appropriate.

### Week 2 and later

- Implement authentication and authorization use cases.
- Implement the Argon2 password-hashing adapter.
- Implement persistence and session management.
- Integrate authorization with API endpoints.
- Enforce clinic isolation and field-level filtering.

No login endpoints, real token generation, database adapters, or desktop authentication screens are part of this Week 1 document.

## 15. Decisions requiring team approval

The following decisions must be agreed upon before their implementation:

1. The default permissions assigned to each role.
2. The access scope associated with each role-permission grant.
3. The permitted field sets for sensitive data.
4. The initial clinic OWNER account creation process.
5. Password reset and account recovery procedures.
6. The handling of duplicate patient registrations.
7. The exact session-revocation behavior following role changes and account security changes.

These decisions must be documented before being treated as approved system behavior.

## 16. Acceptance criteria

This design is ready for implementation when:

- All five roles and the specified permissions are represented.
- Access scopes are explicitly defined.
- Unknown permissions are denied.
- Empty field sets are not treated as wildcards.
- Clinic isolation is enforced by trusted backend data.
- Clinical information has explicit access restrictions.
- OWNER does not automatically bypass clinical restrictions.
- Disabled accounts and invalid sessions cannot authenticate.
- Passwords and refresh tokens are never stored in plaintext.
- The role-permission matrix and other pending decisions are reviewed by the team.