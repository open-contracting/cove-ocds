import os
import time

import pytest
import requests
from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

BROWSER = os.environ.get("BROWSER", "ChromeHeadless")

OCDS_DEFAULT_SCHEMA_VERSION = settings.COVE_CONFIG["schema_version"]
OCDS_SCHEMA_VERSIONS = settings.COVE_CONFIG["schema_version_choices"]
OCDS_SCHEMA_VERSIONS_DISPLAY = [display_url[0] for version, display_url in OCDS_SCHEMA_VERSIONS.items()]


@pytest.fixture(scope="module")
def browser(request):
    if BROWSER == "ChromeHeadless":
        options = Options()
        options.add_argument("--headless")
        browser = webdriver.Chrome(options=options)
    else:
        browser = getattr(webdriver, BROWSER)()
    browser.implicitly_wait(3)

    yield browser

    browser.quit()


@pytest.fixture(scope="module")
def server_url(request, live_server):
    if "CUSTOM_SERVER_URL" in os.environ:
        return os.environ["CUSTOM_SERVER_URL"]
    else:
        return live_server.url


@pytest.fixture()
def url_input_browser(request, server_url, browser, httpserver):
    def _url_input_browser(source_filename, output_source_url=False):
        with open(os.path.join("tests", "fixtures", source_filename), "rb") as fp:
            httpserver.serve_content(fp.read())
        if "CUSTOM_SERVER_URL" in os.environ:
            # Use urls pointing to GitHub if we have a custom (probably non local) server URL
            source_url = (
                "https://raw.githubusercontent.com/open-contracting/cove-ocds/main/tests/fixtures/" + source_filename
            )
        else:
            source_url = httpserver.url + "/" + source_filename

        browser.get(server_url)
        time.sleep(0.5)
        browser.find_element(By.ID, "id_source_url").send_keys(source_url)
        browser.find_element(By.CSS_SELECTOR, "#fetchURL > div.form-group > button.btn.btn-primary").click()

        if output_source_url:
            return browser, source_url
        return browser

    return _url_input_browser


@pytest.mark.parametrize(
    ("link_text", "expected_text", "css_selector", "url"),
    [
        (
            "Open Contracting",
            "Our world runs on public contracts.",
            "h2",
            "http://www.open-contracting.org/",
        ),
        (
            "Open Contracting Data Standard",
            "Open Contracting Data Standard",
            "#open-contracting-data-standard",
            "http://standard.open-contracting.org/",
        ),
    ],
)
def test_footer_ocds(server_url, browser, link_text, expected_text, css_selector, url):
    browser.get(server_url)
    footer = browser.find_element(By.ID, "footer")
    link = footer.find_element(By.LINK_TEXT, link_text)
    href = link.get_attribute("href")
    assert url in href
    link.click()
    time.sleep(0.5)
    assert expected_text in browser.find_element(By.CSS_SELECTOR, css_selector).text


def test_index_page_ocds(server_url, browser):
    browser.get(server_url)
    assert "Data Review Tool" in browser.find_element(By.TAG_NAME, "body").text
    assert "Using the data review tool" in browser.find_element(By.TAG_NAME, "body").text
    assert "'release'" in browser.find_element(By.TAG_NAME, "body").text
    assert "'record'" in browser.find_element(By.TAG_NAME, "body").text


@pytest.mark.parametrize(
    ("css_id", "link_text", "url"),
    [
        (
            "introduction",
            "schema",
            "http://standard.open-contracting.org/latest/en/schema/",
        ),
        (
            "introduction",
            "Open Contracting Data Standard (OCDS)",
            "http://standard.open-contracting.org/",
        ),
        (
            "how-to-use",
            "'release' and 'record'",
            "http://standard.open-contracting.org/latest/en/getting_started/releases_and_records/",
        ),
        (
            "how-to-use",
            "flattened serialization of OCDS",
            "http://standard.open-contracting.org/latest/en/implementation/serialization/",
        ),
        (
            "how-to-use",
            "Open Contracting Data Standard",
            "http://standard.open-contracting.org/",
        ),
    ],
)
def test_index_page_ocds_links(server_url, browser, css_id, link_text, url):
    browser.get(server_url)
    section = browser.find_element(By.ID, css_id)
    link = section.find_element(By.LINK_TEXT, link_text)
    href = link.get_attribute("href")
    assert url in href


def test_common_index_elements(server_url, browser):
    browser.get(server_url)
    browser.find_element(By.CSS_SELECTOR, "#more-information .panel-title").click()
    time.sleep(0.5)
    assert "What happens to the data I provide to this site?" in browser.find_element(By.TAG_NAME, "body").text
    assert "Why do you delete data after 90 days?" in browser.find_element(By.TAG_NAME, "body").text
    assert "Why provide converted versions?" in browser.find_element(By.TAG_NAME, "body").text
    assert "Terms & Conditions" in browser.find_element(By.TAG_NAME, "body").text
    assert "Open Data Services" in browser.find_element(By.TAG_NAME, "body").text
    assert "360 Giving" not in browser.find_element(By.TAG_NAME, "body").text


def test_terms_page(server_url, browser):
    browser.get(server_url + "/terms/")

    assert "Open Contracting Partnership" in browser.find_element(By.TAG_NAME, "body").text


def test_accordion(server_url, browser):
    browser.get(server_url)

    def buttons():
        return [b.is_displayed() for b in browser.find_elements(By.TAG_NAME, "button")]

    time.sleep(0.5)
    assert buttons() == [True, False, False]
    assert "Supply a URL" in browser.find_elements(By.TAG_NAME, "label")[0].text
    browser.find_element(By.PARTIAL_LINK_TEXT, "Upload").click()
    browser.implicitly_wait(1)
    time.sleep(0.5)
    assert buttons() == [False, True, False]
    browser.find_element(By.PARTIAL_LINK_TEXT, "Paste").click()
    time.sleep(0.5)
    assert buttons() == [False, False, True]
    assert "Paste (JSON only)" in browser.find_elements(By.TAG_NAME, "label")[2].text

    # Now test that the whole banner is clickable
    browser.find_element(By.ID, "headingOne").click()
    time.sleep(0.5)
    assert buttons() == [True, False, False]
    browser.find_element(By.ID, "headingTwo").click()
    time.sleep(0.5)
    assert buttons() == [False, True, False]
    browser.find_element(By.ID, "headingThree").click()
    time.sleep(0.5)
    assert buttons() == [False, False, True]


