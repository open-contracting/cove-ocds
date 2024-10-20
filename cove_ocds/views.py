import json
import logging
import re
import warnings
from collections import defaultdict
from http import HTTPStatus

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from flattentool.exceptions import FlattenToolValueError, FlattenToolWarning
from libcove.lib.common import get_spreadsheet_meta_data
from libcove.lib.converters import convert_spreadsheet
from libcove.lib.exceptions import UnrecognisedFileType
from libcove.lib.tools import get_file_type
from libcoveocds.common_checks import common_checks_ocds
from libcoveocds.config import LibCoveOCDSConfig
from libcoveocds.schema import SchemaOCDS

from cove_ocds import forms, models, util
from cove_ocds.exceptions import InputError

logger = logging.getLogger(__name__)


default_form_classes = {
    "upload_form": forms.UploadForm,
    "url_form": forms.UrlForm,
    "text_form": forms.TextForm,
}


@csrf_protect
def data_input(request, form_classes=default_form_classes, text_file_name="test.json"):
    forms = {form_name: form_class() for form_name, form_class in form_classes.items()}
    request_data = None
    if "source_url" in request.GET and settings.COVE_CONFIG.get("allow_direct_web_fetch", False):
        request_data = request.GET
    if request.POST:
        request_data = request.POST
    if request_data:
        if "source_url" in request_data:
            form_name = "url_form"
        elif "paste" in request_data:
            form_name = "text_form"
        else:
            form_name = "upload_form"
        form = form_classes[form_name](request_data, request.FILES)
        forms[form_name] = form
        if form.is_valid():
            data = models.SuppliedData() if form_name == "text_form" else form.save(commit=False)

            data.save()
            if form_name == "url_form":
                try:
                    data.download()
                except requests.exceptions.InvalidURL as err:
                    raise InputError(
                        status=HTTPStatus.UNPROCESSABLE_ENTITY,
                        heading=_("The provided URL is invalid"),
                        message=str(err),
                    ) from None
                except requests.Timeout as err:
                    raise InputError(
                        status=HTTPStatus.GATEWAY_TIMEOUT,
                        heading=_("The provided URL timed out after %(timeout)s seconds") % settings.REQUESTS_TIMEOUT,
                        message=str(err),
                    ) from None
                except requests.ConnectionError as err:
                    raise InputError(
                        status=HTTPStatus.GATEWAY_TIMEOUT,
                        heading=_("The provided URL did not respond"),
                        message=f"{err}\n\n"
                        + _(
                            "Check that your URL is accepting web requests: that is, it is not on localhost, is not "
                            "in an intranet, does not have SSL/TLS errors, and does not block user agents."
                        ),
                    ) from None
                except requests.HTTPError as err:
                    raise InputError(
                        status=HTTPStatus.BAD_GATEWAY,
                        heading=_("The provided URL responded with an error"),
                        message=f"{err}\n\n"
                        + _(
                            "Check that your URL is responding to web requests: that is, it does not require "
                            "authentication, and does not block user agents."
                        ),
                    ) from None
            elif form_name == "text_form":
                data.original_file.save(text_file_name, ContentFile(form["paste"].value()))
            return redirect(reverse("explore", args=(data.pk,)))

    return render(request, "input.html", {"forms": forms})


