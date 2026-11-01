"""Migration and factory step definitions for BDD tests."""

from pathlib import Path
from typing import Any

from pytest_bdd import given, then, when
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_shared.models import Dataset, DataValue

# ==============================================================================
# Given Steps - Migration Setup
# ==============================================================================


@given("the project has an alembic configuration")
def project_has_alembic_config(scenario_context: dict[str, Any], project_root: Path) -> None:
    """Verify alembic configuration exists."""
    scenario_context["project_root"] = project_root


@given("the project has alembic migrations")
def project_has_migrations(scenario_context: dict[str, Any], alembic_dir: Path) -> None:
    """Verify alembic migrations exist."""
    scenario_context["alembic_dir"] = alembic_dir


@given("the factory-boy library is available")
def factory_boy_available(scenario_context: dict[str, Any]) -> None:
    """Verify factory-boy is importable."""
    try:
        import factory  # noqa: F401

        scenario_context["factory_available"] = True
    except ImportError:
        scenario_context["factory_available"] = False


@given("the SQLModel metadata is initialized")
def sqlmodel_metadata_initialized(scenario_context: dict[str, Any]) -> None:
    """Initialize SQLModel metadata by importing models."""
    from ecox_shared.models import (  # noqa: F401
        Dataset,
        DataValue,
        FetchLog,
    )

    scenario_context["metadata_initialized"] = True


@given("an in-memory SQLite database")
def in_memory_sqlite(scenario_context: dict[str, Any]) -> None:
    """Prepare an in-memory SQLite database."""
    scenario_context["use_memory_db"] = True


# ==============================================================================
# When Steps - Migration Actions
# ==============================================================================


@when("I create a dataset using the factory")
def create_dataset_with_factory(scenario_context: dict[str, Any]) -> None:
    """Create a dataset using factory pattern."""
    import factory
    from factory import Faker

    class DatasetFactory(factory.Factory):
        class Meta:
            model = Dataset

        code = factory.Sequence(lambda n: f"DATASET_{n}")
        source = "test"
        name = Faker("sentence", nb_words=3)
        description = Faker("paragraph")

    dataset = DatasetFactory()
    scenario_context["dataset"] = dataset


@when("I create data values using the factory")
def create_data_values_with_factory(scenario_context: dict[str, Any]) -> None:
    """Create data values using factory pattern."""
    import factory
    from factory import Faker

    class DataValueFactory(factory.Factory):
        class Meta:
            model = DataValue

        dataset_id = 1
        geo = factory.Sequence(lambda n: f"GEO_{n}")
        time_period = Faker("date", pattern="%Y")
        indicator = "GDP"
        value = Faker("pyfloat", min_value=100.0, max_value=10000.0)

    values = [DataValueFactory() for _ in range(3)]
    scenario_context["data_values"] = values


@when("I create all tables")
async def create_all_tables(scenario_context: dict[str, Any]) -> None:
    """Create all tables in in-memory database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    scenario_context["test_engine"] = engine


# ==============================================================================
# Then Steps - Migration Assertions
# ==============================================================================


@then("the alembic env.py file should exist")
def alembic_env_exists(scenario_context: dict[str, Any], alembic_dir: Path) -> None:
    """Assert alembic env.py exists."""
    env_file = alembic_dir / "env.py"
    assert env_file.exists(), f"alembic/env.py not found at {env_file}"


@then("the alembic versions directory should exist")
def alembic_versions_exists(scenario_context: dict[str, Any], alembic_dir: Path) -> None:
    """Assert alembic versions directory exists."""
    versions_dir = alembic_dir / "versions"
    assert versions_dir.exists(), f"alembic/versions/ not found at {versions_dir}"


@then("an initial schema migration should exist")
def initial_migration_exists(scenario_context: dict[str, Any], alembic_dir: Path) -> None:
    """Assert initial schema migration exists."""
    versions_dir = alembic_dir / "versions"
    migration_files = list(versions_dir.glob("*initial*.py"))
    assert len(migration_files) > 0, "No initial schema migration found"
    scenario_context["initial_migration"] = migration_files[0]


@then("the migration should create core tables")
def migration_creates_tables(scenario_context: dict[str, Any]) -> None:
    """Assert the migration creates core tables."""
    migration_file = scenario_context.get("initial_migration")
    assert migration_file is not None, "Initial migration not found"

    content = migration_file.read_text()
    # Check for table creation operations
    assert "create_table" in content or "op.create_table" in content, (
        "Migration doesn't create tables"
    )


@then("the dataset should have required fields")
def dataset_has_required_fields(scenario_context: dict[str, Any]) -> None:
    """Assert the dataset has required fields."""
    dataset = scenario_context.get("dataset")
    assert dataset is not None, "Dataset not created"
    assert hasattr(dataset, "code"), "Dataset missing 'code' field"
    assert hasattr(dataset, "source"), "Dataset missing 'source' field"
    assert hasattr(dataset, "name"), "Dataset missing 'name' field"


@then("the dataset code should be unique")
def dataset_code_unique(scenario_context: dict[str, Any]) -> None:
    """Assert dataset codes from factory are unique."""
    import factory

    class DatasetFactory(factory.Factory):
        class Meta:
            model = Dataset

        code = factory.Sequence(lambda n: f"DATASET_{n}")
        source = "test"

    codes = [DatasetFactory().code for _ in range(3)]
    assert len(codes) == len(set(codes)), "Factory doesn't generate unique codes"


@then("the data values should have numeric values")
def data_values_have_numbers(scenario_context: dict[str, Any]) -> None:
    """Assert data values have numeric values."""
    values = scenario_context.get("data_values", [])
    assert len(values) > 0, "No data values created"
    for v in values:
        assert v.value is not None, "Data value missing numeric value"
        assert isinstance(v.value, (int, float)), "Value is not numeric"


@then("the data values should have time periods")
def data_values_have_time_periods(scenario_context: dict[str, Any]) -> None:
    """Assert data values have time periods."""
    values = scenario_context.get("data_values", [])
    assert len(values) > 0, "No data values created"
    for v in values:
        assert v.time_period is not None, "Data value missing time period"


@then("the metadata should contain the dataset table")
def metadata_has_dataset_table(scenario_context: dict[str, Any]) -> None:
    """Assert SQLModel metadata has dataset table."""
    tables = SQLModel.metadata.tables
    assert "dataset" in tables, f"'dataset' table not in metadata. Tables: {list(tables.keys())}"


@then("the metadata should contain the datavalue table")
def metadata_has_datavalue_table(scenario_context: dict[str, Any]) -> None:
    """Assert SQLModel metadata has datavalue table."""
    tables = SQLModel.metadata.tables
    assert "datavalue" in tables, (
        f"'datavalue' table not in metadata. Tables: {list(tables.keys())}"
    )


@then("the metadata should contain the fetchlog table")
def metadata_has_fetchlog_table(scenario_context: dict[str, Any]) -> None:
    """Assert SQLModel metadata has fetchlog table."""
    tables = SQLModel.metadata.tables
    assert "fetchlog" in tables, f"'fetchlog' table not in metadata. Tables: {list(tables.keys())}"


@then("the tables should be queryable")
async def tables_are_queryable(scenario_context: dict[str, Any]) -> None:
    """Assert tables can be queried."""
    engine = scenario_context.get("test_engine")
    assert engine is not None, "Test engine not created"

    async with AsyncSession(engine, expire_on_commit=False) as session:
        from sqlmodel import select

        # Try to query the dataset table
        result = await session.execute(select(Dataset))
        datasets = result.scalars().all()
        assert isinstance(datasets, list), "Failed to query dataset table"

    await engine.dispose()
