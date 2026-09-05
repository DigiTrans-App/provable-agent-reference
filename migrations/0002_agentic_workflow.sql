BEGIN;

CREATE TABLE IF NOT EXISTS agent_activity_records (
    activity_offset bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id text NOT NULL UNIQUE,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    run_id text NOT NULL REFERENCES runs(run_id),
    sequence bigint NOT NULL CHECK (sequence >= 0),
    previous_event_hash text,
    event_type text NOT NULL,
    body jsonb NOT NULL,
    body_hash text NOT NULL CHECK (body_hash ~ '^sha256:[0-9a-f]{64}$'),
    record jsonb NOT NULL,
    record_hash text NOT NULL CHECK (record_hash ~ '^sha256:[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (run_id, sequence),
    CHECK ((sequence = 0 AND previous_event_hash IS NULL) OR
           (sequence > 0 AND previous_event_hash IS NOT NULL AND
            previous_event_hash ~ '^sha256:[0-9a-f]{64}$'))
);

DROP TRIGGER IF EXISTS agent_activity_records_append_only ON agent_activity_records;
CREATE TRIGGER agent_activity_records_append_only
BEFORE UPDATE OR DELETE ON agent_activity_records
FOR EACH ROW EXECUTE FUNCTION reject_journal_mutation();

COMMIT;
