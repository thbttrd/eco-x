"""BDD tests for Epic 4: Automatic Data Refresh.

This module binds the feature file to step definitions.
"""

from pytest_bdd import scenarios

# Import step definitions (wildcard imports needed for pytest-bdd step discovery)
from tests.step_defs.common_steps import *  # noqa: F401, F403
from tests.step_defs.dataset_steps import *  # noqa: F401, F403
from tests.step_defs.refresh_steps import *  # noqa: F401, F403

# Bind all scenarios from the feature file
scenarios("../features/epic04_auto_refresh.feature")
