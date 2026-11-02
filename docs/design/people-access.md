# People and Access Design

**Project:** Clinic Management System  
**Owner:** M2  
**Implementation phase:** Week 1  
**Status:** Design specification

## 1. Purpose

This document defines the design of the people, patient, staff, doctor, identity, and access-control components of the Clinic Management System.

The implementation is divided into two stages:

- **Week 1:** Domain models, validation utilities, application ports, contracts, tests, and documentation.
- **Week 2:** Database adapters, authentication implementation, application use cases, and API integration.

The domain layer must remain independent of databases, HTTP frameworks, desktop interfaces, and external services.

## 2. Architectural responsibilities

M2 is responsible for:

- `domain/shared/`: Contact information, addresses, and shared validation utilities.
- `domain/people/`: Person, patient, staff, doctor, and date-related models.
- `domain/access/`: Accounts, memberships, permissions, sessions, principals, and access policies.
- `application/ports/`: Password, identity, person, patient, staff, account, and session interfaces.
- `application/contracts/`: People and authentication data-transfer objects.

M2 must reuse shared foundation contracts provided by M1. In particular, M2 must not create duplicate implementations of `Entity` or `ValidationError`.

## 3. People domain

### 3.1 ContactInfo

**Location:** `domain/shared/contact.py`

Fields:

- `phone: str | None`
- `email: str | None`

Requirements:

- Both fields may be absent.
- Supplied values must be validated.
- Contact information must be reusable by different domain entities.
- The value object must be immutable.

Methods:

- `is_empty(self) -> bool`
- `normalize_phone(value: str, region: str) -> str`
- `validate_email(value: str) -> str`

Validation does not prove ownership or successful delivery of an email address or phone number.

### 3.2 Address

**Location:** `domain/shared/address.py`

Fields:

- `line1: str`
- `city: str`
- `region: str | None`
- `postal_code: str | None`
- `country_code: str`

Requirements:

- Required strings must not be empty.
- Country codes must follow the agreed country-code shape.
- Optional fields must support missing information.
- No country-specific postal-code assumptions should be imposed.

### 3.3 Person

**Location:** `domain/people/person.py`

Fields:

- `id: UUID`
- `version: int = 0`
- `given_name: str`
- `family_name: str`
- `birth_date: date | None`
- `contact: ContactInfo`
- `address: Address | None`

Methods:

- `full_name(self) -> str`
- `age_on(self, on_date: date) -> int | None`
- `update_contact(self, contact: ContactInfo, address: Address | None) -> None`

Requirements:

- Preserve names and accents.
- Validate birth dates against an explicit reference date.
- Unknown birth dates must be supported.
- The constructor must not read the system clock implicitly.

### 3.4 Patient

**Location:** `domain/people/patient.py`

Fields:

- `id: UUID`
- `version: int = 0`
- `clinic_id: UUID`
- `person_id: UUID`
- `patient_number: str`
- `emergency_contact: ContactInfo | None`
- `archived_at: datetime | None`

Methods:

- `archive(self, *, at: datetime) -> None`
- `restore(self) -> None`
- `is_active(self) -> bool`

Requirements:

- Patient numbers are unique within their clinic; database enforcement is planned for a later phase.
- Archiving and restoring must update the patient's active state consistently.
- A patient must not contain diagnosis, allergy, or password fields.
- Patient registration will later create the person and clinic-specific patient relationship atomically.

### 3.5 StaffProfile

**Location:** `domain/people/staff.py`

Fields:

- `id: UUID`
- `version: int = 0`
- `clinic_id: UUID`
- `person_id: UUID`
- `staff_number: str`
- `hired_on: date`
- `active: bool`

Methods:

- `activate(self) -> None`
- `deactivate(self) -> None`

A staff profile does not automatically grant system access or clinical permissions.

### 3.6 DoctorProfile

**Location:** `domain/people/doctor.py`

Fields:

- `id: UUID`
- `version: int = 0`
- `clinic_id: UUID`
- `staff_id: UUID`
- `specialty: str`
- `licence_number: str`
- `active: bool`

Methods:

- `activate(self) -> None`
- `deactivate(self) -> None`

