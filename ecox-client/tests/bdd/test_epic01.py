"""BDD tests for Epic 1: Data Source Browsing (UI).

This module binds the feature file to step definitions.
"""

from pytest_bdd import scenarios

# Import step definitions (wildcard imports needed for pytest-bdd step discovery)
from tests.step_defs.common_steps import *  # noqa: F401, F403
from tests.step_defs.ui_steps import *  # noqa: F401, F403

# Bind all scenarios from the feature file
scenarios("../features/epic01_data_source_browsing.feature")