def test_500_error(server_url, browser):
    browser.get(server_url + "/test/500")
    # Check that our nice error message is there
    assert "Something went wrong" in browser.find_element(By.TAG_NAME, "body").text
    # Check for the exclamation icon
    # This helps to check that the theme including the css has been loaded
    # properly
    icon_span = browser.find_element(By.CLASS_NAME, "panel-danger").find_element(By.TAG_NAME, "span")
    assert "Glyphicons Halflings" in icon_span.value_of_css_property("font-family")
    assert icon_span.value_of_css_property("color") == "rgba(255, 255, 255, 1)"


@pytest.mark.parametrize(
    ("source_filename", "expected_text", "not_expected_text", "conversion_successful"),
    [
        (
            "tenders_releases_2_releases.json",
            ["Convert", "Schema", "OCDS release package schema version 1.0. You can"] + OCDS_SCHEMA_VERSIONS_DISPLAY,
            ["Schema Extensions", "The schema version specified in the file is"],
            True,
        ),
        (
            "tenders_releases_1_release_with_extensions_1_1.json",
            [
                "Schema Extensions",
                "Contract Parties (Organization structure)",
                "All the extensions above were applied",
                "copy of the schema with extension",
                "Structural Errors",
                "name is missing but required within buyer",
                "The schema version specified in the file is 1.1",
                "Party Scale",
            ],
            ["scale", "/releases/parties/details", "fetching failed"],
            True,
        ),
        (
            "tenders_1_release_with_extensions_1_1_missing_party_scale.json",
            [
                "Schema Extensions",
                "Contract Parties (Organization structure)",
                "scale",
                "/releases/parties/details",
            ],
            ["Party Scale"],
            True,
        ),
        (
            "tenders_releases_1_release_with_extensions_new_layout.json",
            [
                "Schema Extensions",
                "Lots",
                "A tender process can be divided into lots",
                "copy of the schema with extension",
                "Structural Errors",
                "id is missing but required within items",
            ],
            ["fetching failed"],
            True,
        ),
        (
            "tenders_releases_1_release_with_invalid_extensions.json",
            [
                "Schema Extensions",
                "https://raw.githubusercontent.com/open-contracting-extensions/",
                "badprotocol://example.com",
                "400: bad request",
                "Only those extensions successfully fetched",
                "copy of the schema with extension",
                "Structural Errors",
            ],
            ["All the extensions above were applied"],
            True,
        ),
        (
            "tenders_records_1_record_with_invalid_extensions.json",
            [
                "Party Scale",
                "The metrics extension supports publication of forecasts",
                "Get a copy of the schema with extension patches applied",
                "The following extensions failed",
                "Invalid code found in scale",
                "/records/compiledRelease/tender/targets",
                "The schema version specified in the file is 1.1",
                "/records/releases/tender/targets",
            ],
            ["checked against a schema with no extensions"],
            True,
        ),
        (
            "tenders_releases_deprecated_fields_against_1_1_live.json",
            [
                "Deprecated Fields",
                "The single amendment object has been deprecated",
                "documents at the milestone level is now deprecated",
                "releases/0/contracts/1/milestones/0",
                "releases/1/tender",
                "Contracts with no awards: 3",
            ],
            ["copy of the schema with extension"],
            True,
        ),
        (
            "tenders_releases_1_release_with_all_invalid_extensions.json",
            [
                "Schema Extensions",
                "badprotocol://example.com",
                "None of the extensions above could be applied",
                "400: bad request",
            ],
            ["copy of the schema with extension"],
            True,
        ),
        (
            "tenders_releases_2_releases_1_1_tenderers_with_missing_ids.json",
            [
                "We found 6 objects within arrays in your data without an id property",
                "Structure Warnings",
            ],
            [],
            True,
        ),
        (
            "tenders_releases_7_releases_check_ocids.json",
            ["Conformance (Rules)", "6 of your ocid fields have a problem"],
            [],
            True,
        ),
        (
            "ocds_release_nulls.json",
            ["Convert", "Save or Share these results"],
            [],
            True,
        ),
        (
            "badfile_all_validation_errors.json",
            [
                '"" is too short. Strings must be at least one character. This error typically indicates a missing value.',  # noqa: E501
                "An identifier for this particular release of information.",
                r"version does not match the regex ^(\d+\.)(\d+)$",
                "The version of the OCDS schema used in this package, expressed as major.minor For example: 1.0 or 1.1",  # noqa: E501
                "id is missing but required within tender",
                "initiationType is missing but required",
                "Incorrect date format. Dates should use the form YYYY-MM-DDT00:00:00Z. Learn more about dates in OCDS.",  # noqa: E501
                # This matches the description of the `date` field in release-schema.json.
                "The date on which the information contained in the release was first recorded in, or published by, any system.",  # noqa: E501
                "Invalid 'uri' found",
                "The URI of this package that identifies it uniquely in the world.",
                "Invalid code found in currency",
                "The currency of the amount, from the closed currency codelist.",
                "numberOfTenderers is not a integer. Check that the value doesn’t contain decimal points or any characters other than 0-9. Integer values should not be in quotes.",  # noqa: E501
                "The number of parties who submit a bid.",
                "amount is not a number. Check that the value doesn’t contain any characters other than 0-9 and dot (.). Number values should not be in quotes",  # noqa: E501
                "Amount as a number.",
                "ocid is not a string. Check that the value is not null, and has quotes at the start and end. Escape any quotes in the value with \\",  # noqa: E501
                "A globally unique identifier for this Open Contracting Process. Composed of an ocid prefix and an identifier for the contracting process. For more information see the Open Contracting Identifier guidance",  # noqa: E501
                "title is not a string. Check that the value has quotes at the start and end. Escape any quotes in the value with \\",  # noqa: E501
                "A title for this tender. This will often be used by applications as a headline to attract interest, and to help analysts understand the nature of this procurement",  # noqa: E501
                "parties is not a JSON array",
                "Information on the parties (organizations, economic operators and other participants) who are involved in the contracting process and their roles, e.g. buyer, procuring entity, supplier etc. Organization references elsewhere in the schema are used to refer back to this entries in this list.",  # noqa: E501
                "buyer is not a JSON object",
                "The id and name of the party being referenced. Used to cross-reference to the parties section",
                "[] is too short. You must supply at least one value, or remove the item entirely (unless it’s required).",  # noqa: E501
                "One or more values from the closed releaseTag codelist. Tags can be used to filter releases and to understand the kind of information that releases might contain",  # noqa: E501
            ],
            [],
            True,
        ),
        (
            "badfile_extension_validation_errors.json",
            [
                "Incorrect date format. Dates should use the form YYYY-MM-DDT00:00:00Z.",
                "The date when this bid was received.",
                "A local identifier for this bid",
                "Summary statistics on the number and nature of bids received.",
            ],
            ["Reference Docs"],
            True,
        ),
        # Conversion should still work for files that don't validate against the schema
        (
            "tenders_releases_2_releases_invalid.json",
            [
                "Convert",
                "Structural Errors",
                "id is missing but required",
                "Invalid 'uri' found",
            ],
            [],
            True,
        ),
        ("tenders_releases_2_releases_codelists.json", ["oh no", "GSINS"], [], True),
        # Test UTF-8 support
        ("utf8.json", "Convert", ["Ensure that your file uses UTF-8 encoding"], True),
        # Test that non UTF-8 files get an error, with a helpful message
        ("latin1.json", "Ensure that your file uses UTF-8 encoding", [], False),
        ("utf-16.json", "Ensure that your file uses UTF-8 encoding", [], False),
        # But we expect to see an error message if a file is not well formed JSON at all
        (
            "tenders_releases_2_releases_not_json.json",
            "not well formed JSON",
            [],
            False,
        ),
        (
            "tenders_releases_2_releases.xlsx",
            ["Convert", "Schema"] + OCDS_SCHEMA_VERSIONS_DISPLAY,
            ["Missing OCDS package"],
            True,
        ),
        ("badfile.json", "Statistics cannot be produced", [], True),
        # Test unconvertable JSON (main sheet "releases" is missing)
        ("unconvertable_json.json", "could not be converted", [], False),
        (
            "full_record.json",
            [
                "Number of records",
                "Structural Errors",
                "compiledRelease",
                "versionedRelease",
            ],
            [],
            True,
        ),
        # Test "version" value in data
        (
            "tenders_releases_1_release_with_unrecognized_version.json",
            [
                "Your data specifies a version 123.123 which is not recognised",
                f"checked against OCDS release package schema version {OCDS_DEFAULT_SCHEMA_VERSION}. You can",
                "checked against the current default version.",
                "Convert to Spreadsheet",
            ],
            ["Additional Fields (fields in data not in schema)", "Error message"],
            False,
        ),
        (
            "tenders_releases_1_release_with_wrong_version_type.json",
            [
                "Your data specifies a version 1000 (it must be a string) which is not recognised",
                f"checked against OCDS release package schema version {OCDS_DEFAULT_SCHEMA_VERSION}. You can",
                "Convert to Spreadsheet",
            ],
            ["Additional Fields (fields in data not in schema)", "Error message"],
            False,
        ),
        (
            "tenders_releases_1_release_with_patch_in_version.json",
            [
                '"version" field in your data follows the major.minor.patch pattern',
                "100.100.0 format does not comply with the schema",
                "Error message",
            ],
            ["Convert to Spreadsheet"],
            False,
        ),
        (
            "bad_toplevel_list.json",
            ["OCDS JSON should have an object as the top level, the JSON you supplied does not."],
            [],
            False,
        ),
        (
            "tenders_releases_1_release_with_extension_broken_json_ref.json",
            [
                "JSON reference error",
                "Unresolvable JSON pointer:",
                "/definitions/OrganizationReference",
            ],
            ["Convert to Spreadsheet"],
            False,
        ),
        (
            "tenders_releases_1_release_unpackaged.json",
            ["Missing OCDS package", "Error message: Missing OCDS package"],
            ["Convert to Spreadsheet"],
            False,
        ),
        (
            "tenders_releases_1_release_with_closed_codelist.json",
            ["Failed structural checks"],
            ["Passed structural checks"],
            True,
        ),
        (
            "tenders_releases_1_release_with_tariff_codelist.json",
            [
                "releases/contracts/tariffs",
                "chargePaidBy.csv",
                "notADocumentType",
                "notAPaidByCodelist",
            ],
            ["notADocumentType, tariffIllustration"],
            True,
        ),
        (
            "tenders_releases_1_release_with_various_codelists.json",
            [
                "needsAssessment, notADocumentType, tariffIllustration",
                "+releaseTag.csv: Codelist Error, Could not find code field in codelist",
                "-documentType.csv: Codelist error, Trying to remove non existing codelist value notACodelistValueAtAll",  # noqa: E501
                "+method.csv: Unicode Error, codelists need to be in UTF-8",
                "chargePaidBy.csv",
                "notAPaidByCodelist",
            ],
            [],
            True,
        ),
    ],
)
def test_url_input(
    server_url,
    url_input_browser,
    httpserver,
    source_filename,
    expected_text,
    not_expected_text,
    conversion_successful,
):
    browser, source_url = url_input_browser(source_filename, output_source_url=True)
    check_url_input_result_page(
        server_url,
        browser,
        httpserver,
        source_filename,
        expected_text,
        not_expected_text,
        conversion_successful,
    )

    selected_examples = ["tenders_releases_2_releases_invalid.json"]

    if source_filename in selected_examples:
        # refresh page to now check if tests still work after caching some data
        browser.get(browser.current_url)
        check_url_input_result_page(
            server_url,
            browser,
            httpserver,
            source_filename,
            expected_text,
            not_expected_text,
            conversion_successful,
        )
        browser.get(server_url + "?source_url=" + source_url)
        check_url_input_result_page(
            server_url,
            browser,
            httpserver,
            source_filename,
            expected_text,
            not_expected_text,
            conversion_successful,
        )


