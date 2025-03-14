# XML Error Reporting

## Overview

The Hiredar system processes résumés by converting them to structured XML and extracting data. XML validation and parsing errors are common issues that need to be diagnosed and fixed. This document describes the centralized error reporting system implemented to handle these errors consistently across the codebase.

## Key Features

- **Detailed Error Information**: Shows exact error location (line number, column), problematic character, and context
- **Visual Error Markers**: Creates annotated XML files with error indicators (❌) at the exact error location
- **Consistent UX**: Provides uniform error reporting across different parts of the system
- **Error Diagnostics**: Analyzes error types and suggests possible fixes
- **Centralized Logic**: Eliminates code duplication by centralizing error reporting functions
- **XML Sanitization**: Automatically attempts to fix common XML issues before validation
- **Robust Error Handling**: Properly handles cases where XML content might not be available during errors

## Architecture

The XML error reporting system is implemented as a dedicated module:
`apps/job_seekers/utils/resume_processing/xml_error_reporting.py`

### Core Functions

| Function | Purpose |
|----------|---------|
| `get_error_position()` | Extracts line and column from a ParseError safely |
| `get_error_context()` | Collects context information around an error location |
| `format_error_for_console()` | Formats error details for console display |
| `log_xml_error()` | Logs detailed error information using the logger |
| `create_marked_xml()` | Creates XML content with visual error indicators |
| `save_diagnostic_xml()` | Saves problematic XML to a file with error markers |

## Integration Points

The error reporting system is integrated at these key locations:

1. **LLM Processing**: In `llm_processor.py`, detects and reports XML validation errors immediately after LLM response
   - Includes XML sanitization to automatically fix common issues
   - Preserves XML content even when validation fails for better diagnostics
2. **Processing Pipeline**: In `pipeline.py`, handles XML parsing errors and conversion errors with diagnostic file creation
   - Now properly handles cases where XML isn't available after conversion failure
   - Includes robust null checking to prevent UnboundLocalError exceptions
3. **Diagnostic Command**: In `diagnose_resume.py`, provides detailed console output for XML validation issues

## XML Sanitization

The system includes an XML sanitization function that automatically attempts to fix common issues:

- **Missing Root Element**: Adds `<resume>` tags if missing
- **Unclosed Tags**: Ensures proper closing of the root element
- **Invalid Characters**: Removes problematic control characters
- **HTML Entities**: Replaces HTML entities with their XML equivalents
- **Ampersand Escaping**: Properly escapes ampersands in text

This sanitization happens automatically before validation to reduce the likelihood of errors.

## Usage Examples

### Basic Error Handling

```python
try:
    ET.fromstring(xml_content)
except ET.ParseError as e:
    log_xml_error(e, xml_content)
    # Handle the error
```

### Sanitizing XML Content

```python
# Before validation, apply sanitization
xml_content, was_sanitized = sanitize_xml_if_needed(xml_content)
if was_sanitized:
    logger.info("Applied XML sanitization to fix potential issues")
```

### Saving Diagnostic Files

```python
try:
    parsed_data = parse_resume_xml(xml_content)
except ET.ParseError as e:
    log_xml_error(e, xml_content)
    diagnostic_path = save_diagnostic_xml(
        e, xml_content, file_path, "parsing"
    )
    if diagnostic_path:
        # Provide the path to the user for inspection
```

### Console Output

The error reporting system produces console output that shows:

1. The precise error location with line and column numbers
2. A visual pointer (^) to the exact character causing the error
3. The problematic character with its ASCII code
4. Context lines before and after the error
5. Hints about possible solutions based on the error type

## Error Handling Flow

The system follows this sequence for handling XML errors:

1. First attempt to sanitize the XML to fix common issues
2. If validation still fails, capture detailed information about the error
3. Log the error with specific location and character information
4. Save a diagnostic file with visual markers at the error location
5. Provide the diagnostic file path back to the caller
6. Include error details in the response for proper handling by the caller

## Testing

The system includes unit tests to verify its functionality:
`apps/job_seekers/tests/test_xml_error_reporting.py`

Tests cover all core functions and ensure that the error reporting system works consistently across different error scenarios.

## Future Improvements

- Add support for automatic error correction for common XML issues
- Integrate with frontend to display XML errors in the UI
- Add more detailed error classification and fix suggestions
- Support batch processing of multiple XML errors in a single file
- Implement machine learning-based XML correction for complex cases