Requirements:

- A doctor profile is associated with a staff profile.
- Appointments will reference the doctor profile ID.
- Staff employment and doctor status are separate concepts.
- Booking appointments is not a responsibility of this model.

## 4. Access-control domain

### 4.1 Roles

**Location:** `domain/access/enums.py`

The supported roles are:

- `OWNER`
- `MANAGER`
- `DOCTOR`
- `NURSE`
- `SECRETARY`

Roles belong to clinic memberships, not to Person or StaffProfile objects.

### 4.2 Permissions

The supported permissions are:

- `PATIENT_READ`
- `PATIENT_WRITE`
- `APPOINTMENT_READ`
- `APPOINTMENT_WRITE`
- `CLINICAL_READ`
- `CLINICAL_WRITE`
- `PRESCRIBE`
- `BILLING_READ`
- `BILLING_WRITE`
- `PAYMENT_RECORD`
- `PAYMENT_REVERSE`
- `FINANCE_REPORT`
- `STAFF_MANAGE`
- `ROLE_MANAGE`

Unknown permissions must be denied by default.

The final default role-permission matrix requires team agreement and must not be assumed without approval.

### 4.3 AccessScope

The supported scopes are:

- `CLINIC`
- `ASSIGNED`
- `OWN`

The scope determines which resources a permission can apply to.

### 4.4 RoleGrant

**Location:** `domain/access/grants.py`

Fields:

- `role: Role`
- `permission: Permission`
- `scope: AccessScope`
- `fields: frozenset[str]`

Requirements:

- A grant represents one policy rule.
- The object must be immutable.
- An empty field set is not a wildcard.
- Permissions that do not concern data fields must use explicit action-only rules.

### 4.5 ClinicMembership

**Location:** `domain/access/membership.py`

Fields:

- `id: UUID`
- `version: int = 0`
- `account_id: UUID`
- `clinic_id: UUID`
- `staff_id: UUID | None`
- `patient_id: UUID | None`
- `roles: frozenset[Role]`
- `active: bool`

Methods:

- `grant_role(self, role: Role) -> None`
- `revoke_role(self, role: Role) -> None`
- `deactivate(self) -> None`

Requirements:

- Membership connects an account to a clinic.
- Roles are attached to the membership.
- Role changes must be authorized by an application use case.
- The server must invalidate affected sessions when required.
- Patient membership is reserved for future patient-facing access.

### 4.6 UserAccount

**Location:** `domain/access/account.py`

Fields:

- `id: UUID`
- `version: int = 0`
- `person_id: UUID`
- `username: str`
- `password_hash: str`
- `enabled: bool`
- `auth_version: int`
- `must_change_password: bool`

Methods:

- `disable(self) -> None`
- `enable(self) -> None`
- `replace_password_hash(self, encoded_hash: str) -> None`
- `invalidate_sessions(self) -> None`

Security requirements:

- Plaintext passwords must never be stored.
- Password hashes must not appear in representations or API responses.
- Security changes must increment the authentication version.
- There must be no plaintext password property.

### 4.7 Principal

**Location:** `domain/access/principal.py`

Fields:

- `account_id: UUID`
- `clinic_id: UUID`
- `membership_id: UUID`
- `staff_id: UUID | None`
- `patient_id: UUID | None`
- `roles: frozenset[Role]`
- `auth_version: int`

The Principal is an immutable authenticated request context.

It must only be constructed after the server verifies the account, session, and clinic membership.

A client must never be allowed to submit a Principal as trusted authentication context.

### 4.8 ResourceContext

**Location:** `domain/access/policy.py`

Fields:

- `clinic_id: UUID`
- `patient_id: UUID | None`
- `assigned_staff_ids: frozenset[UUID]`
- `available_fields: frozenset[str]`

Resource facts must be loaded and trusted by the server.

Clients must not declare their own ownership, doctor assignments, or resource permissions.

### 4.9 AccessPolicy

**Location:** `domain/access/policy.py`

Fields:

- `grants: tuple[RoleGrant, ...]`

Methods:

- `require(self, principal: Principal, action: Permission, resource: ResourceContext) -> None`
- `allowed_fields(self, principal: Principal, action: Permission, resource: ResourceContext) -> frozenset[str]`

