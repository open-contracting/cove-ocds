import json
from decimal import Decimal

from libcoveocds.schema import SchemaOCDS


def get_schema(lib_cove_ocds_config, package_data):
    return SchemaOCDS(
        select_version=lib_cove_ocds_config.config["schema_version"],
        package_data=package_data,
        lib_cove_ocds_config=lib_cove_ocds_config,
        record_pkg="records" in package_data,
    )


def default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return json.JSONEncoder().default(obj)
