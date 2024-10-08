from django.utils.functional import lazy
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext as _
from libcove.lib.exceptions import CoveInputDataError

mark_safe_lazy = lazy(mark_safe, str)


def raise_invalid_version_argument(version):
    raise CoveInputDataError(
        context={
            "sub_title": _("Unrecognised version of the schema"),
            "link": "index",
            "link_text": _("Try Again"),
            "msg": _(
                format_html(
                    "We think you tried to run your data against an unrecognised version of "
                    'the schema.\n\n<span class="glyphicon glyphicon-exclamation-sign" '
                    'aria-hidden="true"></span> <strong>Error message:</strong> <em>{}</em> is '
                    "not a recognised choice for the schema version",
                    version,
                )
            ),
            "error": _("%(version)s is not a known schema version") % {"version": version},
        }
    )


def raise_invalid_version_data_with_patch(version):
    raise CoveInputDataError(
        context={
            "sub_title": _("Version format does not comply with the schema"),
            "link": "index",
            "link_text": _("Try Again"),
            "msg": _(
                format_html(
                    'The value for the <em>"version"</em> field in your data follows the '
                    "<em>major.minor.patch</em> pattern but according to the schema the patch digit "
                    'shouldn\'t be included (e.g. <em>"1.1.0"</em> should appear as <em>"1.1"</em> in '
                    "your data as this tool always uses the latest patch release for a major.minor "
                    'version).\n\nPlease get rid of the patch digit and try again.\n\n<span class="glyphicon '
                    'glyphicon-exclamation-sign" aria-hidden="true"></span> <strong>Error message: '
                    "</strong> <em>{}</em> format does not comply with the schema",
                    version,
                )
            ),
            "error": _("%(version)s is not a known schema version") % {"version": version},
        }
    )


def raise_json_deref_error(error):
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
                    error,
                )
            ),
            "error": _("%(error)s") % {"error": error},
        }
    )


def raise_missing_package_error():
    raise CoveInputDataError(
        context={
            "sub_title": _("Missing OCDS package"),
            "link": "index",
            "link_text": _("Try Again"),
            "msg": mark_safe_lazy(
                _(
                    "We could not detect a package structure at the top-level of your data. "
                    'OCDS releases and records should be published within a <a href="https://'
                    'standard.open-contracting.org/latest/en/schema/release_package/">release '
                    'package </a> or <a href="https://standard.open-contracting.org/latest/en'
                    '/schema/record_package/"> record package</a> to provide important meta-'
                    'data. For more information, please refer to the <a href="https://standard.'
                    'open-contracting.org/latest/en/primer/releases_and_records/"> '
                    "Releases and Records section </a> in the OCDS documentation.\n\n<span "
                    'class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> '
                    "<strong>Error message:</strong> <em>Missing OCDS package</em>"
                )
            ),
            "error": _("Missing OCDS package"),
        }
    )