Requirements:

- Match clinic membership, action, role, scope, and permitted fields.
- Reject unauthorized operations using `PermissionDeniedError`.
- Deny unknown permissions.
- Do not give OWNER an automatic bypass for clinical-data restrictions.
- Only return fields that are both available and explicitly authorized.

## 5. Audit and sessions

### 5.1 AuditEntry

**Location:** `domain/access/audit.py`

Fields:

- `id: UUID`
- `clinic_id: UUID`
- `actor_id: UUID | None`
- `action: str`
- `resource_type: str`
- `resource_id: UUID | None`
- `outcome: str`
- `occurred_at: datetime`
- `correlation_id: UUID`
- `reason_code: str | None`

Requirements:

- Audit entries are immutable and append-only.
- Failed authentication may have an unknown actor.
- Reason codes must be used instead of free clinical narrative.
- The model must be compatible with M1's AuditWriter contract.

### 5.2 Session
The Session is an entity with an ID. It does not require a version
field under the Week 1 specification.

**Location:** `domain/access/session.py`

Fields:

- `id: UUID`
- `account_id: UUID`
- `auth_version: int`
- `refresh_token_hash: str`
- `created_at: datetime`
- `expires_at: datetime`
- `revoked_at: datetime | None`

Methods:

- `is_valid(self, *, at: datetime, current_auth_version: int) -> bool`
- `revoke(self, *, at: datetime) -> None`

Requirements:

- Never store a raw refresh token.
- Expired, revoked, and outdated sessions must be rejected.
- Session validity must use an explicit reference time.

## 6. Application contracts and ports

### 6.1 Authentication contract

**Location:** `application/contracts/access.py`

`AuthenticatedSession` is an immutable DTO containing:

- `principal: Principal`
- `access_token: str`
- `refresh_token: str`
- `expires_at: datetime`

Token fields must be excluded from representations and logs.

No real token generation is implemented in Week 1.

### 6.2 People contract

**Location:** `application/contracts/people.py`

`PatientSummary` contains:

- `patient_id: UUID`
- `patient_number: str`
- `display_name: str`
- `phone: str | None`
- `version: int`

Actual database querying, joining, and mapping are Week 2 responsibilities.

### 6.3 PasswordHasher port

**Location:** `application/ports/passwords.py`

Methods:

- `hash(self, password: str) -> str`
- `verify(self, password: str, encoded_hash: str) -> bool`
- `needs_rehash(self, encoded_hash: str) -> bool`

An Argon2 adapter will be implemented later. No cryptographic implementation or production fake is required in Week 1.

### 6.4 IdentityProvider port

**Location:** `application/ports/identity_provider.py`

Methods:

- `authenticate(self, username: str, password: str, *, at: datetime) -> AuthenticatedSession`
- `resolve_principal(self, access_token: str, *, clinic_id: UUID, at: datetime) -> Principal`
- `revoke(self, session_id: UUID, *, at: datetime) -> None`

The contract must specify invalid credentials, expired sessions, disabled accounts, and revoked-session errors.

No network implementation or actual login endpoint is implemented in Week 1.

### 6.5 Repository ports

PersonRepository:

- `get(self, clinic_id: UUID, person_id: UUID) -> Person | None`
- `add(self, person: Person) -> None`
- `save(self, person: Person, *, expected_version: int) -> None`

PatientRepository:

- `get(self, clinic_id: UUID, patient_id: UUID) -> Patient | None`
- `add(self, patient: Patient) -> None`
- `save(self, patient: Patient, *, expected_version: int) -> None`
- `search(self, clinic_id: UUID, query: str, page: PageRequest) -> Page[PatientSummary]`

StaffRepository:

- `get(self, clinic_id: UUID, staff_id: UUID) -> StaffProfile | None`
- `get_doctor(self, clinic_id: UUID, doctor_id: UUID) -> DoctorProfile | None`
- `add(self, staff: StaffProfile) -> None`
- `add_doctor(self, doctor: DoctorProfile) -> None`
- `save(self, staff: StaffProfile, *, expected_version: int) -> None`
- `save_doctor(self, doctor: DoctorProfile, *, expected_version: int) -> None`

