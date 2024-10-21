# https://github.com/OpenDataServices/lib-cove-web/blob/main/cove/html_error_msg.py

import json

from django.utils.html import escape, format_html, mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from libcove.lib.tools import decimal_default

# These are "safe" html that we trust
# Don't insert any values into these strings without ensuring escaping
# e.g. using django's format_html function.
validation_error_template_lookup_safe = {
    "date-time": _("Date is not in the correct format"),
    "uri": _("Invalid 'uri' found"),
    "string": _(
        "{}<code>{}</code> is not a string. Check that the value {} has quotes at the start and end. "
        "Escape any quotes in the value with <code>\\</code>"
    ),
    "integer": _(
        "{}<code>{}</code> is not a integer. Check that the value {} doesn’t contain decimal points "
        "or any characters other than 0-9. Integer values should not be in quotes. "
    ),
    "number": _(
        "{}<code>{}</code> is not a number. Check that the value {} doesn’t contain any characters "
        "other than 0-9 and dot (<code>.</code>). Number values should not be in quotes. "
    ),
    "object": _("{}<code>{}</code> is not a JSON object"),
    "array": _("{}<code>{}</code> is not a JSON array"),
    "boolean": _("{}<code>{}</code> is not a JSON boolean"),
    "null": _("{}<code>{}</code> is not null"),
}


def json_repr(s):
    """Prefer JSON to repr(), used by jsonschema."""
    return json.dumps(s, sort_keys=True, default=decimal_default)


