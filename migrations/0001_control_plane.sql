BEGIN;

CREATE TABLE IF NOT EXISTS runs (
    run_id text PRIMARY KEY,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    requester_subject text NOT NULL,
    purpose text NOT NULL,
    audience text NOT NULL,
    risk_tier smallint NOT NULL CHECK (risk_tier BETWEEN 0 AND 4),
    policy_version text NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (tenant_id, case_id, run_id)
);

CREATE TABLE IF NOT EXISTS capability_grants (
    grant_id text PRIMARY KEY,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    run_id text NOT NULL REFERENCES runs(run_id),
    parent_grant_id text REFERENCES capability_grants(grant_id),
    grant_document jsonb NOT NULL,
    grant_hash text NOT NULL CHECK (grant_hash ~ '^sha256:[0-9a-f]{64}$'),
    valid_until timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    tenant_id text NOT NULL,
    subject text NOT NULL,
    operation text NOT NULL,
    key_commitment text NOT NULL,
    request_hash text NOT NULL,
    result_ref text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (tenant_id, subject, operation, key_commitment)
);

CREATE TABLE IF NOT EXISTS journal_records (
    journal_offset bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id text NOT NULL UNIQUE,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    run_id text NOT NULL REFERENCES runs(run_id),
    sequence bigint NOT NULL CHECK (sequence >= 0),
    previous_event_hash text,
    body jsonb NOT NULL,
    body_hash text NOT NULL CHECK (body_hash ~ '^sha256:[0-9a-f]{64}$'),
    record_hash text NOT NULL CHECK (record_hash ~ '^sha256:[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (run_id, sequence),
    CHECK ((sequence = 0 AND previous_event_hash IS NULL) OR
           (sequence > 0 AND previous_event_hash IS NOT NULL AND
            previous_event_hash ~ '^sha256:[0-9a-f]{64}$'))
);

CREATE OR REPLACE FUNCTION reject_journal_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'journal_records are append-only';
END;
$$;

DROP TRIGGER IF EXISTS journal_records_append_only ON journal_records;
CREATE TRIGGER journal_records_append_only
BEFORE UPDATE OR DELETE ON journal_records
FOR EACH ROW EXECUTE FUNCTION reject_journal_mutation();

CREATE TABLE IF NOT EXISTS outbox (
    outbox_id text PRIMARY KEY,
    tenant_id text NOT NULL,
    aggregate_type text NOT NULL,
    aggregate_id text NOT NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    claimed_at timestamptz,
    claimed_by text,
    published_at timestamptz,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error text
);

CREATE INDEX IF NOT EXISTS outbox_pending_idx
ON outbox (available_at, created_at) WHERE published_at IS NULL;

CREATE TABLE IF NOT EXISTS artifacts (
    digest text PRIMARY KEY CHECK (digest ~ '^sha256:[0-9a-f]{64}$'),
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    run_id text NOT NULL REFERENCES runs(run_id),
    media_type text NOT NULL,
    byte_length bigint NOT NULL CHECK (byte_length >= 0),
    storage_key text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN ('staged', 'available', 'unavailable')),
    reconcile_claimed_at timestamptz,
    reconcile_claimed_by text,
    reconcile_attempts integer NOT NULL DEFAULT 0 CHECK (reconcile_attempts >= 0),
    reconcile_available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    last_reconcile_error text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finalized_at timestamptz
);

CREATE INDEX IF NOT EXISTS artifacts_reconcile_idx
ON artifacts (reconcile_available_at, created_at) WHERE status = 'staged';

COMMIT;