def check_url_input_result_page(
    server_url,
    browser,
    httpserver,
    source_filename,
    expected_text,
    not_expected_text,
    conversion_successful,
):
    # Avoid page refresh
    dont_convert = [
        "tenders_releases_1_release_with_unrecognized_version.json",
        "tenders_releases_1_release_with_wrong_version_type.json",
    ]

    if source_filename.endswith(".json") and source_filename not in dont_convert:
        try:
            browser.find_element(By.NAME, "flatten").click()
        except NoSuchElementException:
            pass

    body_text = browser.find_element(By.TAG_NAME, "body").text
    if isinstance(expected_text, str):
        expected_text = [expected_text]

    for text in expected_text:
        assert text in body_text
    for text in not_expected_text:
        assert text not in body_text

    assert "Data Review Tool" in browser.find_element(By.TAG_NAME, "body").text
    # assert 'Release Table' in browser.find_element(By.TAG_NAME, 'body').text

    if conversion_successful:
        if source_filename.endswith(".json"):
            assert "JSON (Original)" in body_text
            original_file = browser.find_element(By.LINK_TEXT, "JSON (Original)").get_attribute("href")
            if "record" not in source_filename:
                converted_file = browser.find_element(
                    By.PARTIAL_LINK_TEXT, "Excel Spreadsheet (.xlsx) (Converted from Original using schema version"
                ).get_attribute("href")
                assert "flattened.xlsx" in converted_file
        elif source_filename.endswith(".xlsx"):
            assert "(.xlsx) (Original)" in body_text
            original_file = browser.find_element(By.LINK_TEXT, "Excel Spreadsheet (.xlsx) (Original)").get_attribute(
                "href"
            )
            converted_file = browser.find_element(
                By.PARTIAL_LINK_TEXT, "JSON (Converted from Original using schema version"
            ).get_attribute("href")
            assert "unflattened.json" in converted_file
        elif source_filename.endswith(".csv"):
            assert "(.csv) (Original)" in body_text
            original_file = browser.find_element(By.LINK_TEXT, "CSV Spreadsheet (.csv) (Original)").get_attribute(
                "href"
            )
            converted_file = browser.find_element(
                By.PARTIAL_LINK_TEXT, "JSON (Converted from Original using schema version"
            ).get_attribute("href")
            assert "unflattened.json" in browser.find_element(
                By.PARTIAL_LINK_TEXT, "JSON (Converted from Original using schema version"
            ).get_attribute("href")

        assert source_filename in original_file
        assert "0 bytes" not in body_text
        # Test for Load New File button
        assert "Load New File" in body_text

        original_file_response = requests.get(original_file)
        assert original_file_response.status_code == 200
        assert int(original_file_response.headers["content-length"]) != 0

        if "record" not in source_filename:
            converted_file_response = requests.get(converted_file)
            if source_filename == "fundingproviders-grants_2_grants_titleswithoutrollup.xlsx":
                grant1 = converted_file_response.json()["grants"][1]
                assert grant1["recipientOrganization"][0]["department"] == "Test data"
                assert grant1["classifications"][0]["title"] == "Test"
            assert converted_file_response.status_code == 200
            assert int(converted_file_response.headers["content-length"]) != 0


