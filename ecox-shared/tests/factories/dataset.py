"""Factories for Dataset-related models."""

from datetime import datetime

import factory

from ecox_shared.models import Dataset, DatasetMetadata, DataValue


class DatasetFactory(factory.Factory):
    """Factory for Dataset model."""

    class Meta:
        """Factory configuration."""

        model = Dataset

    id = factory.Sequence(lambda n: n + 1)
    code = factory.Sequence(lambda n: f"DATASET_{n}")
    name = factory.Faker("sentence", nb_words=3)
    source = factory.Faker("random_element", elements=["eurostat", "fred", "ons"])
    description = factory.Faker("paragraph")
    last_fetched = factory.LazyFunction(datetime.now)
    source_last_update = None
    extra_metadata = None


class DataValueFactory(factory.Factory):
    """Factory for DataValue model."""

    class Meta:
        """Factory configuration."""

        model = DataValue

    id = factory.Sequence(lambda n: n + 1)
    dataset_id = factory.Sequence(lambda n: n + 1)
    geo = factory.Faker("random_element", elements=["EU27_2020", "FR", "DE", "IT", "ES", "US"])
    time_period = factory.Faker("random_element", elements=["2020", "2021", "2022", "2023"])
    indicator = factory.Faker("random_element", elements=["B1GQ", "HICP", "GDP", "CPI"])
    value = factory.Faker("pyfloat", min_value=1000, max_value=1000000)
    unit = factory.Faker("random_element", elements=["EUR", "MIO_EUR", "PC", "USD"])
    flags = factory.Faker("random_element", elements=[None, "e", "p", "b"])


class DatasetMetadataFactory(factory.Factory):
    """Factory for DatasetMetadata model."""

    class Meta:
        """Factory configuration."""

        model = DatasetMetadata

    id = factory.Sequence(lambda n: n + 1)
    dataset_id = factory.Sequence(lambda n: n + 1)
    key = factory.Faker("random_element", elements=["dimension", "attribute", "label"])
    value = factory.Faker("json")
    created_at = factory.LazyFunction(datetime.now)
