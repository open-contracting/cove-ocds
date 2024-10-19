import json
import logging
import re
import warnings
from collections import defaultdict

from cove.views import cove_web_input_error, explore_data_context
from django.conf import settings
from django.shortcuts import render
from django.utils import translation
from django.utils.html import format_html
from django.utils.translation import gettext as _
from flattentool.exceptions import FlattenToolValueError, FlattenToolWarning
from libcove.lib.common import get_spreadsheet_meta_data
from libcove.lib.converters import convert_spreadsheet
from libcove.lib.exceptions import CoveInputDataError
from libcoveocds.common_checks import common_checks_ocds
from libcoveocds.config import LibCoveOCDSConfig
from libcoveocds.schema import SchemaOCDS

from cove_ocds import util

logger = logging.getLogger(__name__)
MAXIMUM_RELEASES_OR_RECORDS = 100


@cove_web_input_error
def explore_ocds(request, pk):
    context, supplied_data, error = explore_data_context(request, pk)
    if error:
        return error

    # Initialize the CoVE configuration.

    lib_cove_ocds_config = LibCoveOCDSConfig(settings.COVE_CONFIG)
    lib_cove_ocds_config.config["current_language"] = translation.get_language()
    # Format the urls with `{lang}` contained in a schema_version_choices.
    lib_cove_ocds_config.config["schema_version_choices"] = {
        version: (display, url.format(lang=request.LANGUAGE_CODE), tag)
        for version, (display, url, tag) in lib_cove_ocds_config.config["schema_version_choices"].items()
    }

    # Read the supplied data.

    if context["file_type"] == "json":
        package_data = util.read_json(supplied_data.original_file.path)

        schema_ocds = util.get_schema(lib_cove_ocds_config, package_data)
    else:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FlattenToolWarning)

            meta_data = get_spreadsheet_meta_data(
                supplied_data.upload_dir(),
                supplied_data.original_file.path,
                SchemaOCDS(select_version="1.1", lib_cove_ocds_config=lib_cove_ocds_config).pkg_schema_url,
                context["file_type"],
            )

        meta_data.setdefault("version", "1.1")
        # Make "missing_package" pass.
        meta_data["releases"] = {}

        schema_ocds = util.get_schema(lib_cove_ocds_config, meta_data)

        # Used in conversions.
        if schema_ocds.extensions:
            schema_ocds.create_extended_schema_file(supplied_data.upload_dir(), supplied_data.upload_url())

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FlattenToolWarning)

            try:
                # Sets:
                # - conversion_warning_messages: str (JSON)
                # - converted_file_size: int (bytes)
                # - conversion = "unflatten"
                # - converted_path: str
                # - converted_url: str
                # - csv_encoding = "utf-8-sig" | "cp1252" | "latin_1"
                context.update(
                    # __wrapped__ is missing when the function is patched by tests.
                    getattr(convert_spreadsheet, "__wrapped__", convert_spreadsheet)(
                        supplied_data.upload_dir(),
                        upload_url=supplied_data.upload_url(),
                        file_name=supplied_data.original_file.path,
                        file_type=context["file_type"],
                        lib_cove_config=lib_cove_ocds_config,
                        # If the schema is not extended, extended_schema_file is None.
                        schema_url=schema_ocds.extended_schema_file or schema_ocds.schema_url,
                        pkg_schema_url=schema_ocds.pkg_schema_url,
                    )
                )
            except FlattenToolValueError as err:
                raise CoveInputDataError(
                    context={
                        "sub_title": _("Sorry, we can't process that data"),
                        "link": "index",
                        "link_text": _("Try Again"),
                        "error": format(err),
                        "msg": format_html(
                            _(
                                "The table isn't structured correctly. For example, a JSON Pointer (<code>tender"
                                "</code>) can't be both a value (<code>tender</code>), a path to an object (<code>"
                                "tender/id</code>) and a path to an array (<code>tender/0/title</code>).\n\n"
                                '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> '
                                "<strong>Error message:</strong> {}",
                            ),
                            err,
                        ),
                    }
                ) from None
            except Exception as err:
                logger.exception("", extra={"request": request})
                raise CoveInputDataError(wrapped_err=err) from None

        with open(context["converted_path"], "rb") as f:
            package_data = json.load(f)

    # Perform the validation.

    context = common_checks_ocds(context, supplied_data.upload_dir(), package_data, schema_ocds)

    # Set by SchemaOCDS.get_schema_obj(deref=True), which, at the latest, is called indirectly by common_checks_ocds().
    if schema_ocds.json_deref_error:
        raise CoveInputDataError(
            context={
                "sub_title": _("JSON reference error"),
                "link": "index",
                "link_text": _("Try Again"),
                "msg": _(
                    format_html(
                        "We have detected a JSON reference error in the schema. This <em> may be "
                        "</em> due to some extension trying to resolve non-existing references. "
                        '\n\n<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true">'
                        "</span> <strong>Error message:</strong> <em>{}</em>",
                        schema_ocds.json_deref_error,
                    )
                ),
                "error": _("%(error)s") % {"error": schema_ocds.json_deref_error},
            }
        )

    # Update the row in the database.

    # The data_schema_version column is NOT NULL.
    supplied_data.data_schema_version = package_data.get("version") or ""
    supplied_data.schema_version = schema_ocds.version
    supplied_data.rendered = True  # not relevant to CoVE OCDS
    supplied_data.save()

    # Finalize the context.

    validation_errors_grouped = defaultdict(list)
    for error_json, values in context["validation_errors"]:
        match json.loads(error_json)["message_type"]:
            case "required":
                key = "required"
            case "format" | "pattern" | "number" | "string" | "date-time" | "uri" | "object" | "integer" | "array":
                key = "format"
            case _:
                key = "other"
        validation_errors_grouped[key].append((error_json, values))

    context["data_schema_version"] = json.dumps(package_data.get("version"))
    context["validation_errors_grouped"] = validation_errors_grouped

    for key in ("additional_closed_codelist_values", "additional_open_codelist_values"):
        for additional_codelist_values in context[key].values():
            if additional_codelist_values["codelist_url"].startswith(schema_ocds.codelists):
                additional_codelist_values["codelist_url"] = (
                    f"https://standard.open-contracting.org/{supplied_data.data_schema_version}/en/schema/codelists/#"
                    + re.sub(r"([A-Z])", r"-\1", additional_codelist_values["codelist"].split(".")[0]).lower()
                )

    if "version" in package_data:
        data_version = package_data["version"]
        if not isinstance(data_version, str) or data_version not in schema_ocds.version_choices:
            context["unrecognized_version_data"] = json.dumps(data_version)

    context["has_records"] = "records" in package_data

    return render(request, "cove_ocds/explore_base.html", context)
