# Resume Processing App Tests

This directory contains tests for the **resume_processing** app, organized into two categories:

## Unit Tests

- Located in `apps/resume_processing/tests/unit`
- Files:
  - `test_xml_error_reporting.py`: Validates XML error reporting utilities
  - `test_xml_sanitization.py`: Ensures XML sanitizer handles edge cases
  - `test_profile_updater.py`: Verifies profile field updates from parsed data

To run unit tests:

```bash
python manage.py test apps.resume_processing.tests.unit
```

## Integration Tests

- Located in `apps/resume_processing/tests/integration`
- Files:
  - `manual_resume_ingestion.py`: End-to-end ingestion and talent sheet generation (manual only)

> ⚠️ **Manual Test**: Requires real API calls to OpenAI and will incur costs.
> Set `ALLOW_MANUAL_TESTS=1` to run:

```bash
ALLOW_MANUAL_TESTS=1 python manage.py test apps.resume_processing.tests.integration.manual_resume_ingestion
```