DARK_RED = "rgba(169, 68, 66, 1)"
DARK_GREEN = "rgba(155, 175, 0, 1)"


@pytest.mark.parametrize(
    ("source_filename", "heading_color"),
    [
        # If everything's fine, it should be green
        ("tenders_releases_2_releases.json", DARK_GREEN),
        # It should be red on:
        # * Not valid against the schema
        (
            "tenders_releases_2_releases_invalid.json",
            DARK_RED,
        ),
        # * Disallowed values on closed codelists
        (
            "tenders_releases_1_release_with_closed_codelist.json",
            DARK_RED,
        ),
        # * Bad extensions
        (
            "tenders_releases_1_release_with_all_invalid_extensions.json",
            DARK_RED,
        ),
        # And same for records too:
        (
            "record_minimal_valid.json",
            DARK_GREEN,
        ),
        (
            "full_record.json",
            DARK_RED,
        ),
        (
            "tenders_records_1_record_with_invalid_extensions.json",
            DARK_RED,
        ),
    ],
)
def test_headlines_class(url_input_browser, source_filename, heading_color):
    browser = url_input_browser(source_filename)
    headlines_panel = browser.find_elements(By.CLASS_NAME, "panel")[0]
    actual = headlines_panel.find_element(By.CLASS_NAME, "panel-heading").value_of_css_property("background-color")

    # Check that this is actually the headlines panel
    assert headlines_panel.text.startswith("Headlines")
    assert heading_color == actual


def test_validation_error_messages(url_input_browser):
    browser = url_input_browser("badfile_all_validation_errors.json")
    for html in [
        '<code>""</code> is too short',
        r"<code>version</code> does not match the regex <code>^(\d+\.)(\d+)$</code>",
        "<code>id</code> is missing but required within <code>tender</code>",
        "<code>initiationType</code> is missing but required",
        'Incorrect date format. Dates should use the form YYYY-MM-DDT00:00:00Z. Learn more about <a href="https://standard.open-contracting.org/latest/en/schema/reference/#date">dates in OCDS</a>.',  # noqa: E501
        "Invalid code found in <code>currency</code>",
        "<code>numberOfTenderers</code> is not a integer",
        "<code>amount</code> is not a number. Check that the value  doesn’t contain any characters other than 0-9 and dot (<code>.</code>).",  # noqa: E501
        "<code>ocid</code> is not a string. Check that the value is not null, and has quotes at the start and end. Escape any quotes in the value with <code>\\</code>",  # noqa: E501
        'For more information see the <a href="https://standard.open-contracting.org/1.1/en/schema/identifiers/">Open Contracting Identifier guidance</a>',  # noqa: E501
        "<code>title</code> is not a string. Check that the value  has quotes at the start and end. Escape any quotes in the value with <code>\\</code>",  # noqa: E501
        "<code>parties</code> is not a JSON array",
        "<code>buyer</code> is not a JSON object",
        "<code>[]</code> is too short.",
        'One or more values from the closed <a href="https://standard.open-contracting.org/1.1/en/schema/codelists/#release-tag">releaseTag</a> codelist',  # noqa: E501
    ]:
        assert html in browser.page_source


def test_extension_validation_error_messages(url_input_browser):
    browser = url_input_browser("badfile_extension_validation_errors.json")
    for html in [
        "&lt;script&gt;alert('badscript');&lt;/script&gt;",
        "<a>test</a>",
    ]:
        assert html in browser.page_source
    for html in [
        "<script>alert('badscript');</script>",
        "badlink",
    ]:
        assert html not in browser.page_source


@pytest.mark.parametrize("warning_texts", [[], []])
@pytest.mark.parametrize("flatten_or_unflatten", ["flatten", "unflatten"])
def test_flattentool_warnings(server_url, browser, httpserver, monkeypatch, warning_texts, flatten_or_unflatten):
    # If we're testing a remove server then we can't run this test as we can't
    # set up the mocks
    if "CUSTOM_SERVER_URL" in os.environ:
        pytest.skip()
    # Actual input file doesn't matter, as we override
    # flattentool behaviour with a mock below
    if flatten_or_unflatten == "flatten":
        source_filename = "tenders_releases_2_releases.json"
    else:
        source_filename = "tenders_releases_2_releases.xlsx"

    import warnings

    import flattentool
    from flattentool.exceptions import DataErrorWarning

    def mockunflatten(input_name, output_name, *args, **kwargs):
        with open(kwargs["cell_source_map"], "w") as fp:
            fp.write("{}")
        with open(kwargs["heading_source_map"], "w") as fp:
            fp.write("{}")
        with open(output_name, "w") as fp:
            fp.write("{}")
            for warning_text in warning_texts:
                warnings.warn(warning_text, DataErrorWarning)

    def mockflatten(input_name, output_name, *args, **kwargs):
        with open(output_name + ".xlsx", "w") as fp:
            fp.write("{}")
            for warning_text in warning_texts:
                warnings.warn(warning_text, DataErrorWarning)

    mocks = {"flatten": mockflatten, "unflatten": mockunflatten}
    monkeypatch.setattr(flattentool, flatten_or_unflatten, mocks[flatten_or_unflatten])

    with open(os.path.join("tests", "fixtures", source_filename), "rb") as fp:
        httpserver.serve_content(fp.read())
    if "CUSTOM_SERVER_URL" in os.environ:
        # Use urls pointing to GitHub if we have a custom (probably non local) server URL
        source_url = (
            "https://raw.githubusercontent.com/open-contracting/cove-ocds/main/tests/fixtures/" + source_filename
        )
    else:
        source_url = httpserver.url + "/" + source_filename

    browser.get(server_url + "?source_url=" + source_url)

    if source_filename.endswith(".json"):
        browser.find_element(By.NAME, "flatten").click()

    body_text = browser.find_element(By.TAG_NAME, "body").text
    if len(warning_texts) == 0:
        assert "conversion Errors" not in body_text
        assert "Conversion Warnings" not in body_text
    else:
        assert warning_texts[0] in body_text
        assert "Conversion Errors" in body_text
        assert "conversion Warnings" not in body_text


