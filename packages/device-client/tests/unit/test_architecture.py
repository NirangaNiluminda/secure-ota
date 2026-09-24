"""Executable enforcement of the dependency rule.

Clean architecture that is only described in a README rots within a week. This
test parses every module's imports and fails the build the moment a dependency
points outward — so the layering is a property the code *has*, not a claim the
report *makes*.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "secure_ota_device"

#: What each layer is allowed to import from, within this package.
ALLOWED: dict[str, set[str]] = {
    "domain": set(),
    "application": {"domain"},
    "infrastructure": {"domain", "application"},
    "composition": {"domain", "application", "infrastructure"},
    "cli": {"domain", "application", "composition"},
}

#: Third-party packages no layer below infrastructure may touch.
FORBIDDEN_THIRD_PARTY = {"web3", "eth_account", "requests", "httpx"}


def _python_files() -> list[Path]:
    return sorted(path for path in SRC.rglob("*.py") if path.name != "__init__.py")


def _layer_of(path: Path) -> str:
    return path.relative_to(SRC).parts[0]


def _module_name(path: Path) -> str:
    parts = path.relative_to(SRC).with_suffix("").parts
    return ".".join(("secure_ota_device", *parts))


def _imported_modules(path: Path) -> list[str]:
    """Absolute dotted names for every import in the file, relatives resolved."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package_parts = _module_name(path).split(".")[:-1]
    found: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module:
                    found.append(node.module)
            else:
                # level=1 is the current package, level=2 its parent, and so on.
                base = package_parts[: len(package_parts) - (node.level - 1)]
                found.append(".".join([*base, node.module] if node.module else base))

    return found


@pytest.mark.parametrize("path", _python_files(), ids=_module_name)
def test_layer_only_imports_inward(path: Path) -> None:
    layer = _layer_of(path)
    if layer not in ALLOWED:
        pytest.skip(f"{layer} is not a layered package")

    for imported in _imported_modules(path):
        if not imported.startswith("secure_ota_device."):
            continue
        target_layer = imported.split(".")[1]
        if target_layer == layer:
            continue
        assert target_layer in ALLOWED[layer], (
            f"{_module_name(path)} ({layer}) imports {imported} ({target_layer}); "
            f"{layer} may only depend on {sorted(ALLOWED[layer]) or 'nothing'}"
        )


@pytest.mark.parametrize("path", _python_files(), ids=_module_name)
def test_inner_layers_have_no_third_party_imports(path: Path) -> None:
    """Only infrastructure may know a third-party library exists."""
    if _layer_of(path) not in {"domain", "application"}:
        pytest.skip("infrastructure and above may use third-party packages")

    for imported in _imported_modules(path):
        root = imported.split(".")[0]
        assert root not in FORBIDDEN_THIRD_PARTY, (
            f"{_module_name(path)} imports {imported}; the domain and application "
            "layers must stay free of infrastructure concerns"
        )


def test_domain_is_completely_self_contained() -> None:
    """The strongest form of the rule, stated once on its own.

    The domain must be importable with nothing but the standard library. If this
    ever fails, the business rules have been entangled with a framework.
    """
    for path in _python_files():
        if _layer_of(path) != "domain":
            continue
        for imported in _imported_modules(path):
            assert not imported.startswith("secure_ota_device.") or imported.startswith(
                "secure_ota_device.domain"
            ), f"{_module_name(path)} reaches outside the domain via {imported}"
