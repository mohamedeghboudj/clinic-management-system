-- Design reference for synthetic development. Review and translate into versioned migrations.
-- Never run on the meeting project during kickoff. Requires Supabase auth.users and btree_gist.
BEGIN;
CREATE SCHEMA clinic_app;
REVOKE ALL ON SCHEMA clinic_app FROM PUBLIC, anon, authenticated;
SET LOCAL search_path = clinic_app, extensions, pg_catalog;
CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA extensions;

CREATE TABLE clinic (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    timezone text NOT NULL,
    currency text NOT NULL CHECK (currency = 'DZD'),
    phone text,
    email text,
    address_line1 text,
    city text,
    region text,
    postal_code text,
    country_code text,
    active boolean NOT NULL,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0)
);

CREATE TABLE opening_period (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    weekday smallint NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    opens_at time NOT NULL,
    closes_at time NOT NULL,
    PRIMARY KEY (clinic_id, weekday, opens_at),
    CHECK (opens_at < closes_at)
);

CREATE TABLE person (
    id uuid PRIMARY KEY,
    given_name text NOT NULL,
    family_name text NOT NULL,
    birth_date date,
    phone text,
    email text,
    address_line1 text,
    city text,
    region text,
    postal_code text,
    country_code text,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0)
);

CREATE TABLE patient (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    person_id uuid NOT NULL REFERENCES person(id),
    patient_number text NOT NULL,
    emergency_phone text,
    emergency_email text,
    archived_at timestamptz,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    UNIQUE (clinic_id, patient_number),
    UNIQUE (clinic_id, person_id)
);

CREATE TABLE staff (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    person_id uuid NOT NULL REFERENCES person(id),
    staff_number text NOT NULL,
    hired_on date NOT NULL,
    active boolean NOT NULL,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    UNIQUE (clinic_id, staff_number),
    UNIQUE (clinic_id, person_id)
);

CREATE TABLE doctor (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    staff_id uuid NOT NULL,
    specialty text NOT NULL,
    licence_number text NOT NULL,
    active boolean NOT NULL,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, staff_id) REFERENCES staff(clinic_id, id),
    UNIQUE (clinic_id, staff_id),
    UNIQUE (clinic_id, licence_number)
);

CREATE TABLE account (
    id uuid PRIMARY KEY REFERENCES auth.users(id),
    person_id uuid NOT NULL UNIQUE REFERENCES person(id),
    username text NOT NULL UNIQUE,
    enabled boolean NOT NULL,
    auth_version integer NOT NULL CHECK (auth_version >= 1),
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0)
);

CREATE TABLE membership (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    account_id uuid NOT NULL REFERENCES account(id),
    staff_id uuid,
    patient_id uuid,
    active boolean NOT NULL,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, staff_id) REFERENCES staff(clinic_id, id),
    FOREIGN KEY (clinic_id, patient_id) REFERENCES patient(clinic_id, id),
    UNIQUE (clinic_id, account_id)
);

CREATE TABLE staff_role (
    code text PRIMARY KEY
);

CREATE TABLE permission (
    code text PRIMARY KEY
);

CREATE TABLE membership_role (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    membership_id uuid NOT NULL,
    role text NOT NULL REFERENCES staff_role(code),
    PRIMARY KEY (clinic_id, membership_id, role),
    FOREIGN KEY (clinic_id, membership_id) REFERENCES membership(clinic_id, id)
);

CREATE TABLE role_grant (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    role text NOT NULL REFERENCES staff_role(code),
    permission text NOT NULL REFERENCES permission(code),
    scope text NOT NULL CHECK (scope IN ('CLINIC','ASSIGNED','OWN')),
    PRIMARY KEY (clinic_id, role, permission, scope)
);

CREATE TABLE grant_field (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    role text NOT NULL,
    permission text NOT NULL,
    scope text NOT NULL,
    field_name text NOT NULL,
    PRIMARY KEY (clinic_id, role, permission, scope, field_name),
    FOREIGN KEY (clinic_id, role, permission, scope) REFERENCES role_grant(clinic_id, role, permission, scope)
);

CREATE TABLE room (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    number text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('CONSULTATION','OPERATING','WARD')),
    capacity integer NOT NULL CHECK (capacity > 0),
    status text NOT NULL CHECK (status IN ('ACTIVE','OUT_OF_SERVICE')),
    status_reason text,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    UNIQUE (clinic_id, number)
);

CREATE TABLE room_exception (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    room_id uuid NOT NULL,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    reason_code text NOT NULL,
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, room_id) REFERENCES room(clinic_id, id),
    CHECK (starts_at < ends_at)
);

CREATE TABLE doctor_exception (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    doctor_id uuid NOT NULL,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    reason_code text NOT NULL,
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, doctor_id) REFERENCES doctor(clinic_id, id),
    CHECK (starts_at < ends_at)
);

