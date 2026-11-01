"""Version step definitions for ecox-client BDD tests."""

import tomllib
from pathlib import Path
from typing import Any

from pytest_bdd import then


def get_project_version() -> str:
    """Read version from root pyproject.toml."""
    # Navigate from step_defs -> tests -> ecox-client -> eco-x (root)
    root_dir = Path(__file__).parent.parent.parent.parent
    pyproject_path = root_dir / "pyproject.toml"

    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    return data["project"]["version"]


@then("the response should contain the current version")
def response_contains_current_version(scenario_context: dict[str, Any]) -> None:
    """Assert response contains the current version from pyproject.toml."""
    response = scenario_context.get("response")
    assert response is not None, "No response in context"

    version = get_project_version()
    version_string = f"v{version}"

    assert version_string in response.text, (
        f"Expected version '{version_string}' in response. "
        f"Response excerpt: {response.text[:500]}..."
    )
