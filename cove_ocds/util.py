import json
import re
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


def get_schema(request, context, supplied_data, lib_cove_ocds_config, package_data):
    request_version = request.POST.get("version")
    data_version = package_data.get("version")

    schema_ocds = SchemaOCDS(
        # This will be the user-requested version, the previously-determined version, or None.
        select_version=request_version or supplied_data.schema_version,
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

    if schema_ocds.invalid_version_argument:
        raise CoveInputDataError(
            context={
                "sub_title": _("Unrecognised version of the schema"),
                "error": _("%(version)s is not a known schema version") % {"version": request_version},
                "link": "index",
                "link_text": _("Try Again"),
                "msg": format_html(
                    _(
                        "We think you tried to run your data against an unrecognised version of the schema.\n\n"
                        '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> <strong>'
                        "Error message:</strong> <em>{}</em> is not a recognised choice for the schema version",
                    ),
                    request_version,
                ),
            }
        )

    if schema_ocds.invalid_version_data:
        if isinstance(data_version, str) and re.compile(r"^\d+\.\d+\.\d+$").match(data_version):
            raise CoveInputDataError(
                context={
                    "sub_title": _("Version format does not comply with the schema"),
                    "error": _("%(version)s is not a known schema version") % {"version": data_version},
                    "link": "index",
                    "link_text": _("Try Again"),
                    "msg": format_html(
                        _(
                            'The value for the <em>"version"</em> field in your data follows the <em>major.minor.'
                            "patch</em> pattern but according to the schema the patch digit shouldn't be included "
                            '(e.g. <em>"1.1.0"</em> should appear as <em>"1.1"</em> in your data as this tool '
                            "always uses the latest patch release for a major.minor version).\n\n"
                            "Please get rid of the patch digit and try again.\n\n"
                            '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> '
                            "<strong>Error message:</strong> <em>{}</em> format does not comply with the schema",
                        ),
                        json.dumps(data_version),
                    ),
                }
            )

        if not isinstance(data_version, str):
            data_version = _("%(version)s (not a string)") % {"version": json.dumps(data_version)}
        context["unrecognized_version_data"] = data_version

    # Cache the extended schema.
    if schema_ocds.extensions:
        schema_ocds.create_extended_schema_file(supplied_data.upload_dir(), supplied_data.upload_url())

    # If the schema is not extended, extended_schema_file is None.
    schema_url = schema_ocds.extended_schema_file or schema_ocds.schema_url

    # Regenerate alternative formats if the user requests a different version.
    replace = bool(supplied_data.schema_version) and schema_ocds.version != supplied_data.schema_version

    return schema_ocds, schema_url, replace


def default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return json.JSONEncoder().default(obj)