@pytest.mark.parametrize(("data_url"), ["/data/0", "/data/324ea8eb-f080-43ce-a8c1-9f47b28162f3"])
def test_url_invalid_dataset_request(server_url, browser, data_url):
    # Test a badly formed hexadecimal UUID string
    browser.get(server_url + data_url)
    assert "We don't seem to be able to find the data you requested." in browser.find_element(By.TAG_NAME, "body").text
    # Test for well formed UUID that doesn't identify any dataset that exists
    browser.get(server_url + "/data/38e267ce-d395-46ba-acbf-2540cdd0c810")
    assert "We don't seem to be able to find the data you requested." in browser.find_element(By.TAG_NAME, "body").text
    assert "360 Giving" not in browser.find_element(By.TAG_NAME, "body").text
    # 363 - Tests there is padding round the 'go to home' button
    success_button = browser.find_element(By.CLASS_NAME, "success-button")
    assert success_button.value_of_css_property("padding-bottom") == "20px"


@pytest.mark.parametrize(
    (
        "source_filename",
        "expected",
        "not_expected",
        "expected_additional_field",
        "not_expected_additional_field",
    ),
    [
        (
            "tenders_releases_1_release_with_extensions_1_1.json",
            "structural checks against OCDS release package schema version 1.1",
            "version is missing but required",
            "methodRationale",
            "version",
        ),
        (
            "tenders_releases_1_release_with_invalid_extensions.json",
            "structural checks against OCDS release package schema version 1.0",
            "version is missing but required",
            "methodRationale",
            "version",
        ),
        (
            "tenders_releases_2_releases_with_metatab_version_1_1_extensions.xlsx",
            "structural checks against OCDS release package schema version 1.1",
            "version is missing but required",
            "methodRationale",
            "version",
        ),
    ],
)
def test_url_input_with_version(
    server_url,
    url_input_browser,
    httpserver,
    source_filename,
    expected,
    not_expected,
    expected_additional_field,
    not_expected_additional_field,
):
    browser = url_input_browser(source_filename)
    body_text = browser.find_element(By.TAG_NAME, "body").text
    additional_field_box = browser.find_element(By.ID, "additionalFieldTable").text

    assert expected in body_text
    assert not_expected not in body_text
    assert expected_additional_field in additional_field_box
    assert not_expected_additional_field not in additional_field_box

    # Refresh page to check if tests still work after caching the data
    browser.get(browser.current_url)

    assert expected in body_text
    assert not_expected not in body_text
    assert expected_additional_field in additional_field_box
    assert not_expected_additional_field not in additional_field_box


@pytest.mark.parametrize(
    (
        "source_filename",
        "select_version",
        "expected",
        "not_expected",
        "expected_additional_field",
        "not_expected_additional_field",
    ),
    [
        (
            "tenders_releases_1_release_with_extensions_1_1.json",
            "1.0",
            "structural checks against OCDS release package schema version 1.0",
            "version is missing but required",
            "version",
            "publisher",
        ),
        (
            "tenders_releases_1_release_with_invalid_extensions.json",
            "1.1",
            "version is missing but required",
            "structural checks against OCDS release package schema version 1.0",
            "methodRationale",
            "version",
        ),
        (
            "tenders_releases_2_releases_with_metatab_version_1_1_extensions.xlsx",
            "1.0",
            "structural checks against OCDS release package schema version 1.0",
            "version is missing but required",
            "version",
            "publisher",
        ),
    ],
)
def test_url_input_with_version_change(
    server_url,
    url_input_browser,
    httpserver,
    select_version,
    source_filename,
    expected,
    not_expected,
    expected_additional_field,
    not_expected_additional_field,
):
    browser = url_input_browser(source_filename)
    select = Select(browser.find_element(By.NAME, "version"))
    select.select_by_value(select_version)
    browser.find_element(By.CSS_SELECTOR, ".btn-primary[value='Go']").click()
    time.sleep(0.5)

    body_text = browser.find_element(By.TAG_NAME, "body").text
    additional_field_box = browser.find_element(By.ID, "additionalFieldTable").text

    assert expected in body_text
    assert not_expected not in body_text
    assert expected_additional_field in additional_field_box
    assert not_expected_additional_field not in additional_field_box

    # Refresh page to check if tests still work after caching the data
    browser.get(browser.current_url)

    assert expected in body_text
    assert not_expected not in body_text
    assert expected_additional_field in additional_field_box
    assert not_expected_additional_field not in additional_field_box


@pytest.mark.parametrize(
    ("source_filename", "expected", "not_expected"),
    [
        (
            "tenders_releases_1_release_with_extensions_1_1.json",
            [
                "Party Scale",
                "The metrics extension supports publication of forecasts",
                "All the extensions above were applied to extend the schema",
                "Get a copy of the schema with extension patches applied",
            ],
            [
                "The following extensions failed",
                "extensions were not introduced in the schema until version 1.1.",
            ],
        ),
        (
            "tenders_releases_1_release_with_invalid_extensions.json",
            [
                "Party Scale",
                "The metrics extension supports publication of forecasts",
                "Get a copy of the schema with extension patches applied",
                "The following extensions failed",
                "extensions were not introduced in the schema until version 1.1.",
            ],
            ["checked against a schema with no extensions"],
        ),
        (
            "tenders_releases_1_release_with_all_invalid_extensions.json",
            [
                "None of the extensions above could be applied",
                "extensions were not introduced in the schema until version 1.1.",
            ],
            ["Party Scale", "Get a copy of the schema with extension patches applied"],
        ),
        (
            "tenders_releases_2_releases_with_metatab_version_1_1_extensions.xlsx",
            [
                "Party Scale",
                "The metrics extension supports publication of forecasts",
                "All the extensions above were applied to extend the schema",
                "Get a copy of the schema with extension patches applied",
            ],
            [
                "The following extensions failed",
                "extensions were not introduced in the schema until version 1.1.",
            ],
        ),
    ],
)
def test_url_input_with_extensions(server_url, url_input_browser, httpserver, source_filename, expected, not_expected):
    browser = url_input_browser(source_filename)
    schema_extension_box = browser.find_element(By.ID, "schema-extensions").text

    for text in expected:
        assert text in schema_extension_box
    for text in not_expected:
        assert text not in schema_extension_box

    # Refresh page to check if tests still work after caching the data
    browser.get(browser.current_url)

    for text in expected:
        assert text in schema_extension_box
    for text in not_expected:
        assert text not in schema_extension_box


