import os
import re
from contextlib import contextmanager

from django.conf import settings
from playwright.sync_api import sync_playwright

REMOTE = "CUSTOM_SERVER_URL" in os.environ
WHITESPACE = re.compile(r"\s+")
SCHEMA_VERSION_CHOICES = settings.COVE_CONFIG["schema_version_choices"]
DEFAULT_SCHEMA_VERSION = list(SCHEMA_VERSION_CHOICES)[-1]


@contextmanager
def setup_agent():
    with sync_playwright() as p, p.chromium.launch() as browser, browser.new_context() as context:
        context.set_default_timeout(10000)
        yield context.new_page()


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
