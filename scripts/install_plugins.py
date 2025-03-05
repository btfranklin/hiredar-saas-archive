#!/usr/bin/env python
"""Install custom pylint plugins."""

import subprocess


def main() -> None:
    """Install the pylint plugins in development mode."""
    # Run pdm add -d -e . to install the plugins as a development dependency
    print("Installing pylint plugins using PDM...")
    subprocess.check_call(["pdm", "add", "-d", "-e", "."])

    print("Pylint plugins installed successfully.")
    print("You can now run pylint with your custom plugins.")


if __name__ == "__main__":
    main()
