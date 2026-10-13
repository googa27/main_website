"""Conservative deprecation syntax checks using Python compiler symbol tables."""

import ast
import symtable


class _Scope:
    def __init__(self, table, parent, kind, shadows=()):
        self.table = table
        self.parent = parent
        self.kind = kind
        self.shadows = set(shadows)
        self.imports = {}
        self.wildcard = False


class _Calls(ast.NodeVisitor):
    def __init__(self, table):
        self.root = _Scope(table, None, "module")
        self.scope = self.root
        self.scopes = [self.root]
        self.calls = []
        self.spoiled = set()
        self.children = {}
        self.used = set()
        self._tables(table)

    def _tables(self, table):
        children = table.get_children()
        self.children[table.get_id()] = children
        for child in children:
            self._tables(child)

    def _child(self, name, line, kind, parameters=None, optional=False):
        container = self.scope
        while container.table is None:
            container = container.parent
        matches = [
            table
            for table in self.children[container.table.get_id()]
            if table.get_id() not in self.used
            and table.get_name() == name
            and table.get_lineno() == line
            and table.get_type() == kind
            and (parameters is None or set(table.get_parameters()) == parameters)
        ]
        if not matches and optional:
            return None
        if len(matches) != 1:
            raise ValueError("Ambiguous or unsupported compiler scope")
        table = matches[0]
        self.used.add(table.get_id())
        return table

    def _enter(self, table, kind, nodes, shadows=()):
        previous = self.scope
        self.scope = _Scope(table, previous, kind, shadows)
        self.scopes.append(self.scope)
        try:
            for node in nodes:
                self.visit(node)
        finally:
            self.scope = previous

    def _arguments(self, args):
        values = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        if args.vararg:
            values.append(args.vararg)
        if args.kwarg:
            values.append(args.kwarg)
        return values

    def visit_FunctionDef(self, node):
        if node.type_params:
            raise ValueError("Generic annotation scope is not selected")
        for expression in [
            *node.decorator_list,
            *node.args.defaults,
            *[value for value in node.args.kw_defaults if value is not None],
            *[
                arg.annotation
                for arg in self._arguments(node.args)
                if arg.annotation is not None
            ],
            *([node.returns] if node.returns is not None else []),
        ]:
            self.visit(expression)
        table = self._child(
            node.name,
            node.lineno,
            "function",
            {arg.arg for arg in self._arguments(node.args)},
        )
        self._enter(table, "function", node.body)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_TypeAlias(self, node):
        raise ValueError("Lazy type-alias scope is not selected")

    def visit_ClassDef(self, node):
        if node.type_params:
            raise ValueError("Generic annotation scope is not selected")
        for expression in [
            *node.decorator_list,
            *node.bases,
            *[keyword.value for keyword in node.keywords],
        ]:
            self.visit(expression)
        self._enter(self._child(node.name, node.lineno, "class"), "class", node.body)

    def visit_Lambda(self, node):
        for expression in [
            *node.args.defaults,
            *[value for value in node.args.kw_defaults if value is not None],
        ]:
            self.visit(expression)
        table = self._child(
            "lambda",
            node.lineno,
            "function",
            {arg.arg for arg in self._arguments(node.args)},
        )
        self._enter(table, "function", [node.body])

    def _comprehension(self, node, name, values):
        # Python3.12 inlines list/set/dict comprehensions: symtable exposes
        # no child for them. AST targets still have their own lexical scope.
        self.visit(node.generators[0].iter)
        shadows = {
            target.id
            for generator in node.generators
            for target in ast.walk(generator.target)
            if isinstance(target, ast.Name)
        }
        table = self._child(name, node.lineno, "function", optional=True)
        inside = [*node.generators[0].ifs]
        for generator in node.generators[1:]:
            inside.extend([generator.iter, *generator.ifs])
        self._enter(table, "comprehension", [*inside, *values], shadows)

    def visit_ListComp(self, node):
        self._comprehension(node, "listcomp", [node.elt])

    def visit_SetComp(self, node):
        self._comprehension(node, "setcomp", [node.elt])

    def visit_DictComp(self, node):
        self._comprehension(node, "dictcomp", [node.key, node.value])

    def visit_GeneratorExp(self, node):
        self._comprehension(node, "genexpr", [node.elt])

    def visit_NamedExpr(self, node):
        if self.scope.kind == "comprehension":
            outer = self.scope.parent
            while outer.kind == "comprehension":
                outer = outer.parent
            for target in ast.walk(node.target):
                if isinstance(target, ast.Name):
                    owner = self._owner(outer, target.id)
                    if owner is not None:
                        self.spoiled.add((id(owner), target.id))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                self.scope.wildcard = True
            else:
                name = alias.asname or alias.name
                selected = (
                    node.level == 0
                    and node.module == "unittest.mock"
                    and alias.name == "patch"
                )
                self.scope.imports.setdefault(name, []).append(selected)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.scope.imports.setdefault(name, []).append(False)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "dict":
            self.calls.append((self.scope, node))
        self.generic_visit(node)

    def _enclosing(self, scope, name):
        while scope is not None:
            if scope.kind == "comprehension":
                if name in scope.shadows:
                    return scope
            elif scope.kind != "class":
                try:
                    symbol = scope.table.lookup(name)
                except KeyError:
                    symbol = None
                if symbol is not None:
                    if symbol.is_global():
                        return self.root
                    if symbol.is_local():
                        return scope
            scope = scope.parent
        return None

    def _owner(self, scope, name):
        if scope.kind == "comprehension":
            if name in scope.shadows:
                return scope
            return self._owner(scope.parent, name)
        try:
            symbol = scope.table.lookup(name)
        except KeyError:
            return None
        if scope is self.root or symbol.is_local():
            return scope
        if symbol.is_global():
            return self.root
        if symbol.is_free() or symbol.is_nonlocal():
            return self._enclosing(scope.parent, name)
        return None

    def _foreign_writes(self):
        for scope in self.scopes:
            if scope.kind == "comprehension":
                continue
            for symbol in scope.table.get_symbols():
                if (symbol.is_global() or symbol.is_nonlocal()) and (
                    symbol.is_assigned() or symbol.is_imported()
                ):
                    owner = self._owner(scope, symbol.get_name())
                    if owner is not None and owner is not scope:
                        self.spoiled.add((id(owner), symbol.get_name()))

    def violations(self):
        self._foreign_writes()
        lines = []
        for scope, node in self.calls:
            if not isinstance(node.func.value, ast.Name):
                lines.append(node.lineno)
                continue
            name = node.func.value.id
            owner = self._owner(scope, name)
            if owner is None or owner.table is None:
                lines.append(node.lineno)
                continue
            symbol = owner.table.lookup(name)
            trusted = (
                owner.imports.get(name) == [True]
                and not owner.wildcard
                and not symbol.is_assigned()
                and not symbol.is_parameter()
                and (id(owner), name) not in self.spoiled
            )
            if not trusted:
                lines.append(node.lineno)
        return sorted(lines)


def deprecated_dict_calls(source: str) -> list[int]:
    """Exempt known stdlib patch aliases per lexical scope, never by spelling.

    Globals/nonlocals and comprehension assignment expressions can invalidate
    their actual defining alias. Ambiguous/unsupported scopes fail closed.
    Dynamic namespace mutation and runtime types are not proved by this gate.
    """
    tree = ast.parse(source)
    all_calls = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "dict"
    ]
    if not all_calls:
        return []
    try:
        visitor = _Calls(symtable.symtable(source, "<deprecation-contract>", "exec"))
        visitor.visit(tree)
        return visitor.violations()
    except (SyntaxError, ValueError, KeyError):
        return sorted(all_calls)
