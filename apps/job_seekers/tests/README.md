# Job Seekers App Tests

This directory contains tests for the job_seekers app. The tests are organized into two main categories:

## Unit Tests

Located in the `unit/` directory, these tests focus on testing individual components in isolation. They use mocks and stubs to avoid dependencies on external systems.

Examples of unit tests include:

- Testing XML processing and sanitization
- Testing resume parsing functionality
- Testing profile updates

## Integration Tests

Located in the `integration/` directory, these tests verify that different components of the system work correctly together. They may make real API calls to external services like OpenAI.

### Resume Ingestion Test

The `test_resume_ingestion.py` file contains an integration test that verifies the entire pipeline from resume processing to talent sheet generation:

1. Process sample resumes to create job seeker profiles
2. Generate talent sheets for the job seekers who opt into the talent pool
3. Generate an HTML report to inspect the quality of the generated talent sheets

The test follows the same workflow as the production system:

- Creates test users with job_seeker type
- Processes resumes through the same pipeline used in the production system
- Uses the talent sheet generation task that would be triggered when users join the talent pool
- Outputs a comprehensive HTML report showing the talent sheets with promotional blurbs and role recommendations

**Note:** This test makes real API calls to OpenAI and should be run manually, not in automated CI/CD pipelines.

## Manual Tests

Some tests are designed to be run manually only and are not discovered by the test runner. These include:

- `manual_resume_ingestion.py` - Tests the resume ingestion and talent sheet generation with real API calls

### Running Manual Tests

To run a manual test, you must explicitly set the environment variable `ALLOW_MANUAL_TESTS=1`:

```bash
# Run the manual resume ingestion test
ALLOW_MANUAL_TESTS=1 python manage.py test apps.job_seekers.tests.integration.manual_resume_ingestion
```

⚠️ **WARNING**: Manual tests typically involve real API calls that may incur costs.

## Running Tests

To run unit tests:

```bash
python manage.py test apps.job_seekers.tests.unit
```

To run integration tests (requires API keys):

```bash
python manage.py test apps.job_seekers.tests.integration
```

To run a specific test:

```bash
python manage.py test apps.job_seekers.tests.integration.manual_resume_ingestion
```
