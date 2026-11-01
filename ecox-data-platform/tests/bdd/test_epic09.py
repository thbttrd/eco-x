"""BDD tests for Epic 9: Data Storage & History.

This module binds the feature file to step definitions.
"""

from pytest_bdd import scenarios

# Import step definitions (wildcard imports needed for pytest-bdd step discovery)
from tests.step_defs.api_steps import *  # noqa: F401, F403
from tests.step_defs.common_steps import *  # noqa: F401, F403
from tests.step_defs.dataset_steps import *  # noqa: F401, F403
from tests.step_defs.source_steps import *  # noqa: F401, F403
from tests.step_defs.storage_steps import *  # noqa: F401, F403

# Bind all scenarios from the feature file
scenarios("../features/epic09_storage_history.feature")