@pytest.mark.parametrize(
    ("source_filename", "expected", "not_expected"),
    [
        (
            "tenders_releases_1_release_with_extensions_1_1.json",
            ["This file applies 3 valid extensions to the schema"],
            ["Failed to apply"],
        ),
        (
            "tenders_releases_1_release_with_invalid_extensions.json",
            [
                "Failed to apply 3 extensions to the schema",
                "This file applies 3 valid extensions to the schema",
            ],
            [],
        ),
        (
            "tenders_releases_1_release_with_all_invalid_extensions.json",
            ["Failed to apply 3 extensions to the schema"],
            ["This file applies", "valid extensions to the schema"],
        ),
    ],
)
def test_url_input_extension_headlines(
    server_url, url_input_browser, httpserver, source_filename, expected, not_expected
):
    browser = url_input_browser(source_filename)
    headlines_box_text = browser.find_element(By.CLASS_NAME, "panel-body").text

    for text in expected:
        assert text in headlines_box_text
    for text in not_expected:
        assert text not in headlines_box_text


@pytest.mark.parametrize(
    ("source_filename", "expected", "not_expected"),
    [("tenders_releases_extra_data.json", ["uniquedata"], [])],
)
def test_ocds_show(server_url, url_input_browser, httpserver, source_filename, expected, not_expected):
    browser = url_input_browser(source_filename)

    browser.find_element(By.CSS_SELECTOR, "a[href='#extra']").click()

    body_text = browser.find_element(By.TAG_NAME, "body").text

    for text in expected:
        assert text in body_text
    for text in not_expected:
        assert text not in body_text


@pytest.mark.parametrize(
    ("source_filename", "expected", "not_expected"),
    [
        (
            "basic_release_empty_fields.json",
            [
                "Check Description",
                "Location of first 3 errors",
                "The data includes fields that are empty or contain only whitespaces. "
                "Fields that are not being used, or that have no value, "
                "should be excluded in their entirety (key and value) from the data",
                "releases/0/buyer/name",
                "releases/0/parties/0/address",
                "releases/0/planning/budget/id",
            ],
            "releases/0/tender/items/0/additionalClassifications",
        ),
    ],
)
def test_additional_checks_section(server_url, url_input_browser, httpserver, source_filename, expected, not_expected):
    browser = url_input_browser(source_filename)
    additional_checks_text = browser.find_element(By.ID, "additionalChecksTable").text

    for text in expected:
        assert text in additional_checks_text
    assert not_expected not in additional_checks_text


@pytest.mark.parametrize("source_filename", ["full_record.json"])
def test_additional_checks_section_not_being_displayed(server_url, url_input_browser, httpserver, source_filename):
    """Additional checks sections should only be displayed when there are results"""

    browser = url_input_browser(source_filename)
    additional_checks = browser.find_elements(By.ID, "additionalChecksTable")

    assert additional_checks == []


@pytest.mark.parametrize("source_filename", ["basic_release_empty_fields.json"])
def test_additional_checks_error_modal(server_url, url_input_browser, httpserver, source_filename):
    browser = url_input_browser(source_filename)
    browser.find_element(By.CSS_SELECTOR, 'a[data-target=".additional-checks-1"]').click()
    modal = browser.find_element(By.CSS_SELECTOR, ".additional-checks-1")
    modal_text = modal.text
    table_rows = browser.find_elements(By.CSS_SELECTOR, ".additional-checks-1 tbody tr")

    assert "Location" in modal_text
    assert "releases/0/tender/items/0/additionalClassifications" in modal_text
    assert len(table_rows) == 4

    browser.find_element(By.CSS_SELECTOR, "div.modal.additional-checks-1 button.close").click()


@pytest.fixture
def skip_if_remote():
    # If we're testing a remote server, then we can't run these tests, as we
    # can't make assumptions about what environment variables will be set
    if "CUSTOM_SERVER_URL" in os.environ:
        pytest.skip()


def test_releases_table_25_rows(skip_if_remote, url_input_browser):
    """
    Check that when there are more than 25 releases, only 25 are shown in the
    table, and there is a message.
    """

    browser = url_input_browser("30_releases.json")
    assert "This file contains 30 releases" in browser.find_element(By.TAG_NAME, "body").text
    panel = browser.find_element(By.CSS_SELECTOR, "#releases-table-panel")
    assert "first 25 releases" in panel.text
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#releases-table-panel table tbody tr")
    assert len(table_rows) == 25


def test_releases_table_7_rows(skip_if_remote, url_input_browser):
    """
    Check that when there are less than 25 releases, they are all shown in the
    table, and there is no message.
    """

    browser = url_input_browser("tenders_releases_7_releases_check_ocids.json")
    assert "This file contains 7 releases" in browser.find_element(By.TAG_NAME, "body").text
    panel = browser.find_element(By.CSS_SELECTOR, "#releases-table-panel")
    assert "first 25 releases" not in panel.text
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#releases-table-panel table tbody tr")
    assert len(table_rows) == 7


@pytest.fixture
def settings_releases_table_10(settings):
    # This needs to be in a fixture, to make sure its loaded before
    # url_input_browser
    settings.RELEASES_OR_RECORDS_TABLE_LENGTH = 10


def test_releases_table_10_rows_env_var(skip_if_remote, settings_releases_table_10, url_input_browser):
    """
    Check that when the appropriate setting is set, and there are more than 10
    releases, only 10 are shown in the table, and there is a message.
    """

    browser = url_input_browser("30_releases.json")
    assert "This file contains 30 releases" in browser.find_element(By.TAG_NAME, "body").text
    panel = browser.find_element(By.CSS_SELECTOR, "#releases-table-panel")
    assert "first 10 releases" in panel.text
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#releases-table-panel table tbody tr")
    assert len(table_rows) == 10


