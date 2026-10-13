"""Conservative source policy; LibCST owns Python lexical name resolution."""

import ast

import libcst as cst
from libcst.metadata import (
    PositionProvider,
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
)


def _unproved_bindings(tree: ast.AST) -> tuple[set[str], bool]:
    """Disable the exemption for syntax not modeled by qualified-name metadata.

    This intentionally applies across the file for affected names. It does not
    attempt to infer execution order or invent another lexical scope resolver.
    """
    names: set[str] = set()
    wildcard = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            wildcard |= any(alias.name == "*" for alias in node.names)
        elif isinstance(node, ast.Delete):
            names.update(
                child.id for child in ast.walk(node) if isinstance(child, ast.Name)
            )
        elif isinstance(node, ast.NamedExpr):
            names.update(
                child.id
                for child in ast.walk(node.target)
                if isinstance(child, ast.Name)
            )
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names.add(node.rest)
    return names, wildcard


class _DictionaryCalls(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (QualifiedNameProvider, PositionProvider)

    def __init__(self, unproved: set[str], wildcard: bool) -> None:
        self.unproved = unproved
        self.wildcard = wildcard
        self.lines: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        function = node.func
        if not isinstance(function, cst.Attribute) or function.attr.value != "dict":
            return
        receiver = function.value
        exact_stdlib_import = (
            isinstance(receiver, cst.Name)
            and receiver.value not in self.unproved
            and not self.wildcard
            and self.get_metadata(QualifiedNameProvider, function, set())
            == {QualifiedName("unittest.mock.patch.dict", QualifiedNameSource.IMPORT)}
        )
        if not exact_stdlib_import:
            self.lines.append(self.get_metadata(PositionProvider, node).start.line)


def deprecated_dict_calls(source: str) -> list[int]:
    """Refuse every .dict call except a proved, unshadowed stdlib patch alias."""
    tree = ast.parse(source)
    compile(tree, "<api-deprecation-policy>", "exec")
    visitor = _DictionaryCalls(*_unproved_bindings(tree))
    cst.MetadataWrapper(cst.parse_module(source)).visit(visitor)
    return sorted(visitor.lines)


def ignored_control_flow_type_comments(source: str) -> list[int]:
    """Refuse control-flow comments that cannot be relied on by the native parser."""
    tree = ast.parse(source, type_comments=True)
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, (ast.For, ast.AsyncFor, ast.With, ast.AsyncWith))
        and node.type_comment is not None
    )
