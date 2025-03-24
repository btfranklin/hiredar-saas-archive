# Hiredar Testing Guide

This document provides a basic overview of testing in the Hiredar project.

## Running Tests

The Hiredar project uses Django's standard testing framework. To run tests:

```bash
# Run all tests
python manage.py test

# Run tests with more verbose output
python manage.py test -v 2

# Run tests for a specific app
python manage.py test apps.job_seekers

# Run tests for a specific module
python manage.py test apps.job_seekers.tests.test_xml_sanitization

# Run a specific test class
python manage.py test apps.job_seekers.tests.test_xml_sanitization.XMLSanitizationTests

# Run a specific test method
python manage.py test apps.job_seekers.tests.test_xml_sanitization.XMLSanitizationTests.test_character_replacements
```

## Test Structure

Tests are organized within each app in the project, following these conventions:

- Tests are located in a `tests/` directory within each app
- Each test directory contains an `__init__.py` file
- Test files are named with a `test_` prefix (e.g., `test_models.py`, `test_views.py`)
- Test classes inherit from Django's `TestCase` or `SimpleTestCase`
- Test methods are named with a `test_` prefix

Example test structure:

```tree
apps/
├── authentication/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   └── test_views.py
├── job_seekers/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_xml_sanitization.py
│   │   └── test_xml_error_reporting.py
├── jobs/
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_models.py
├── messaging/
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_models.py
├── core/
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_views.py
└── recruiters/
    ├── tests/
        ├── __init__.py
        └── test_models.py
```

## Test Types

The project uses these types of tests:

- **Unit Tests**: Test individual components in isolation
- **SimpleTestCase**: For tests that don't require database access
- **TestCase**: For tests that require database access (automatically creates and destroys a test database)

## Best Practices

When writing tests for the Hiredar project:

1. **Use Django's test classes**:
   - Use `SimpleTestCase` for tests that don't need database access
   - Use `TestCase` for tests that need database access

2. **Follow naming conventions**:
   - Name test files with the `test_` prefix
   - Name test methods with the `test_` prefix

3. **Write clear test methods**:
   - Each test method should test a single behavior
   - Use descriptive test method names
   - Add docstrings to test methods explaining what's being tested

4. **Keep tests independent**:
   - Tests should not depend on the outcome of other tests
   - Use `setUp` and `tearDown` methods to create and clean up test data

5. **Test real functionality**:
   - Test behavior, not implementation details
   - Focus on testing requirements and edge cases

6. **Group tests logically**:
   - Use separate files for testing different components (models, views, forms, etc.)
   - Keep related tests in the same file
   - Use descriptive class names that reflect what's being tested

## Test Configuration

The Hiredar project uses a slightly customized test setup:

- The `apps` directory is added to the Python path for proper test discovery

Test configuration is handled in `settings.py` and doesn't require any manual setup to run tests.
