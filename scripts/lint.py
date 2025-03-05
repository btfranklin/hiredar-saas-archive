#!/usr/bin/env python
"""
Linter script to run pylint and mypy on Python files in the project.
Identifies and reports files with issues.
"""

import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict


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


def run_pylint(file_path: str, rcfile: str) -> tuple[float, list[str]]:
    """Run pylint on a single file and return score and messages."""
    # Get the full path to the rcfile
    rcfile_path = str(Path(rcfile).resolve())

    # Build the command using PDM to run pylint
    cmd = ["pdm", "run", "pylint", f"--rcfile={rcfile_path}", file_path]

    # Run pylint using 'with' to properly manage resources
    with subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    ) as process:
        output, _ = process.communicate()

    # Extract score if it exists
    score_match = re.search(r"Your code has been rated at (-?\d+\.\d+)/10", output)
    score = float(score_match.group(1)) if score_match else 0.0

    # Extract messages
    messages: list[str] = []
    for line in output.splitlines():
        if re.search(r"^\S+:\d+:\d+: [EWFRC]\d+", line):
            messages.append(line)

    return score, messages


def process_files(
    files: list[str], rcfile: str
) -> list[tuple[str, float, int, list[str]]]:
    """Process a list of files with pylint and return results."""
    results: list[tuple[str, float, int, list[str]]] = []
    error_counts: DefaultDict[str, int] = defaultdict(int)

    total_files = len(files)
    print(f"Found {total_files} Python files to lint")

    if total_files == 0:
        print("No Python files found. Check your path arguments.")
        return []

    for i, file_path in enumerate(files, 1):
        print(f"Linting file {i}/{total_files}: {file_path}")
        score, messages = run_pylint(file_path, rcfile)

        # Count error types
        for message in messages:
            error_match = re.search(r"[EWFRC]\d+", message)
            if error_match:
                error_counts[error_match.group(0)] += 1

        results.append((file_path, score, len(messages), messages))

    # Print most common error types
    print("\n\n=== Most Common Error Types ===")
    if error_counts:
        for error_type, count in sorted(
            error_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"{error_type}: {count} occurrences")
    else:
        print("No error types found.")

    return results


def print_results(results: list[tuple[str, float, int, list[str]]]) -> None:
    """Print formatted results of linting."""
    # Sort by score (ascending) and then by number of issues (descending)
    results.sort(key=lambda x: (x[1], -x[2]))

    # Print summary of files with issues
    print("\n\n=== Files with Issues ===")
    files_with_issues = 0
    for file_path, score, issue_count, _ in results:
        if issue_count > 0:
            files_with_issues += 1
            print(f"{file_path}: Score {score}/10, {issue_count} issues")

    if files_with_issues == 0:
        print("No files with issues found.")

    # Print the top 5 files with the most issues
    print("\n\n=== Top 5 Files with Most Issues ===")
    top_files = 0
    for file_path, score, issue_count, messages in sorted(
        results, key=lambda x: x[2], reverse=True
    )[:5]:
        if issue_count > 0:
            top_files += 1
            print(f"\n{file_path}: Score {score}/10, {issue_count} issues")
            for message in messages[:5]:  # Show only first 5 messages
                print(f"  {message}")
            if len(messages) > 5:
                print(f"  ... and {len(messages) - 5} more issues")

    if top_files == 0:
        print("No files with issues to display.")


def run_mypy(file_paths: list[str]) -> tuple[int, list[str]]:
    """Run mypy on files and return error count and messages."""
    if not file_paths:
        return 0, []

    # Build the mypy command using the configured parameters
    cmd = [
        "pdm", "run", "mypy", 
        "--namespace-packages", 
        "--explicit-package-bases", 
        "--ignore-missing-imports"
    ]
    cmd.extend(file_paths)

    # Run mypy
    with subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    ) as process:
        output, _ = process.communicate()

    # Extract messages
    messages = [line for line in output.splitlines() if ": error:" in line]
    error_count = len(messages)

    return error_count, messages


def main() -> None:
    """Main function to run the linter on Python files."""
    # Get the project root (one directory up from the scripts directory)
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    project_root = script_dir.parent
    os.chdir(project_root)  # Change to project root to handle paths correctly
    rcfile = str(project_root / ".pylintrc")

    # Handle command line arguments
    if len(sys.argv) > 1:
        paths = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
        files: list[str] = []
        for path in paths:
            # Handle relative paths properly by resolving from project root
            full_path = os.path.normpath(os.path.join(os.getcwd(), path))
            if os.path.isdir(full_path):
                found_files = find_python_files(full_path)
                files.extend(found_files)
            elif os.path.isfile(full_path) and full_path.endswith(".py"):
                files.append(full_path)
            else:
                print(f"Warning: {path} is not a Python file or directory. Skipping.")
    else:
        # By default, lint all Python files in the project
        files = find_python_files(str(project_root))

    if not files:
        print("No Python files found. Check your path arguments.")
        return

    # Run pylint checks
    print("=== Running Pylint Checks ===")
    results = process_files(files, rcfile)
    print_results(results)
    
    # Run mypy checks
    print("\n\n=== Running MyPy Type Checks ===")
    error_count, messages = run_mypy(files)
    
    if error_count > 0:
        print(f"Found {error_count} type errors:")
        for message in messages:
            print(f"  {message}")
    else:
        print("No type errors found.")


if __name__ == "__main__":
    main()
