"""Factories for Source-related models."""

from datetime import datetime

import factory

from ecox_shared.models import SourceMetadata


class SourceMetadataFactory(factory.Factory):
    """Factory for SourceMetadata model."""

    class Meta:
        """Factory configuration."""

        model = SourceMetadata

    id = factory.Sequence(lambda n: n + 1)
    source = factory.Sequence(lambda n: f"source_{n}")
    total_datasets = factory.Faker("random_int", min=10, max=1000)
    cached_toc = None
    last_updated = factory.LazyFunction(datetime.now)