CREATE TABLE appointment (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    patient_id uuid NOT NULL,
    doctor_id uuid NOT NULL,
    room_id uuid NOT NULL,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('SCHEDULED','CHECKED_IN','COMPLETED','CANCELLED','NO_SHOW')),
    reason_summary text,
    cancellation_reason text,
    updated_at timestamptz NOT NULL,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, patient_id) REFERENCES patient(clinic_id, id),
    FOREIGN KEY (clinic_id, doctor_id) REFERENCES doctor(clinic_id, id),
    FOREIGN KEY (clinic_id, room_id) REFERENCES room(clinic_id, id),
    CHECK (starts_at < ends_at),
    EXCLUDE USING gist (clinic_id WITH =, doctor_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) WHERE (status IN ('SCHEDULED','CHECKED_IN')),
    EXCLUDE USING gist (clinic_id WITH =, room_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) WHERE (status IN ('SCHEDULED','CHECKED_IN'))
);

CREATE TABLE consultation (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    appointment_id uuid NOT NULL,
    note text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('DRAFT','FINAL')),
    finalized_at timestamptz,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, appointment_id) REFERENCES appointment(clinic_id, id),
    UNIQUE (clinic_id, appointment_id),
    CHECK ((status = 'FINAL') = (finalized_at IS NOT NULL))
);

CREATE TABLE clinical_entry (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    consultation_id uuid,
    standalone_patient_id uuid,
    author_id uuid NOT NULL,
    kind text NOT NULL,
    content text NOT NULL,
    recorded_at timestamptz NOT NULL,
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, consultation_id) REFERENCES consultation(clinic_id, id),
    FOREIGN KEY (clinic_id, standalone_patient_id) REFERENCES patient(clinic_id, id),
    FOREIGN KEY (clinic_id, author_id) REFERENCES doctor(clinic_id, id),
    CHECK (num_nonnulls(consultation_id, standalone_patient_id) = 1)
);

CREATE TABLE amendment (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    entry_id uuid NOT NULL,
    author_id uuid NOT NULL,
    reason text NOT NULL,
    replacement_content text NOT NULL,
    recorded_at timestamptz NOT NULL,
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, entry_id) REFERENCES clinical_entry(clinic_id, id),
    FOREIGN KEY (clinic_id, author_id) REFERENCES doctor(clinic_id, id)
);

CREATE TABLE prescription (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    consultation_id uuid,
    standalone_patient_id uuid,
    standalone_doctor_id uuid,
    status text NOT NULL CHECK (status IN ('DRAFT','ISSUED','CANCELLED')),
    issued_at timestamptz,
    cancel_reason text,
    cancelled_at timestamptz,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, consultation_id) REFERENCES consultation(clinic_id, id),
    FOREIGN KEY (clinic_id, standalone_patient_id) REFERENCES patient(clinic_id, id),
    FOREIGN KEY (clinic_id, standalone_doctor_id) REFERENCES doctor(clinic_id, id),
    CHECK (num_nonnulls(consultation_id, standalone_patient_id) = 1 AND (standalone_patient_id IS NULL) = (standalone_doctor_id IS NULL))
);

CREATE TABLE prescription_item (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    prescription_id uuid NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    medication_name text NOT NULL,
    strength text,
    form text,
    dose text NOT NULL,
    route text NOT NULL,
    frequency text NOT NULL,
    duration text NOT NULL,
    instructions text,
    PRIMARY KEY (clinic_id, prescription_id, position),
    FOREIGN KEY (clinic_id, prescription_id) REFERENCES prescription(clinic_id, id)
);

CREATE TABLE service (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    code text NOT NULL,
    description text NOT NULL,
    price numeric(18,2) NOT NULL CHECK (price >= 0 AND price < 'Infinity'),
    currency text NOT NULL CHECK (currency = 'DZD'),
    duration_minutes integer CHECK (duration_minutes > 0),
    active boolean NOT NULL,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    UNIQUE (clinic_id, code)
);

CREATE TABLE invoice (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    patient_id uuid NOT NULL,
    currency text NOT NULL CHECK (currency = 'DZD'),
    status text NOT NULL CHECK (status IN ('DRAFT','ISSUED','VOID')),
    number text,
    issued_at timestamptz,
    due_on date,
    void_reason text,
    voided_at timestamptz,
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, patient_id) REFERENCES patient(clinic_id, id),
    UNIQUE (clinic_id, number)
);

