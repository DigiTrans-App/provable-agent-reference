BEGIN;

CREATE TABLE IF NOT EXISTS effect_records (
    record_id text PRIMARY KEY,
    record_type text NOT NULL CHECK (record_type IN ('execution_receipt', 'reconciliation')),
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    run_id text NOT NULL REFERENCES runs(run_id),
    document jsonb NOT NULL,
    record_hash text NOT NULL CHECK (record_hash ~ '^sha256:[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (record_type, record_hash)
);

DROP TRIGGER IF EXISTS effect_records_append_only ON effect_records;
CREATE TRIGGER effect_records_append_only
BEFORE UPDATE OR DELETE ON effect_records
FOR EACH ROW EXECUTE FUNCTION reject_journal_mutation();

COMMIT;
