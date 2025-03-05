# Hiredar Linting Guide

This document outlines the linting setup and tools for the Hiredar project.

## Setup Overview

Hiredar uses pylint for code quality checking with custom configurations to enforce project-specific coding standards, including:

- Type annotations for all functions and methods
- Using native Python types (`list`, `dict`, `tuple`) instead of `typing` module types
- Using `| None` syntax instead of `Optional[T]` for optional parameters
- Django-specific linting rules via pylint-django

## Tools Used

- **PDM**: Python Dependency Manager used for managing all dependencies
- **pylint**: The primary linting tool
- **pylint-django**: Plugin for Django-specific linting rules
- **Custom pylint plugin**: Enforces our type annotation preferences
- **isort**: Used for sorting imports

## Installation

1. Install the custom pylint plugins using PDM:

```bash
# Make sure the script is executable
chmod +x scripts/install_plugins.py

# Install the plugins as a development dependency with PDM
./scripts/install_plugins.py
```

This only needs to be done once, or whenever the custom plugins are updated.

## Running the Linter

To lint your code:

```bash
# Make sure the script is executable
chmod +x scripts/lint.py

# Run the linter on the entire project
./scripts/lint.py

# Or run on a specific file or directory
./scripts/lint.py apps/authentication/
./scripts/lint.py apps/authentication/models.py
```

This will run pylint with our custom configuration and provide a detailed report.

## Linting Preferences

The project follows these linting preferences:

1. **Python Version**: Uses Python 3.12 features

2. **Type Annotations**:
   - All functions and methods should have type annotations
   - Prefer native types over typing module types:
     - `list` instead of `List`
     - `dict` instead of `Dict`
     - `tuple` instead of `Tuple`
   - Use `| None` instead of `Optional[T]` for optional parameters

3. **Django Best Practices**:
   - Class-based views are preferred over function-based views
   - Models should have descriptive docstrings
   - Views should document their purposes and expected inputs/outputs

## Custom Pylint Plugin

The project includes a custom pylint plugin (`pylint_plugins`) that enforces our type annotation preferences:

- It warns when `typing.List`, `typing.Dict`, or `typing.Tuple` are used instead of native types
- It warns when `Optional[T]` is used instead of `T | None` syntax

## Automated Fixes

You can use the `scripts/fix_imports.py` script to automatically fix import order using isort:

```bash
# Make sure the script is executable
chmod +x scripts/fix_imports.py

# Fix imports in a specific file
./scripts/fix_imports.py path/to/file.py

# Fix imports in all Python files
./scripts/fix_imports.py --all
```

## Continuous Integration

The linting rules are also enforced in CI/CD pipelines. Pull requests will fail CI checks if they don't comply with our linting standards.

## IDE Integration

For the best development experience, configure your IDE (Cursor) to use our pylint configuration. This will highlight issues as you write code.
