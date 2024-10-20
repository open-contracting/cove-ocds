import json

from django import template
from django.conf import settings
from django.utils.html import mark_safe
from django.utils.translation import gettext as _

from cove_ocds.html_error_msg import html_error_msg, json_repr

register = template.Library()


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


@register.filter(name="json")
def json_dumps(data):
    return json.dumps(data)


# https://github.com/OpenDataServices/lib-cove-web/blob/main/cove/templatetags/cove_tags.py


@register.inclusion_tag("modal_errors.html")
def cove_modal_errors(**context):
    context["validation_error_locations_length"] = settings.VALIDATION_ERROR_LOCATIONS_LENGTH
    return context


@register.filter
def json_decode(error_json):
    return json.loads(error_json)


@register.filter
def concat(arg1, arg2):
    return f"{arg1}{arg2}"


@register.filter
def subtract(value, arg):
    return value - arg


@register.filter
def take_or_sample(population, k):
    return population[:k]


@register.filter
def list_from_attribute(list_of_dicts, key_name):
    return [value[key_name] for value in list_of_dicts]
