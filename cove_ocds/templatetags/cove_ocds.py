from cove.html_error_msg import html_error_msg, json_repr
from cove.templatetags.cove_tags import register  # as such, `load cove_ocds` implicitly calls `load cove_tags`
from dateutil import parser
from django.utils.html import mark_safe
from django.utils.translation import gettext as _
from rfc3339_validator import validate_rfc3339


@register.filter(name="html_error_msg")
def html_error_msg_ocds(error):
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

    return html_error_msg(error)


@register.filter
def to_datetime(value):
    if value and validate_rfc3339(value):
        return parser.parse(value)
    return None
