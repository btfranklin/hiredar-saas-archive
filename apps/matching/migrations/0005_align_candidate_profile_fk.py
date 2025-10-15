"""Align legacy CandidateMatch foreign key to the new CandidateProfile schema."""

from django.db import migrations


RENAME_LEGACY_COLUMN_SQL = """
DO $$
DECLARE
    legacy_column text;
    legacy_attnum integer;
    constraint_row record;
BEGIN
    -- Exit early if the expected column is already present.
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'matching_candidatematch'
          AND column_name = 'candidate_profile_id'
    ) THEN
        RETURN;
    END IF;

    -- Detect the legacy column name that still exists in older databases.
    SELECT column_name
    INTO legacy_column
    FROM information_schema.columns
    WHERE table_name = 'matching_candidatematch'
      AND column_name IN ('talent_sheet_id', 'job_seeker_profile_id', 'jobseeker_profile_id')
    ORDER BY CASE column_name
        WHEN 'talent_sheet_id' THEN 1
        WHEN 'job_seeker_profile_id' THEN 2
        WHEN 'jobseeker_profile_id' THEN 3
        ELSE 4
    END
    LIMIT 1;

    IF legacy_column IS NULL THEN
        -- No legacy column detected; nothing to do.
        RETURN;
    END IF;

    -- Look up the attribute number for the legacy column so we can drop the FK constraint(s).
    SELECT attnum
    INTO legacy_attnum
    FROM pg_attribute
    WHERE attrelid = 'matching_candidatematch'::regclass
      AND attname = legacy_column;

    IF legacy_attnum IS NULL THEN
        RETURN;
    END IF;

    -- Drop any foreign key constraints that still reference the legacy column.
    FOR constraint_row IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'matching_candidatematch'::regclass
          AND contype = 'f'
          AND legacy_attnum = ANY(conkey)
    LOOP
        EXECUTE format(
            'ALTER TABLE matching_candidatematch DROP CONSTRAINT %I',
            constraint_row.conname
        );
    END LOOP;

    -- Finally rename the legacy column so Django can query the table again.
    EXECUTE format(
        'ALTER TABLE matching_candidatematch RENAME COLUMN %I TO candidate_profile_id',
        legacy_column
    );
END $$;
"""


ADD_NEW_FOREIGN_KEY_SQL = """
DO $$
BEGIN
    -- Ensure the expected column exists before attempting to add the constraint.
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'matching_candidatematch'
          AND column_name = 'candidate_profile_id'
    ) THEN
        RETURN;
    END IF;

    -- Skip if a foreign key to candidates_candidateprofile already exists.
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'matching_candidatematch'::regclass
          AND contype = 'f'
          AND confrelid = 'candidates_candidateprofile'::regclass
    ) THEN
        RETURN;
    END IF;

    -- Add the new FK constraint using NOT VALID so that legacy rows can be cleaned up first.
    ALTER TABLE matching_candidatematch
    ADD CONSTRAINT matching_candid_candidate_profile_id_fk
    FOREIGN KEY (candidate_profile_id)
    REFERENCES candidates_candidateprofile(id)
    DEFERRABLE INITIALLY DEFERRED
    NOT VALID;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("matching", "0004_shortlistedmatch"),
        ("candidates", "0005_alter_candidateprofile_options"),
    ]

    operations = [
        migrations.RunSQL(RENAME_LEGACY_COLUMN_SQL, migrations.RunSQL.noop),
        migrations.RunSQL(ADD_NEW_FOREIGN_KEY_SQL, migrations.RunSQL.noop),
    ]