def test_releases_table_7_rows_env_var(skip_if_remote, settings_releases_table_10, url_input_browser):
    """
    Check that when the appropriate setting is set, and there are less than 10
    releases, they are all shown in the table, and there is no message.
    """

    browser = url_input_browser("tenders_releases_7_releases_check_ocids.json")
    assert "This file contains 7 releases" in browser.find_element(By.TAG_NAME, "body").text
    panel = browser.find_element(By.CSS_SELECTOR, "#releases-table-panel")
    assert "first 25 releases" not in panel.text
    assert "first 10 releases" not in panel.text
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#releases-table-panel table tbody tr")
    assert len(table_rows) == 7


def test_records_table_25_rows(skip_if_remote, url_input_browser):
    """
    Check that when there are more than 25 records, only 25 are shown in the
    table, and there is a message.
    """

    browser = url_input_browser("30_records.json")
    assert "This file contains 30 records" in browser.find_element(By.TAG_NAME, "body").text
    panel = browser.find_element(By.CSS_SELECTOR, "#records-table-panel")
    assert "first 25 records" in panel.text
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#records-table-panel table tbody tr")
    assert len(table_rows) == 25


def test_records_table_7_rows(skip_if_remote, url_input_browser):
    """
    Check that when there are less than 25 records, they are all shown in the
    table, and there is no message.
    """

    browser = url_input_browser("7_records.json")
    assert "This file contains 7 records" in browser.find_element(By.TAG_NAME, "body").text
    panel = browser.find_element(By.CSS_SELECTOR, "#records-table-panel")
    assert "first 25 records" not in panel.text
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#records-table-panel table tbody tr")
    assert len(table_rows) == 7


@pytest.fixture
def settings_records_table_10(settings):
    # This needs to be in a fixture, to make sure its loaded before
    # url_input_browser
    settings.RELEASES_OR_RECORDS_TABLE_LENGTH = 10


def test_records_table_10_rows_env_var(skip_if_remote, settings_records_table_10, url_input_browser):
    """
    Check that when the appropriate setting is set, and there are more than 10
    records, only 10 are shown in the table, and there is a message.
    """

    browser = url_input_browser("30_records.json")
    assert "This file contains 30 records" in browser.find_element(By.TAG_NAME, "body").text
    panel = browser.find_element(By.CSS_SELECTOR, "#records-table-panel")
    assert "first 10 records" in panel.text
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#records-table-panel table tbody tr")
    assert len(table_rows) == 10


def test_records_table_7_rows_env_var(skip_if_remote, settings_records_table_10, url_input_browser):
    """
    Check that when the appropriate setting is set, and there are less than 10
    records, they are all shown in the table, and there is no message.
    """

    browser = url_input_browser("7_records.json")
    assert "This file contains 7 records" in browser.find_element(By.TAG_NAME, "body").text
    panel = browser.find_element(By.CSS_SELECTOR, "#records-table-panel")
    assert "first 25 records" not in panel.text
    assert "first 10 records" not in panel.text
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#records-table-panel table tbody tr")
    assert len(table_rows) == 7


def test_error_list_1000_lines(skip_if_remote, url_input_browser):
    """
    Check that when there are more than 1000 error locations, only 1001 are
    shown in the table, and there is a message.
    """

    browser = url_input_browser("1001_empty_releases.json")
    assert "1001" in browser.find_element(By.TAG_NAME, "body").text
    browser.find_element(By.LINK_TEXT, "1001").click()
    modal_body = browser.find_element(By.CSS_SELECTOR, ".modal-body")
    assert "first 1000 locations for this error" in modal_body.text
    assert "releases/999" in modal_body.text
    assert "releases/1000" not in modal_body.text
    table_rows = modal_body.find_elements(By.CSS_SELECTOR, "table tbody tr")
    assert len(table_rows) == 1000


def test_error_list_999_lines(skip_if_remote, url_input_browser):
    """
    Check that when there are less than 1000 error locations, they are all shown
    in the table, and there is no message.
    """

    browser = url_input_browser("999_empty_releases.json")
    assert "999" in browser.find_element(By.TAG_NAME, "body").text
    browser.find_element(By.LINK_TEXT, "999").click()
    modal_body = browser.find_element(By.CSS_SELECTOR, ".modal-body")
    assert "first 999 locations for this error" not in modal_body.text
    assert "releases/998" in modal_body.text
    assert "releases/999" not in modal_body.text
    table_rows = modal_body.find_elements(By.CSS_SELECTOR, "table tbody tr")
    assert len(table_rows) == 999


@pytest.fixture
def settings_error_locations_sample(settings):
    # This needs to be in a fixture, to make sure its loaded before
    # url_input_browser
    settings.VALIDATION_ERROR_LOCATIONS_SAMPLE = True


def test_error_list_1000_lines_sample(skip_if_remote, settings_error_locations_sample, url_input_browser):
    """
    Check that when there are more than 1000 error locations, only 1001 are
    shown in the table, and there is a message.
    """

    browser = url_input_browser("1001_empty_releases.json")
    assert "1001" in browser.find_element(By.TAG_NAME, "body").text
    browser.find_element(By.LINK_TEXT, "1001").click()
    modal_body = browser.find_element(By.CSS_SELECTOR, ".modal-body")
    assert "random 1000 locations for this error" in modal_body.text
    table_rows = modal_body.find_elements(By.CSS_SELECTOR, "table tbody tr")
    assert len(table_rows) == 1000


def test_error_list_999_lines_sample(skip_if_remote, settings_error_locations_sample, url_input_browser):
    """
    Check that when there are less than 1000 error locations, they are all shown
    in the table, and there is no message.
    """

    browser = url_input_browser("999_empty_releases.json")
    assert "999" in browser.find_element(By.TAG_NAME, "body").text
    browser.find_element(By.LINK_TEXT, "999").click()
    modal_body = browser.find_element(By.CSS_SELECTOR, ".modal-body")
    assert "first 999 locations for this error" not in modal_body.text
    assert "releases/998" in modal_body.text
    assert "releases/999" not in modal_body.text
    table_rows = modal_body.find_elements(By.CSS_SELECTOR, "table tbody tr")
    assert len(table_rows) == 999


def test_records_table_releases_count(skip_if_remote, url_input_browser):
    """
    Check that the correct releases count is shown in the records table.
    """

    browser = url_input_browser("30_records.json")
    assert "release" in browser.find_elements(By.CSS_SELECTOR, "#records-table-panel table thead th")[1].text
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#records-table-panel table tbody tr")
    assert table_rows[0].find_elements(By.CSS_SELECTOR, "td")[1].text == "5"


@pytest.mark.parametrize(
    ("source_filename", "expected"),
    [
        (
            "release_aggregate.json",
            [
                "Unique OCIDs: 1",
                "Unique Item IDs: 2",
                "Currencies: EUR, GBP, USD, YEN",
            ],
        ),
    ],
)
def test_key_field_information(server_url, url_input_browser, httpserver, source_filename, expected):
    """Check that KFIs are displaying"""

    browser = url_input_browser(source_filename)
    kfi_text = browser.find_element(By.ID, "kfi").text
    for text in expected:
        assert text in kfi_text


