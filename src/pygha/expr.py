# src/pygha/expr.py
from typing import Any


class Expression:
    def __init__(self, expr: str):
        self.expr = expr

    def __str__(self) -> str:
        return self.expr

    def __and__(self, other: Any) -> "Expression":
        return Expression(f"({self.expr}) && ({other})")

    def __or__(self, other: Any) -> "Expression":
        return Expression(f"({self.expr}) || ({other})")

    def __invert__(self) -> "Expression":
        return Expression(f"!({self.expr})")

    def __eq__(self, other: Any) -> "Expression":  # type: ignore[override]
        val = f"'{other}'" if isinstance(other, str) else str(other)
        return Expression(f"{self.expr} == {val}")

    def __ne__(self, other: Any) -> "Expression":  # type: ignore[override]
        val = f"'{other}'" if isinstance(other, str) else str(other)
        return Expression(f"{self.expr} != {val}")


class ContextHelper:
    def __init__(self, name: str):
        self._name = name

    def __getattr__(self, item: str) -> Expression:
        return Expression(f"{self._name}.{item}")

    def __str__(self) -> str:
        return self._name


# Public API helpers
github = ContextHelper("github")
runner = ContextHelper("runner")
env = ContextHelper("env")


# Functions
def always() -> Expression:
    return Expression("always()")


def success() -> Expression:
    return Expression("success()")


def failure() -> Expression:
    return Expression("failure()")
