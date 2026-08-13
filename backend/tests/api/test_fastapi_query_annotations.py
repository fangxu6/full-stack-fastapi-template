import ast
from pathlib import Path

import pytest

TARGET_ROUTER_PATHS = (
    "app/api/routes/items.py",
    "app/modules/inventory/correction_router.py",
    "app/modules/inventory/router.py",
    "app/modules/scheduler/router.py",
)


def _is_query_call(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Query"
    )


def _contains_query_call(node: ast.expr | None) -> bool:
    return node is not None and any(_is_query_call(child) for child in ast.walk(node))


def _is_annotated(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "Annotated"
    )


@pytest.mark.parametrize("relative_path", TARGET_ROUTER_PATHS)
def test_route_query_parameters_use_annotated_metadata(relative_path: str) -> None:
    source_path = Path(__file__).parents[2] / relative_path
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

    violations: list[str] = []
    for function in ast.walk(tree):
        if not isinstance(function, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        positional_args = [*function.args.posonlyargs, *function.args.args]
        positional_defaults = [
            *([None] * (len(positional_args) - len(function.args.defaults))),
            *function.args.defaults,
        ]
        for argument, default in [
            *zip(positional_args, positional_defaults, strict=True),
            *zip(function.args.kwonlyargs, function.args.kw_defaults, strict=True),
        ]:
            if _is_query_call(default):
                violations.append(
                    f"{function.name}.{argument.arg} uses Query(...) as a default"
                )
            if _contains_query_call(argument.annotation) and not _is_annotated(
                argument.annotation
            ):
                violations.append(
                    f"{function.name}.{argument.arg} has Query(...) outside Annotated[...]"
                )

    assert not violations, "\n".join(violations)
