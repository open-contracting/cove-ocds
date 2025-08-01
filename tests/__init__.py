import re

from django.conf import settings

WHITESPACE = re.compile(r"\s+")
schema_version_choices = settings.COVE_CONFIG["schema_version_choices"]
OCDS_DEFAULT_SCHEMA_VERSION = list(schema_version_choices)[-1]
OCDS_SCHEMA_VERSIONS_DISPLAY = [display for (display, _, _) in schema_version_choices.values()]


def assert_in(elements, expected, not_expected):
    actuals = [
        WHITESPACE.sub(" ", element.text_content().strip()) if hasattr(element, "text_content") else element.text
        for element in elements
    ]

    for text in expected:
        assert any(text in actual for actual in actuals), f"{text!r} not in {actuals!r}"

    for text in not_expected:
        for actual in actuals:
            assert text not in actual
