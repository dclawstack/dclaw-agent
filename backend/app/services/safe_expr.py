"""Safe expression evaluator for agent condition nodes.

We forbid: function calls, imports, attribute access on dunders,
subscripting via slices, generator/lambda/list-comp, anything beyond
boolean/comparison/arithmetic over the supplied variables.
"""
from __future__ import annotations

import ast
import operator
from typing import Any


class UnsafeConditionError(ValueError):
    """Raised when a condition uses a disallowed construct."""


_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

_UNARY_OPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}

_CMP_OPS: dict[type[ast.cmpop], Any] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


def safe_eval(expr: str, variables: dict[str, Any]) -> Any:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UnsafeConditionError(f"invalid expression: {exc.msg}") from exc
    return _eval_node(tree.body, variables)


def _eval_node(node: ast.AST, variables: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id.startswith("_"):
            raise UnsafeConditionError(f"reserved identifier: {node.id}")
        if node.id not in variables:
            raise UnsafeConditionError(f"unknown variable: {node.id}")
        return variables[node.id]

    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, variables) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        return any(values)

    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise UnsafeConditionError(f"unary op not allowed: {type(node.op).__name__}")
        return op(_eval_node(node.operand, variables))

    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise UnsafeConditionError(f"binary op not allowed: {type(node.op).__name__}")
        return op(_eval_node(node.left, variables), _eval_node(node.right, variables))

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, variables)
        for op_node, right_node in zip(node.ops, node.comparators):
            op = _CMP_OPS.get(type(op_node))
            if op is None:
                raise UnsafeConditionError(
                    f"comparison not allowed: {type(op_node).__name__}"
                )
            right = _eval_node(right_node, variables)
            if not op(left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.Subscript):
        target = _eval_node(node.value, variables)
        index = _eval_node(node.slice, variables)
        return target[index]

    if isinstance(node, ast.List):
        return [_eval_node(e, variables) for e in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(e, variables) for e in node.elts)

    raise UnsafeConditionError(f"node type not allowed: {type(node).__name__}")
