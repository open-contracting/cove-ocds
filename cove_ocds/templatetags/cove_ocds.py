import json

from django import template

from cove_ocds.html_error_msg import html_error_msg

register = template.Library()
register.filter()(html_error_msg)


@register.filter(name="json")
def json_dumps(data):
    return json.dumps(data)


@register.filter
def json_decode(error_json):
    return json.loads(error_json)


@register.filter
def concat(a, b):
    return f"{a}{b}"


@register.filter
def subtract(value, arg):
    return value - arg


@register.filter
def list_from_attribute(list_of_dicts, key_name):
    return [value[key_name] for value in list_of_dicts]
