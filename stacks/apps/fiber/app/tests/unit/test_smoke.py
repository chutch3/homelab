def test_package_imports() -> None:
    import fiber

    assert fiber is not None


def test_version_is_defined() -> None:
    import fiber
    assert hasattr(fiber, "__version__")
    assert isinstance(fiber.__version__, str)
    assert fiber.__version__ == "0.1.0"


def test_containers_uses_package_version() -> None:
    """containers.py must derive fiber_version from fiber.__version__, not a hardcoded literal."""
    import ast
    import pathlib
    src = pathlib.Path(__file__).parent.parent.parent / "fiber" / "container.py"
    text = src.read_text()
    tree = ast.parse(text)
    # Accept: `import fiber` with `fiber.__version__` usage, or `from fiber import __version__`
    imports_fiber = any(
        isinstance(node, ast.Import) and any(a.name == "fiber" for a in node.names)
        for node in ast.walk(tree)
    )
    imports_version_from = any(
        isinstance(node, ast.ImportFrom) and node.module in ("fiber", "fiber.__init__")
        and any(a.name == "__version__" for a in node.names)
        for node in ast.walk(tree)
    )
    uses_version = "fiber.__version__" in text or "__version__" in text
    assert (imports_fiber or imports_version_from) and uses_version, (
        "containers.py must import fiber and use fiber.__version__"
    )
