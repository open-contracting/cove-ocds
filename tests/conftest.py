import os
from pathlib import Path

import pytest
from django.test import override_settings

from tests import REMOTE, setup_agent


@pytest.fixture(scope="session")
def server_url(live_server):
    return os.getenv("CUSTOM_SERVER_URL", live_server.url)


@pytest.fixture
def page():
    with (
        override_settings(
            # Needed for JavaScript and CSS tests.
            STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
        ),
        setup_agent() as page,
    ):
        yield page


@pytest.fixture
@pytest.mark.django_db
def submit_url(request, httpserver, server_url, page):
    def inner(filename):
        if REMOTE:
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
