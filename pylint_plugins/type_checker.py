"""
Custom pylint plugin for type hint checking.

This plugin enforces the following conventions:
1. Prefer native types (list, dict) over typing module types (List, Dict)
2. Prefer '| None' syntax over Optional[T]
"""

from typing import Any

from astroid.nodes import ImportFrom, Name, Subscript
from pylint.checkers import BaseChecker
from pylint.lint import PyLinter


class TypeHintChecker(BaseChecker):
    """Checker for enforcing preferred type hint styles."""

    name = "type-hint-checker"
    priority = -1
    msgs = {
        "C9001": (
            "Use native type 'list' instead of 'List' from typing",
            "use-native-list",
            "Use Python's native 'list' type instead of 'List' from typing module",
        ),
        "C9002": (
            "Use native type 'dict' instead of 'Dict' from typing",
            "use-native-dict",
            "Use Python's native 'dict' type instead of 'Dict' from typing module",
        ),
        "C9003": (
            "Use native type 'tuple' instead of 'Tuple' from typing",
            "use-native-tuple",
            "Use Python's native 'tuple' type instead of 'Tuple' from typing module",
        ),
        "C9004": (
            "Use 'T | None' syntax instead of 'Optional[T]'",
            "use-union-pipe",
            "Use 'T | None' syntax instead of 'Optional[T]' for optional types",
        ),
    }
    options: tuple[Any, ...] = ()

    def visit_importfrom(self, node: ImportFrom) -> None:
        """Check for imports from typing module."""
        if node.modname == "typing":
            for name, _ in node.names:
                if name in ("List", "Dict", "Tuple"):
                    self.add_message(f"use-native-{name.lower()}", node=node)
                elif name == "Optional":
                    self.add_message("use-union-pipe", node=node)

    def visit_subscript(self, node: Subscript) -> None:
        """Check for usage of typing types in type annotations."""
        if isinstance(node.value, Name):
            value_name = node.value.name
            if value_name == "Optional":
                self.add_message("use-union-pipe", node=node)
            elif value_name in ("List", "Dict", "Tuple"):
                self.add_message(f"use-native-{value_name.lower()}", node=node)


def register(linter: PyLinter) -> None:
    """Register checkers."""
    linter.register_checker(TypeHintChecker(linter))
