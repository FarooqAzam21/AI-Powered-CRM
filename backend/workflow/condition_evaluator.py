"""
P5 — Condition Evaluator
Pure functions for evaluating workflow conditions against CRM context.
Supports AND/OR groups with field comparison operators.
No database calls — all context must be pre-fetched.
"""
from typing import Any, Dict, List, Optional
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Allowed operators ────────────────────────────────────────────────────────
OPERATORS = {
    "eq", "ne", "contains", "not_contains", "starts_with",
    "gt", "gte", "lt", "lte", "is_empty", "is_not_empty",
    "in", "not_in",
    # aliases
    "equals", "not_equals", "greater_than", "greater_than_or_equal",
    "less_than", "less_than_or_equal", "in_list", "not_in_list",
}

OPERATOR_MAP = {
    "equals": "eq",
    "not_equals": "ne",
    "greater_than": "gt",
    "greater_than_or_equal": "gte",
    "less_than": "lt",
    "less_than_or_equal": "lte",
    "in_list": "in",
    "not_in_list": "not_in",
}


def _coerce(value: Any, operator: str) -> Any:
    """Best-effort numeric coercion for comparison operators."""
    if operator in {"gt", "gte", "lt", "lte"}:
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    return value


def _get_nested(obj: dict, path: str) -> Any:
    """
    Resolve a dot-separated field path from a context dict.
    e.g. 'deal.amount' → context['deal']['amount']
    """
    parts = path.split(".")
    cur = obj
    for part in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def evaluate_condition(condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Evaluate a single condition node against the CRM context dict.

    Condition schema:
      {
        "field": "deal.amount",          # dot-path into context
        "operator": "gt",                # one of OPERATORS
        "value": 5000,                   # comparison value
      }
    """
    field = condition.get("field", "")
    operator = condition.get("operator", "eq")
    operator = OPERATOR_MAP.get(operator, operator)
    expected = condition.get("value")

    if operator not in OPERATORS:
        logger.warning("Unknown operator '%s' — treating as False", operator)
        return False

    actual = _get_nested(context, field)

    try:
        if operator == "is_empty":
            return actual is None or actual == "" or actual == []
        if operator == "is_not_empty":
            return actual is not None and actual != "" and actual != []

        actual = _coerce(actual, operator)
        expected_coerced = _coerce(expected, operator)

        if operator == "eq":
            return str(actual).lower() == str(expected_coerced).lower() if isinstance(actual, str) else actual == expected_coerced
        if operator == "ne":
            return actual != expected_coerced
        if operator == "contains":
            return expected_coerced in str(actual).lower() if actual is not None else False
        if operator == "not_contains":
            return expected_coerced not in str(actual).lower() if actual is not None else True
        if operator == "starts_with":
            return str(actual).lower().startswith(str(expected_coerced).lower()) if actual else False
        if operator == "gt":
            return actual > expected_coerced
        if operator == "gte":
            return actual >= expected_coerced
        if operator == "lt":
            return actual < expected_coerced
        if operator == "lte":
            return actual <= expected_coerced
        if operator == "in":
            return actual in (expected_coerced if isinstance(expected_coerced, list) else [expected_coerced])
        if operator == "not_in":
            return actual not in (expected_coerced if isinstance(expected_coerced, list) else [expected_coerced])
    except Exception as exc:
        logger.warning("Condition eval error field=%s op=%s: %s", field, operator, exc)
        return False

    return False


def evaluate_group(group: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Evaluate a condition group.

    Group schema:
      {
        "logic": "AND" | "OR",        # default AND
        "conditions": [...],           # list of condition dicts OR nested groups
      }
    """
    logic = group.get("logic", "AND").upper()
    items = group.get("conditions", [])

    if not items:
        return True  # Empty group → pass-through

    results = []
    for item in items:
        if "conditions" in item:
            # Nested group
            results.append(evaluate_group(item, context))
        else:
            results.append(evaluate_condition(item, context))

    if logic == "OR":
        return any(results)
    return all(results)


def evaluate_all_conditions(
    condition_groups: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> bool:
    """
    Evaluate a list of top-level condition groups (implicitly AND between groups).
    Returns True if all groups pass.
    """
    if not condition_groups:
        return True  # No conditions → always match
    return all(evaluate_group(g, context) for g in condition_groups)


class ConditionEvaluator:
    """Class wrapper for condition evaluation."""

    @staticmethod
    def evaluate(condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return evaluate_condition(condition, context)

    @staticmethod
    def evaluate_group(group: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return evaluate_group(group, context)

    @staticmethod
    def evaluate_all(condition_groups: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        return evaluate_all_conditions(condition_groups, context)

