import json
from decimal import Decimal

from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext as _
from libcove.lib.exceptions import CoveInputDataError
from libcoveocds.schema import SchemaOCDS


def read_json(path):
    # Read as text, because the json module can read binary UTF-16 and UTF-32.
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except UnicodeError as err:
            raise CoveInputDataError(
                context={
                    "sub_title": _("Sorry, we can't process that data"),
                    "error": format(err),
                    "link": "index",
                    "link_text": _("Try Again"),
                    "msg": format_html(
                        _(
                            "The file that you uploaded doesn't appear to be well formed JSON. OCDS JSON follows the "
                            "I-JSON format, which requires UTF-8 encoding. Ensure that your file uses UTF-8 encoding, "
                            "then try uploading again.\n\n"
                            '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> <strong>'
                            "Error message:</strong> {}"
                        ),
                        err,
                    ),
                }
            ) from None
        except ValueError as err:
            raise CoveInputDataError(
                context={
                    "sub_title": _("Sorry, we can't process that data"),
                    "error": format(err),
                    "link": "index",
                    "link_text": _("Try Again"),
                    "msg": format_html(
                        _(
                            "We think you tried to upload a JSON file, but it is not well formed JSON.\n\n"
                            '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> <strong>'
                            "Error message:</strong> {}"
                        ),
                        err,
                    ),
                }
            ) from None

    if not isinstance(data, dict):
        raise CoveInputDataError(
            context={
                "sub_title": _("Sorry, we can't process that data"),
                "link": "index",
                "link_text": _("Try Again"),
                "msg": _("OCDS JSON should have an object as the top level, the JSON you supplied does not."),
            }
        )

    return data


def get_schema(lib_cove_ocds_config, package_data):
    schema_ocds = SchemaOCDS(
        select_version=lib_cove_ocds_config.config["schema_version"],
        package_data=package_data,
        lib_cove_ocds_config=lib_cove_ocds_config,
        record_pkg="records" in package_data,
    )

    if schema_ocds.missing_package:
        raise CoveInputDataError(
            context={
                "sub_title": _("Missing OCDS package"),
                "error": _("Missing OCDS package"),
                "link": "index",
                "link_text": _("Try Again"),
                "msg": mark_safe(
                    _(
                        "We could not detect a package structure at the top-level of your data. OCDS releases and "
                        'records should be published within a <a href="https://standard.open-contracting.org/latest/en'
                        '/schema/release_package/">release package </a> or <a href="https://standard.open-contracting.'
                        'org/latest/en/schema/record_package/"> record package</a> to provide important meta-data. '
                        'For more information, please refer to the <a href="https://standard.open-contracting.org/'
                        'latest/en/primer/releases_and_records/"> Releases and Records section </a> in the OCDS '
                        "documentation.\n\n"
                        '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> <strong>'
                        "Error message:</strong> <em>Missing OCDS package</em>"
                    )
                ),
            }
        )

    return schema_ocds


def default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return json.JSONEncoder().default(obj)
