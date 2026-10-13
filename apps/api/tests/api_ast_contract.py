"""Pure AST policies shared by API source and architecture fitness tests."""

import ast
from collections import Counter


def deprecated_dict_calls(tree: ast.AST) -> list[int]:
    """Recognize exact, lexically unshadowed unittest.mock.patch imports only.

    This is a conservative syntax gate, not runtime type or namespace proof.
    Other imports, wildcard imports and any lexical rebinding keep refusal.
    """
    bindings: Counter[str] = Counter()
    candidates: set[str] = set()
    wildcard = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    wildcard = True
                    continue
                name = alias.asname or alias.name.split(".")[0]
                bindings[name] += 1
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.level == 0
                    and node.module == "unittest.mock"
                    and alias.name == "patch"
                ):
                    candidates.add(name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bindings[node.id] += 1
        elif isinstance(node, ast.arg):
            bindings[node.arg] += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bindings[node.name] += 1
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bindings[node.name] += 1
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            bindings[node.name] += 1
        elif isinstance(node, ast.MatchMapping) and node.rest:
            bindings[node.rest] += 1
    allowed = (
        set() if wildcard else {name for name in candidates if bindings[name] == 1}
    )
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "dict"
        and not (
            isinstance(node.func.value, ast.Name) and node.func.value.id in allowed
        )
    ]