def explore_ocds(request, pk):
    try:
        supplied_data = models.SuppliedData.objects.get(pk=pk)
    except (
        models.SuppliedData.DoesNotExist,
        ValidationError,
    ):  # Catches primary key does not exist and badly formed UUID
        raise InputError(
            status=HTTPStatus.NOT_FOUND,
            heading=_("Sorry, the page you are looking for is not available"),
            message=_("We don't seem to be able to find the data you requested."),
        ) from None

    try:
        if supplied_data.original_file.path.endswith("validation_errors-3.json"):
            raise InputError(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                heading=_("You are not allowed to upload a file with this name."),
                message=_("Rename the file or change the URL and try again."),
            ) from None

        try:
            file_type = get_file_type(supplied_data.original_file)
        except UnrecognisedFileType:
            raise InputError(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                heading=_("Sorry, we can't process that data"),
                message=_("We did not recognise the file type.\n\nWe can only process json, csv, ods and xlsx files."),
            ) from None

        context = {
            "original_file_url": supplied_data.original_file.url,
            "original_file_size": supplied_data.original_file.size,
            "file_type": file_type,
            "current_url": request.build_absolute_uri(),
            "source_url": supplied_data.source_url,
            "created_datetime": supplied_data.created.strftime("%A, %d %B %Y %I:%M%p %Z"),
            "support_email": settings.SUPPORT_EMAIL,
        }
    except FileNotFoundError:
        raise InputError(
            status=HTTPStatus.NOT_FOUND,
            heading=_("Sorry, the page you are looking for is not available"),
            message=_(
                "The data you were hoping to explore no longer exists.\n\nThis is because all "
                "data supplied to this website is automatically deleted after %s days, and therefore "
                "the analysis of that data is no longer available."
            )
            % getattr(settings, "DELETE_FILES_AFTER_DAYS", 7),
        ) from None

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
        # Read as text, because the json module can read binary UTF-16 and UTF-32.
        with open(supplied_data.original_file.path, encoding="utf-8") as f:
            try:
                package_data = json.load(f)
            except UnicodeError as err:
                raise InputError(
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                    heading=_("Sorry, we can't process that data"),
                    message=format_html(
                        _(
                            "The file that you uploaded doesn't appear to be well formed JSON. OCDS JSON follows the "
                            "I-JSON format, which requires UTF-8 encoding. Ensure that your file uses UTF-8 encoding, "
                            "then try uploading again.\n\n"
                            '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> <strong>'
                            "Error message:</strong> {}"
                        ),
                        err,
                    ),
                ) from None
            except ValueError as err:
                raise InputError(
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                    heading=_("Sorry, we can't process that data"),
                    message=format_html(
                        _(
                            "We think you tried to upload a JSON file, but it is not well formed JSON.\n\n"
                            '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> <strong>'
                            "Error message:</strong> {}"
                        ),
                        err,
                    ),
                ) from None

        if not isinstance(package_data, dict):
            raise InputError(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                heading=_("Sorry, we can't process that data"),
                message=_("OCDS JSON should have an object as the top level, the JSON you supplied does not."),
            ) from None

        schema_ocds = util.get_schema(lib_cove_ocds_config, package_data)
    else:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FlattenToolWarning)

            try:
                meta_data = get_spreadsheet_meta_data(
                    supplied_data.upload_dir(),
                    supplied_data.original_file.path,
                    SchemaOCDS(select_version="1.1", lib_cove_ocds_config=lib_cove_ocds_config).pkg_schema_url,
                    context["file_type"],
                )
            except Exception as err:
                logger.exception("", extra={"request": request})
                raise InputError(
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                    heading=_("Sorry, we can't process that data"),
                    message=_(
                        "We think you tried to supply a spreadsheet, but we failed to convert it."
                        "\n\nError message: %(error)r"
                    )
                    % {"error": err},
                ) from None

        meta_data.setdefault("version", "1.1")

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
                raise InputError(
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                    heading=_("Sorry, we can't process that data"),
                    message=format_html(
                        _(
                            "The table isn't structured correctly. For example, a JSON Pointer (<code>tender"
                            "</code>) can't be both a value (<code>tender</code>), a path to an object (<code>"
                            "tender/id</code>) and a path to an array (<code>tender/0/title</code>).\n\n"
                            '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> '
                            "<strong>Error message:</strong> {}",
                        ),
                        err,
                    ),
                ) from None
            except Exception as err:
                logger.exception("", extra={"request": request})
                raise InputError(
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                    heading=_("Sorry, we can't process that data"),
                    message=_(
                        "We think you tried to supply a spreadsheet, but we failed to convert it."
                        "\n\nError message: %(error)r"
                    )
                    % {"error": err},
                ) from None

        with open(context["converted_path"], "rb") as f:
            package_data = json.load(f)

    if "releases" not in package_data and "records" not in package_data:
        raise InputError(
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
            heading=_("Missing OCDS package"),
            message=mark_safe(
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
        ) from None

    # Perform the validation.

    context = common_checks_ocds(context, supplied_data.upload_dir(), package_data, schema_ocds)

    # Set by SchemaOCDS.get_schema_obj(deref=True), which, at the latest, is called indirectly by common_checks_ocds().
    if schema_ocds.json_deref_error:
        raise InputError(
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
            heading=_("JSON reference error"),
            message=_(
                format_html(
                    "We have detected a JSON reference error in the schema. This <em> may be "
                    "</em> due to some extension trying to resolve non-existing references. "
                    '\n\n<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true">'
                    "</span> <strong>Error message:</strong> <em>{}</em>",
                    schema_ocds.json_deref_error,
                )
            ),
        ) from None

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

    context["validation_errors_grouped"] = validation_errors_grouped

    for key in ("additional_closed_codelist_values", "additional_open_codelist_values"):
        for additional_codelist_values in context[key].values():
            if additional_codelist_values["codelist_url"].startswith(schema_ocds.codelists):
                additional_codelist_values["codelist_url"] = (
                    f"https://standard.open-contracting.org/{schema_ocds.version}/en/schema/codelists/#"
                    + re.sub(r"([A-Z])", r"-\1", additional_codelist_values["codelist"].split(".", 1)[0]).lower()
                )

    if "version" in package_data:
        data_version = package_data["version"]
        if not isinstance(data_version, str) or data_version not in schema_ocds.version_choices:
            context["unrecognized_version_data"] = json.dumps(data_version)

    context["has_records"] = "records" in package_data

    return render(request, "explore.html", context)
