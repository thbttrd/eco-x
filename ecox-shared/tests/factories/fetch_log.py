"""Factory for FetchLog model."""

from datetime import datetime

import factory

from ecox_shared.models import FetchLog


class FetchLogFactory(factory.Factory):
    """Factory for FetchLog model."""

    class Meta:
        """Factory configuration."""

        model = FetchLog

    id = factory.Sequence(lambda n: n + 1)
    dataset_code = factory.Sequence(lambda n: f"DATASET_{n}")
    source = factory.Faker("random_element", elements=["eurostat", "fred", "ons"])
    status = factory.Faker("random_element", elements=["success", "error", "partial"])
    records_fetched = factory.Faker("random_int", min=0, max=10000)
    error_message = None
    filters = None
    started_at = factory.LazyFunction(datetime.now)
    completed_at = factory.LazyFunction(datetime.now)
    duration_seconds = factory.Faker("pyfloat", min_value=0.1, max_value=60.0)

    class Params:
        """Factory parameters for different states."""

        failed = factory.Trait(
            status="error",
            error_message=factory.Faker("sentence"),
            records_fetched=0,
        )
