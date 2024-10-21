import os
import time

import pytest
from django.test import override_settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

BROWSER = os.getenv("BROWSER", "ChromeHeadless")


@pytest.fixture(scope="module")
def browser():
    if BROWSER == "ChromeHeadless":
        options = Options()
        options.add_argument("--headless")
        browser = webdriver.Chrome(options=options)
    else:
        browser = getattr(webdriver, BROWSER)()
    browser.implicitly_wait(3)

    with override_settings(
        STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    ):
        yield browser

    browser.quit()


@pytest.fixture(scope="module")
def server_url(live_server):
    if "CUSTOM_SERVER_URL" in os.environ:
        return os.environ["CUSTOM_SERVER_URL"]
    return live_server.url


@pytest.fixture()
def url_input_browser(request, server_url, browser, httpserver):
    def _url_input_browser(source_filename, *, output_source_url=False):
        if source_filename.startswith("http"):
            source_url = source_filename
        elif "CUSTOM_SERVER_URL" in os.environ:
            source_url = (
                f"https://raw.githubusercontent.com/open-contracting/cove-ocds/main/tests/fixtures/{source_filename}"
            )
        else:
            with open(os.path.join("tests", "fixtures", source_filename), "rb") as fp:
                httpserver.serve_content(fp.read())
            source_url = f"{httpserver.url}/{source_filename}"

        browser.get(server_url)
        time.sleep(0.5)
        browser.find_element(By.ID, "id_source_url").send_keys(source_url)
        browser.find_element(By.CSS_SELECTOR, "#fetchURL > div.form-group > button.btn.btn-primary").click()

        if output_source_url:
            return browser, source_url
        return browser

    return _url_input_browser


@pytest.fixture
def skip_if_remote():
    # If we're testing a remote server, then we can't run these tests, as we
    # can't make assumptions about what environment variables will be set
    if "CUSTOM_SERVER_URL" in os.environ:
        pytest.skip()
