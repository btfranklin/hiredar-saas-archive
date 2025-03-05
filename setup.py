"""Setup script for custom pylint plugins."""

from setuptools import find_packages, setup

setup(
    name="pylint-plugins",
    version="0.1",
    description="Custom pylint plugins for Hiredar project",
    author="Hiredar Team",
    packages=find_packages(),
    install_requires=[
        "pylint>=2.15.0",
        "astroid>=2.12.0",
    ],
)