AccountRepository:

- `get_by_username(self, username: str) -> UserAccount | None`
- `add(self, account: UserAccount) -> None`
- `get_membership(self, account_id: UUID, clinic_id: UUID) -> ClinicMembership | None`
- `add_membership(self, membership: ClinicMembership) -> None`
- `save_membership(self, membership: ClinicMembership, *, expected_version: int) -> None`
- `save(self, account: UserAccount, *, expected_version: int) -> None`

SessionRepository:

- `get(self, session_id: UUID) -> Session | None`
- `add(self, session: Session) -> None`
- `revoke(self, session_id: UUID, *, at: datetime) -> None`

All repository contracts must preserve clinic boundaries and expected-version concurrency checks.

PersonRepository.get must only expose a deployment-wide person through a patient or staff relationship in the supplied clinic. Adding a Person alone does not grant access.

## 7. Registration workflow design

Future application use case:

`RegisterPatient.execute(self, command: RegisterPatientCommand, principal: Principal) -> PatientSummary`

The command will contain:

- Person name information.
- Optional birth date.
- Optional contact information.
- Optional address.
- An idempotency key.

The server must:

1. Authenticate the caller.
2. Verify authorization to register a patient in the selected clinic.
3. Validate the supplied information.
4. Allocate a clinic-specific patient number.
5. Create the Person and Patient relationship atomically.
6. Return an authorized PatientSummary.
7. Prevent duplicate requests from creating duplicate patients.

No RegisterPatient service implementation is required in Week 1.

## 8. Response field authorization

Future response mapping:

`patient_to_response(patient: Patient, person: Person, fields: frozenset[str]) -> PatientSummary`

Only authorized fields may be returned.

The required DTO fields must not be silently exposed when the caller lacks permission.

If a required field cannot be authorized, the application must define an explicit response strategy before implementing the mapper.

## 9. Login throttling design

Future port:

- `check(self, username_key: str, *, at: datetime) -> None`
- `record_failure(self, username_key: str, *, at: datetime) -> None`

Requirements:

- Support configurable backoff or lockout.
- Use generic login failure messages.
- Record security-relevant failures for auditing.
- Provide a recovery strategy.
- Avoid permanent denial of service caused by repeated malicious attempts.

Implementation is deferred.

## 10. Security requirements

The implementation must enforce:

- Deny-by-default authorization.
- Clinic-scoped data access.
- Server-controlled ownership and assignments.
- Field-level clinical-data authorization.
- No automatic OWNER bypass for clinical data.
- Password hashing through the PasswordHasher abstraction.
- No plaintext passwords or raw refresh tokens in storage.
- Session invalidation after relevant security changes.
- Immutable audit records.
- Explicit session expiration and revocation.
- Safe handling of authentication errors.
- Atomic patient registration.

## 11. Unresolved decisions

The following decisions require team agreement before final implementation:

1. The default permission grants for each role.
2. The convention for calculating birthdays on February 29 in non-leap years.
3. The exact validation package and supported phone-number regions.
4. The response strategy when required PatientSummary fields are not authorized.
5. The agreed error contract and import path supplied by M1.
6. The final account and clinic-selection behavior.

These decisions must not be silently assumed.

## 12. Acceptance criteria

The M2 implementation is accepted when:

- All specified models and value objects exist.
- Constructors validate local invariants.
- All public methods have type annotations and Google-style docstrings.
- Models use explicit reference dates and times.
- Sensitive values are excluded from representations and logs.
- Authorization denies unknown or unmatched grants.
- Wrong-clinic and unauthorized-resource access is rejected.
- Clinical field filtering is enforced.
- Sessions reject expiration, revocation, and authentication-version mismatch.
- Repository interfaces specify expected-version behavior.
- Independent unit tests cover successful and failure cases.
- Documentation and tests agree with the implementation.

**Implementation boundary:** Week 1 delivers domain models, ports, contracts, utilities, tests, and design documentation. Database adapters, HTTP endpoints, desktop screens, and real authentication integrations are deferred to Week 2.