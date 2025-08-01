import os
from pathlib import Path

import pytest
from django.test import override_settings
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def skip_if_remote():
    """Use this fixture to skip tests that require specific settings configured via environment variables."""
    if "CUSTOM_SERVER_URL" in os.environ:
        pytest.skip()


@pytest.fixture(scope="session")
def server_url(live_server):
    if "CUSTOM_SERVER_URL" in os.environ:
        return os.environ["CUSTOM_SERVER_URL"]
    return live_server.url


@pytest.fixture
def page():
    with (
        override_settings(
            # Needed for JavaScript tests, CSS tests, and /media/ URLs.
            STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
        ),
        sync_playwright() as p,
        p.chromium.launch() as browser,
        browser.new_context() as context,
    ):
        context.set_default_timeout(10000)
        page = context.new_page()
        yield page


@pytest.fixture
@pytest.mark.django_db
def submit_url(request, server_url, page, httpserver):
    def inner(filename):
        if "CUSTOM_SERVER_URL" in os.environ:
            source_url = f"https://raw.githubusercontent.com/open-contracting/cove-ocds/main/tests/fixtures/{filename}"
        else:
            with (Path("tests") / "fixtures" / filename).open("rb") as f:
                httpserver.serve_content(f.read())
            source_url = f"{httpserver.url}/{filename}"

        page.goto(server_url)
        page.fill("#id_source_url", source_url)
        page.click("button")

        return page

    return inner
