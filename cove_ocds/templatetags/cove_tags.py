from django import template
from django.utils.html import mark_safe
from django.utils.translation import ugettext_lazy as _

from cove.html_error_msg import html_error_msg, json_repr
from cove.templatetags.cove_tags import register

# https://github.com/open-contracting/lib-cove-ocds/blob/e6120c058340dfeec71cdcc67c976fa591b1a2b1/libcoveocds/common_checks.py
validation_error_lookup = {
    "date-time": mark_safe(_(
        'Incorrect date format. Dates should use the form YYYY-MM-DDT00:00:00Z. Learn more about <a href="https://standard.open-contracting.org/latest/en/schema/reference/#date">dates in OCDS</a>.'  # noqa: E501
    )),
}


@register.filter(name='html_error_msg')
def html_error_msg_ocds(error):
    if error["error_id"] == "releases_both_embedded_and_linked":
        return _(
            "This array should contain either entirely embedded releases or "
            "linked releases. Embedded releases contain an 'id' whereas linked "
            "releases do not. Your releases contain a mixture."
        )
    elif error["error_id"] == "oneOf_any":
        return _("%s is not valid under any of the given schemas") % (json_repr(error["instance"]),)
    elif error["error_id"] == "oneOf_each":
        return _("%(instance)s is valid under each of %(reprs)s") % {
            "instance": json_repr(error["instance"]),
            "reprs": error.get("reprs")
        }

    new_message = validation_error_lookup.get(error["message_type"])
    if new_message:
        return new_message
    else:
        return html_error_msg(error)
