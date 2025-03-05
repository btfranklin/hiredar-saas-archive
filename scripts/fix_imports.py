#!/usr/bin/env python
"""
Script to fix import ordering and remove unused imports in Python files.

This script uses isort to organize imports and autoflake to remove unused imports.
"""

import os
import subprocess
import sys
from pathlib import Path


def find_python_files(
    path: str = ".", exclude_dirs: list[str] | None = None
) -> list[str]:
    """Find all Python files in the given path, excluding specified directories."""
    if exclude_dirs is None:
        exclude_dirs = [".venv", "__pycache__", "migrations"]

    result: list[str] = []
    for root, _, files in os.walk(path):
        # Skip excluded directories
        if any(excluded in root for excluded in exclude_dirs):
            continue
        for file in files:
            if file.endswith(".py"):
                result.append(os.path.join(root, file))
    return result


def remove_unused_imports(file_path: str) -> None:
    """Remove unused imports in a file using autoflake."""
    print(f"Removing unused imports in {file_path}")

    # Install autoflake if not already installed
    try:
        subprocess.run(
            ["pdm", "run", "autoflake", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing autoflake using PDM...")
        subprocess.run(
            ["pdm", "add", "-d", "autoflake"],
            check=True,
        )

    # Run autoflake on the file using PDM
    # --in-place: Modify the file in place
    # --remove-all-unused-imports: Remove all unused imports
    # --remove-unused-variables: Remove unused variables
    result = subprocess.run(
        [
            "pdm",
            "run",
            "autoflake",
            "--in-place",
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            file_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"Error removing unused imports in {file_path}:")
        print(result.stderr)
    else:
        print(f"Successfully removed unused imports in {file_path}")


def fix_imports(file_path: str) -> None:
    """Fix import ordering in a file using isort."""
    print(f"Fixing import ordering in {file_path}")

    # Install isort if not already installed
    try:
        subprocess.run(
            ["pdm", "run", "isort", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing isort using PDM...")
        subprocess.run(
            ["pdm", "add", "-d", "isort"],
            check=True,
        )

    # Run isort on the file using PDM
    result = subprocess.run(
        ["pdm", "run", "isort", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"Error fixing import ordering in {file_path}:")
        print(result.stderr)
    else:
        print(f"Successfully fixed import ordering in {file_path}")


def process_file(file_path: str) -> None:
    """Process a single file by removing unused imports and fixing import ordering."""
    # First remove unused imports, then fix the ordering
    remove_unused_imports(file_path)
    fix_imports(file_path)


def main() -> None:
    """Main function to fix imports in Python files."""
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            # Fix all Python files in the project
            script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            project_root = script_dir.parent
            files = find_python_files(str(project_root))
            print(f"Found {len(files)} Python files to process")
            for file_path in files:
                process_file(file_path)
        else:
            # Fix specific files or directories
            for path in sys.argv[1:]:
                if os.path.isdir(path):
                    files = find_python_files(path)
                    print(f"Found {len(files)} Python files in {path}")
                    for file_path in files:
                        process_file(file_path)
                elif os.path.isfile(path) and path.endswith(".py"):
                    process_file(path)
                else:
                    print(
                        f"Warning: {path} is not a Python file or directory. Skipping."
                    )
    else:
        print("Usage:")
        print("  ./scripts/fix_imports.py --all             # Fix all Python files")
        print("  ./scripts/fix_imports.py path/to/file.py   # Fix a specific file")
        print(
            "  ./scripts/fix_imports.py path/to/dir       # Fix all files in a directory"
        )


if __name__ == "__main__":
    main()