def html_error_msg(error):
    if error["error_id"] == "releases_both_embedded_and_linked":
        return _(
            "This array should contain either entirely embedded releases or "
            "linked releases. Embedded releases contain an 'id' whereas linked "
            "releases do not. Your releases contain a mixture."
        )

    if error["error_id"] == "oneOf_any":
        return _("%s is not valid under any of the given schemas") % (json_repr(error["instance"]),)

    if error["error_id"] == "oneOf_each":
        return _("%(instance)s is valid under each of %(reprs)s") % {
            "instance": json_repr(error["instance"]),
            "reprs": error.get("reprs"),
        }

    if error["message_type"] == "date-time":
        return mark_safe(
            _(
                # https://github.com/open-contracting/lib-cove-ocds/blob/main/libcoveocds/common_checks.py
                "Incorrect date format. Dates should use the form YYYY-MM-DDT00:00:00Z. Learn more about "
                '<a href="https://standard.open-contracting.org/latest/en/schema/reference/#date">dates in OCDS</a>.'
            )
        )

    # https://github.com/OpenDataServices/lib-cove-web/blob/main/cove/html_error_msg.py

    # This should not happen for json schema validation, but may happen for
    # other forms of validation, e.g. XML for IATI
    if "validator" not in error:
        return error["message"]

    # Support cove-ocds, which hasn't fully moved over to the template tag based approach
    if "message_safe" in error and error["message_safe"] != escape(error["message"]):
        return format_html(error["message_safe"])

    e_validator = error["validator"]
    e_validator_value = error.get("validator_value")
    validator_type = error["message_type"]
    null_clause = error["null_clause"]
    header = error["header_extra"]

    pre_header = _("Array Element ") if isinstance(header, str) and "[number]" in header else ""

    null_clause = ""
    if e_validator in ("format", "type"):
        if isinstance(e_validator_value, list):
            if "null" not in e_validator_value:
                null_clause = _("is not null, and")
        else:
            null_clause = _("is not null, and")

        if validator_type in validation_error_template_lookup_safe:
            message_safe_template = validation_error_template_lookup_safe[validator_type]

            return format_html(message_safe_template, pre_header, error["header"], null_clause)
        if e_validator == "format":
            return _("%(instance)s is not a %(validator_value)s") % {
                "instance": json_repr(error.get("instance")),
                "validator_value": json_repr(e_validator_value),
            }

    if e_validator == "required":
        path_no_number = error["path_no_number"].split("/")
        if len(path_no_number) > 1:
            parent_name = path_no_number[-1]
            return format_html(
                _("<code>{}</code> is missing but required within <code>{}</code>"),
                error["header"],
                parent_name,
            )
        return format_html(_("<code>{}</code> is missing but required"), error["header"])

    if e_validator == "enum":
        return format_html(_("Invalid code found in <code>{}</code>"), header)

    if e_validator == "pattern":
        return format_html(
            _("<code>{}</code> does not match the regex <code>{}</code>"),
            header,
            e_validator_value,
        )

    if e_validator == "minItems":
        if e_validator_value == 1:
            return format_html(
                _(
                    "<code>{}</code> is too short. You must supply at least one value, "
                    "or remove the item entirely (unless it’s required)."
                ),
                json_repr(error.get("instance")),
            )
        return format_html(
            _("<code>{}</code> is too short"),
            json_repr(error.get("instance")),
        )

    if e_validator == "minLength":
        if e_validator_value == 1:
            return format_html(
                _(
                    "<code>{}</code> is too short. Strings must be at least one character. "
                    "This error typically indicates a missing value."
                ),
                json_repr(error.get("instance")),
            )
        return format_html(
            _("<code>{}</code> is too short"),
            json_repr(error.get("instance")),
        )

    if e_validator == "maxItems":
        return format_html(
            _("<code>{}</code> is too long"),
            json_repr(error.get("instance")),
        )

    if e_validator == "maxLength":
        return format_html(
            _("<code>{}</code> is too long"),
            json_repr(error.get("instance")),
        )

    if e_validator == "minProperties":
        return _("{} does not have enough properties").format(json_repr(error.get("instance")))

    if e_validator == "maxProperties":
        return _("{} has too many properties").format(json_repr(error.get("instance")))

    if e_validator == "minimum":
        if error.get("exclusiveMinimum", False):
            return _("%(instance)s is less than or equal to the minimum of %(validator_value)s") % {
                "instance": json_repr(error.get("instance")),
                "validator_value": json_repr(e_validator_value),
            }
        return _("%(instance)s is less than the minimum of %(validator_value)s") % {
            "instance": json_repr(error.get("instance")),
            "validator_value": json_repr(e_validator_value),
        }

    if e_validator == "maximum":
        if error.get("exclusiveMaximum", False):
            return _("%(instance)s is more than or equal to the maximum of %(validator_value)s") % {
                "instance": json_repr(error.get("instance")),
                "validator_value": json_repr(e_validator_value),
            }
        return _("%(instance)s is more than the maximum of %(validator_value)s") % {
            "instance": json_repr(error.get("instance")),
            "validator_value": json_repr(e_validator_value),
        }

    if e_validator == "anyOf":
        return _("%s is not valid under any of the given schemas") % (json_repr(error["instance"]),)

    if e_validator == "multipleOf":
        return _("%(instance)s is not a multiple of %(validator_value)s") % {
            "instance": json_repr(error.get("instance")),
            "validator_value": json_repr(e_validator_value),
        }

    if e_validator == "not":
        return _("%(validator_value)s is not allowed for %(instance)s") % {
            "instance": json_repr(error.get("instance")),
            "validator_value": json_repr(e_validator_value),
        }

    if e_validator == "additionalItems":
        extras = error.get("extras") or []
        return ngettext(
            "Additional items are not allowed (%s was unexpected)",
            "Additional items are not allowed (%s were unexpected)",
            len(extras),
        ) % (extras,)

    if e_validator == "dependencies":
        return _("%(each)s is a dependency of %(property)s") % {
            "each": json_repr(error.get("each")),
            "property": json_repr(error.get("property")),
        }

    if error.get("error_id"):
        if error["error_id"] == "uniqueItems_no_ids":
            return _("Array has non-unique elements")

        if error["error_id"].startswith("uniqueItems_with_"):
            id_name = error["error_id"][len("uniqueItems_with_") :]
            if "__" in id_name:
                id_names = id_name.split("__")
                return _("Non-unique combination of {} values").format(", ".join(id_names))
            return _("Non-unique {} values").format(id_name)

        if error["error_id"] == "additionalProperties_not_allowed":
            extras = error.get("extras") or []
            return ngettext(
                "Additional properties are not allowed (%s was unexpected)",
                "Additional properties are not allowed (%s were unexpected)",
                len(extras),
            ) % (extras,)

        if error["error_id"] == "additionalProperties_does_not_match_regexes":
            extras = error.get("extras") or []
            return ngettext(
                "%(extras)s does not match any of the regexes: %(patterns)s",
                "%(extras)s do not match any of the regexes: %(patterns)s",
                len(extras),
            ) % {
                "extras": error["reprs"][0],
                "patterns": error["reprs"][1],
            }

    return error["message"]