def test_jsonschema_translation(
    url_input_browser,
):
    english_validation_messages = [
        "'a' does not match any of the regexes: 'okay'",
        '"a" is a dependency of "b"',
        '"a" is not a "email"',
        '"a" is not valid under any of the given schemas',
        '"a" is not valid under any of the given schemas',
        '"a" is too short',
        '"aaa" is too long',
        "1 is less than the minimum of 2",
        "1 is valid under each of {'type': 'integer'}, {'type': 'number'}",
        "2 is more than or equal to the maximum of 2",
        "2 is less than or equal to the minimum of 2",
        "2 is not a multiple of 3",
        "3 is more than the maximum of 2",
        "Additional items are not allowed (['a'] was unexpected)",
        "Additional properties are not allowed (['a'] was unexpected)",
        '{"a": 1, "b": 2, "c": 3} has too many properties',
        '["a", "a", "a"] is too long',
        '["a"] is too short',
        '"a" is not valid under any of the given schemas',
        '{"type": "string"} is not allowed for "a"',
    ]

    spanish_validation_messages = [
        "'a' no coincide con ninguna de las expresiones regulares: 'okay'",
        '"a"es una dependencia de "b"',
        '"a" no es un "email"',
        '"a" no es válido bajo ninguno de los esquemas dados',
        '"a" no es válido bajo ninguno de los esquemas dados',
        '"a"es muy corto',
        '"aaa"es muy largo',
        "1 es menor que el mínimo de 2",
        "1es válido bajo cada uno de {'type': 'integer'}, {'type': 'number'}",
        "2es mayor o igual que el máximo de 2",
        "2 es menor o igual que el mínimo de 2",
        "2 no es un múltiplo de 3",
        "3 es mayor que el máximo de 2",
        "Items adicionales no están permitidos (['a'] fue inesperado)",
        "Propiedades adicionales no están permitidas (['a'] fue inesperado )",
        '{"a": 1, "b": 2, "c": 3} tiene demasiadas propiedades',
        '["a", "a", "a"]es muy largo',
        '["a"]es muy corto',
        '"a" no es válido bajo ninguno de los esquemas dados',
        '{"type": "string"} no está permitido para "a"',
    ]

    source_filename = "extended_many_jsonschema_keys.json"
    browser = url_input_browser(source_filename)

    # Ensure language is English
    browser.find_elements(By.XPATH, "//*[contains(text(), 'español')]")[0].click()
    browser.find_elements(By.XPATH, "//*[contains(text(), 'English')]")[0].click()

    body_text = browser.find_element(By.TAG_NAME, "body").text

    for message in english_validation_messages:
        assert message in body_text

    browser.find_elements(By.XPATH, "//*[contains(text(), 'English')]")[0].click()
    browser.find_elements(By.XPATH, "//*[contains(text(), 'español')]")[0].click()
    body_text = browser.find_element(By.TAG_NAME, "body").text

    for message in english_validation_messages:
        assert message not in body_text

    for message in spanish_validation_messages:
        assert message in body_text


def test_jsonschema_translation_2(
    url_input_browser,
):
    english_validation_messages = [
        "id is missing but required within tender",
        "initiationType is missing but required",
        "version does not match the regex ^(\\d+\\.)(\\d+)$",
        "amount is not a number. Check that the value doesn’t contain any characters other than 0-9 and dot (.). Number values should not be in quotes.",  # noqa: E501
        "buyer is not a JSON object",
        "numberOfTenderers is not a integer. Check that the value doesn’t contain decimal points or any characters other than 0-9. Integer values should not be in quotes.",  # noqa: E501
        "ocid is not a string. Check that the value is not null, and has quotes at the start and end. Escape any quotes in the value with \\",  # noqa: E501
        "parties is not a JSON array",
        "title is not a string. Check that the value has quotes at the start and end. Escape any quotes in the value with \\",  # noqa: E501
        "Incorrect date format. Dates should use the form YYYY-MM-DDT00:00:00Z. Learn more about dates in OCDS.",
        "Invalid 'uri' found",
        '"" is too short. Strings must be at least one character. This error typically indicates a missing value.',
        "Invalid code found in currency",
        "[] is too short. You must supply at least one value, or remove the item entirely (unless it’s required).",
    ]

    spanish_validation_messages = [
        "id falta pero se requiere dentro de tender",
        "initiationTypefalta pero se requiere",
        "versionno coincide con la expresión regular ^(\\d+\\.)(\\d+)$",
        "amountno es un número. Compruebe que el valor no contenga ningún carácter más que 0-9 y el punto (.). Los valores numéricos no deben estar entre comillas",  # noqa: E501
        "buyer no es un objeto JSON.",
        "numberOfTenderers no es un entero. Compruebe que el valor no contenga puntos decimales ni ningún otro carácter que no sea 0-9. Los valores enteros no deben estar entre comillas.",  # noqa: E501
        "ocid no es un hilo. Revise que el valor no es 'null', y tenga comillas al principio y al final. Escapa de cualquier comillas con el valor \\",  # noqa: E501
        "parties no es una matriz JSON",
        "title no es un hilo. Revise que el valor tenga comillas al principio y al final. Escapa de cualquier comillas con el valor \\",  # noqa: E501
        "Formato de fecha inválido. Las fechas deben usar el formato YYYY-MM-DDT00:00:00Z. Lea más sobre fechas en OCDS",  # noqa: E501
        "Se ha encontrado una 'uri' inválida",
        '""es muy corto. Las cadenas deben ser de al menos un caracter. Este error generalmente indica que hay un valor faltante.',  # noqa: E501
        "Código inválido encontrado en currency",
        "[]es muy corto. Debe proporcionar al menos un valor o eliminar el artículo por completo (a menos que sea necesario)",  # noqa: E501
    ]

    source_filename = "badfile_all_validation_errors.json"
    browser = url_input_browser(source_filename)

    # Ensure language is English
    browser.find_elements(By.XPATH, "//*[contains(text(), 'español')]")[0].click()
    browser.find_elements(By.XPATH, "//*[contains(text(), 'English')]")[0].click()

    body_text = browser.find_element(By.TAG_NAME, "body").text

    for message in english_validation_messages:
        assert message in body_text

    browser.find_elements(By.XPATH, "//*[contains(text(), 'English')]")[0].click()
    browser.find_elements(By.XPATH, "//*[contains(text(), 'español')]")[0].click()
    body_text = browser.find_element(By.TAG_NAME, "body").text

    for message in english_validation_messages:
        assert message not in body_text

    for message in spanish_validation_messages:
        assert message in body_text
