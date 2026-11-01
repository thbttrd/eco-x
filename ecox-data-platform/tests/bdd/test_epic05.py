"""BDD tests for Epic 5: Economic News Aggregation.

This module binds the feature file to step definitions for testing
the news aggregation API functionality.
"""

from pytest_bdd import scenarios

# Import step definitions (wildcard imports needed for pytest-bdd step discovery)
from tests.step_defs.api_steps import *  # noqa: F401, F403
from tests.step_defs.common_steps import *  # noqa: F401, F403
from tests.step_defs.news_steps import *  # noqa: F401, F403

# Bind all scenarios from the feature file
scenarios("../features/epic05_news_aggregation.feature")
