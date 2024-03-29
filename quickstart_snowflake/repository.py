from dagster import (
    ScheduleDefinition,
    define_asset_job,
    load_assets_from_package_module,
    repository,
    with_resources,
)
from dagster_snowflake import build_snowflake_io_manager
from dagster_snowflake_pandas import SnowflakePandasTypeHandler

from quickstart_snowflake import assets

daily_refresh_schedule = ScheduleDefinition(
    job=define_asset_job(name="all_assets_job"), cron_schedule="0 0 * * *"
)


@repository
def quickstart_snowflake():
    return [
        *with_resources(
            load_assets_from_package_module(assets),
            resource_defs={
                "io_manager": build_snowflake_io_manager([SnowflakePandasTypeHandler()]).configured(
                    # Read about using environment variables and secrets in Dagster:
                    # https://docs.dagster.io/guides/dagster/using-environment-variables-and-secrets
                    {
                        "account": "rb83340.europe-west4.gcp",
                        "user": "ranjuramesh",
                        "password": "NpI9UcA8Cn#9",
                        "warehouse": "compute_wh",
                        "database": "rawdata_db",
                        "schema": "testing",
                    }
                ),
            },
        ),
        daily_refresh_schedule,
    ]