CREATE TABLE invoice_line (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    description text NOT NULL,
    quantity numeric NOT NULL CHECK (quantity > 0 AND quantity < 'Infinity'),
    unit_price numeric(18,2) NOT NULL CHECK (unit_price >= 0 AND unit_price < 'Infinity'),
    discount_amount numeric(18,2) NOT NULL CHECK (discount_amount BETWEEN 0 AND round(quantity * unit_price, 2)),
    tax_rate numeric NOT NULL CHECK (tax_rate BETWEEN 0 AND 1),
    source_service_id uuid,
    source_consultation_id uuid,
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, invoice_id) REFERENCES invoice(clinic_id, id),
    FOREIGN KEY (clinic_id, source_service_id) REFERENCES service(clinic_id, id),
    FOREIGN KEY (clinic_id, source_consultation_id) REFERENCES consultation(clinic_id, id),
    UNIQUE (clinic_id, invoice_id, position),
    UNIQUE (clinic_id, invoice_id, source_service_id, source_consultation_id)
);

CREATE TABLE invoice_counter (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    year integer NOT NULL,
    last_value bigint NOT NULL CHECK (last_value >= 0),
    PRIMARY KEY (clinic_id, year)
);

CREATE TABLE command_receipt (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    actor_id uuid NOT NULL,
    command_key uuid NOT NULL,
    operation text NOT NULL,
    request_digest bytea NOT NULL,
    result_type text NOT NULL,
    result_id uuid NOT NULL,
    result_version integer NOT NULL,
    committed_at timestamptz NOT NULL,
    PRIMARY KEY (clinic_id, actor_id, command_key),
    FOREIGN KEY (clinic_id, actor_id) REFERENCES membership(clinic_id, account_id)
);

CREATE TABLE payment (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    amount numeric(18,2) NOT NULL CHECK (amount > 0 AND amount < 'Infinity'),
    method text NOT NULL CHECK (method IN ('CASH','CARD','CHEQUE','BANK_TRANSFER')),
    received_at timestamptz NOT NULL,
    received_by uuid NOT NULL,
    idempotency_key uuid NOT NULL,
    external_reference text,
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, invoice_id) REFERENCES invoice(clinic_id, id),
    FOREIGN KEY (clinic_id, received_by, idempotency_key) REFERENCES command_receipt(clinic_id, actor_id, command_key) DEFERRABLE INITIALLY DEFERRED,
    UNIQUE (clinic_id, received_by, idempotency_key)
);

CREATE TABLE payment_reversal (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    payment_id uuid NOT NULL,
    amount numeric(18,2) NOT NULL CHECK (amount > 0 AND amount < 'Infinity'),
    reason text NOT NULL,
    reversed_at timestamptz NOT NULL,
    reversed_by uuid NOT NULL,
    idempotency_key uuid NOT NULL,
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, payment_id) REFERENCES payment(clinic_id, id),
    FOREIGN KEY (clinic_id, reversed_by, idempotency_key) REFERENCES command_receipt(clinic_id, actor_id, command_key) DEFERRABLE INITIALLY DEFERRED,
    UNIQUE (clinic_id, reversed_by, idempotency_key)
);

CREATE TABLE audit_entry (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    actor_id uuid,
    action text NOT NULL,
    resource_type text NOT NULL,
    resource_id uuid,
    outcome text NOT NULL,
    occurred_at timestamptz NOT NULL,
    correlation_id uuid NOT NULL,
    reason_code text,
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, actor_id) REFERENCES membership(clinic_id, account_id)
);

CREATE TABLE outbox_event (
    clinic_id uuid NOT NULL REFERENCES clinic(id),
    id uuid NOT NULL,
    event_type text NOT NULL,
    entity_id uuid NOT NULL,
    entity_version integer NOT NULL,
    actor_id uuid NOT NULL,
    occurred_at timestamptz NOT NULL,
    correlation_id uuid NOT NULL,
    delivered_at timestamptz,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    PRIMARY KEY (clinic_id, id),
    FOREIGN KEY (clinic_id, actor_id) REFERENCES membership(clinic_id, account_id)
);

CREATE INDEX patient_person_lookup ON patient (person_id, clinic_id);
CREATE INDEX doctor_day ON appointment (clinic_id, doctor_id, starts_at, id);
CREATE INDEX clinic_patient_visit ON appointment (clinic_id, patient_id, starts_at, id);
CREATE INDEX history_visit ON clinical_entry (clinic_id, consultation_id, recorded_at, id);
CREATE INDEX history_standalone ON clinical_entry (clinic_id, standalone_patient_id, recorded_at, id);
CREATE INDEX history_corrections ON amendment (clinic_id, entry_id, recorded_at, id);
CREATE INDEX patient_invoices ON invoice (clinic_id, patient_id, id);
CREATE INDEX invoice_payments ON payment (clinic_id, invoice_id, received_at, id);
CREATE INDEX payment_reversals ON payment_reversal (clinic_id, payment_id, id);
CREATE INDEX pending_events ON outbox_event (occurred_at, id) WHERE delivered_at IS NULL;
REVOKE ALL ON ALL TABLES IN SCHEMA clinic_app FROM PUBLIC, anon, authenticated;
COMMIT;
