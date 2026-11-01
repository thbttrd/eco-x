"""BDD tests for Epic 13: Migrations & Factories.

This module binds the feature file to step definitions.
"""

from pytest_bdd import scenarios

# Import step definitions (wildcard imports needed for pytest-bdd step discovery)
from tests.step_defs.migration_steps import *  # noqa: F401, F403

# Bind all scenarios from the feature file
scenarios("../features/epic13_migrations.feature")
