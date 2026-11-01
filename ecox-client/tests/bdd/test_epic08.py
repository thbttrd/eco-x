"""BDD tests for Epic 8: Application Information.

This module binds the feature file to step definitions.
"""

from pytest_bdd import scenarios

# Import step definitions (wildcard imports needed for pytest-bdd step discovery)
from tests.step_defs.common_steps import *  # noqa: F401, F403
from tests.step_defs.i18n_steps import *  # noqa: F401, F403
from tests.step_defs.version_steps import *  # noqa: F401, F403

# Bind all scenarios from the feature file
scenarios("../features/epic08_application_info.feature")
