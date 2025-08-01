import os
from pathlib import Path
from urllib.parse import urlsplit

import flattentool
import lxml.etree
import lxml.html
import pytest
import requests
from django.test import override_settings

from tests import DEFAULT_SCHEMA_VERSION, REMOTE, SCHEMA_VERSION_CHOICES, WHITESPACE, assert_in, setup_agent

SCHEMA_VERSIONS_DISPLAY = [display for (display, _, _) in SCHEMA_VERSION_CHOICES.values()]


class MockResponse:
    def __init__(self, content, path_info):
        self.content = content
        self.status_code = 200
        self.request = {"PATH_INFO": path_info}


def make_request(client, method, server_url, path, data=None):
    if REMOTE:  # client.post() would 404
        if method == "GET":
            return requests.get(f"{server_url}{path}")

        with setup_agent() as page:
            page.goto(f"{server_url}{path}")
            if method == "POST":  # Callers only use "POST" to submit this form
                page.click('button[name="flatten"]')

            page.wait_for_load_state("networkidle")
            content = page.content().encode()
            path_info = urlsplit(page.url).path

        return MockResponse(content, path_info)

    return getattr(client, method.lower())(path, data)


def submit_file(client, filename):
    path = Path("tests") / "fixtures" / filename

    if REMOTE:  # client.post() would 404
        with setup_agent() as page:
            page.goto(os.environ["CUSTOM_SERVER_URL"])
            page.click("text=Upload")
            page.locator('input[name="original_file"]').set_input_files(str(path))
            page.click('form[enctype] button[type="submit"]')

            page.wait_for_load_state("networkidle")
            content = page.content().encode()
            path_info = urlsplit(page.url).path

        return MockResponse(content, path_info)

    with path.open("rb") as f:
        response = client.post("/", {"original_file": f, "csrfmiddlewaretoken": ""})

    assert response.status_code == 302

    response = client.get(response.url)

    assert response.status_code == 200

    return response


@pytest.mark.parametrize(
    ("filename", "expected", "not_expected", "conversion_successful"),
    [
        (
            "tenders_releases_2_releases.json",
            ["Convert", "Schema", "OCDS release package schema version 1.0. You can", *SCHEMA_VERSIONS_DISPLAY],
            ["Schema Extensions"],
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
                "Organization scale",
            ],
            ["/releases/parties/details", "fetching failed"],
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
            ["Organization scale"],
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
                "Organization scale",
                "The metrics extension supports publication of forecasts",
                "Get a copy of the schema with extension patches applied",
                "The following extensions failed",
                "Codelist Errors",
                "records/compiledRelease/parties/details",
                "mooo",
                "/records/compiledRelease/tender/targets",
                "The schema version specified in the file is 1.1",
                "/records/releases/tender/targets",
            ],
            ["checked against a schema with no extensions"],
            False,  # context["conversion"] is set to False for record packages
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
            ["We found 6 objects within arrays in your data without an id property", "Structure Warnings"],
            [],
            True,
        ),
        (
            "tenders_releases_7_releases_check_ocids.json",
            ["Conformance (Rules)", "6 of your ocid fields have a problem"],
            [],
            True,
        ),
        ("ocds_release_nulls.json", ["Convert", "Save or Share these results"], [], True),
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
                "Codelist Errors",
                "releases/tender/value",
                "badCurrencyCode",
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
                "The date when the bid or expression of interest was received.",
                "A local identifier for the bid or expression of interest.",
                "Summary statistics about the number of bidders, bids and expressions of interest.",
            ],
            ["Reference Docs"],
            True,
        ),
        # Conversion should still work for files that don't validate against the schema.
        (
            "tenders_releases_2_releases_invalid.json",
            ["Convert", "Structural Errors", "id is missing but required", "Invalid 'uri' found"],
            [],
            True,
        ),
        ("tenders_releases_2_releases_codelists.json", ["oh no", "GSINS"], [], True),
        ("utf8.json", ["Convert"], ["Ensure that your file uses UTF-8 encoding"], True),
        ("latin1.json", ["Ensure that your file uses UTF-8 encoding"], [], False),  # invalid encoding
        ("utf-16.json", ["Ensure that your file uses UTF-8 encoding"], [], False),  # invalid encoding
        ("tenders_releases_2_releases_not_json.json", ["not well formed JSON"], [], False),  # invalid JSON
        ("non_dict_json.json", [], ["could not be converted"], True),
        (
            "full_record.json",
            ["Number of records", "Structural Errors", "compiledRelease", "versionedRelease"],
            [],
            False,  # context["conversion"] is set to False for record packages
        ),
        # Test "version" value in data.
        (
            "tenders_releases_1_release_with_unrecognized_version.json",
            [
                "Your data specifies a version 123.123 which is not recognised",
                f"checked against OCDS release package schema version {DEFAULT_SCHEMA_VERSION}. You can",
                "checked against the current default version.",
                "Convert to Spreadsheet",
            ],
            ["Additional Fields (fields in data not in schema)", "Error message"],
            None,  # Skip conversion (the unrecognized_version_data alert is not displayed after conversion).
        ),
        (
            "tenders_releases_1_release_with_wrong_version_type.json",
            [
                "Your data specifies a version 1000 (it must be a string) which is not recognised",
                f"checked against OCDS release package schema version {DEFAULT_SCHEMA_VERSION}. You can",
                "Convert to Spreadsheet",
            ],
            ["Additional Fields (fields in data not in schema)", "Error message"],
            None,  # Skip conversion (the unrecognized_version_data alert is not displayed after conversion).
        ),
        (
            "tenders_releases_1_release_with_patch_in_version.json",
            [
                '"version" field in your data follows the major.minor.patch pattern',
                "100.100.0 format does not comply with the schema",
                "Error message",
            ],
            ["Convert to Spreadsheet"],
            False,  # Invalid version
        ),
        (
            "bad_toplevel_list.json",
            ["OCDS JSON should have an object as the top level, the JSON you supplied does not."],
            [],
            False,  # Invalid type
        ),
        (
            "tenders_releases_1_release_with_extension_broken_json_ref.json",
            ["JSON reference error", "Unresolvable JSON pointer:", "/definitions/OrganizationReference"],
            ["Convert to Spreadsheet"],
            False,  # Invalid reference
        ),
        (
            "tenders_releases_1_release_unpackaged.json",
            ["Missing OCDS package", "Error message: Missing OCDS package"],
            ["Convert to Spreadsheet"],
            False,  # Invalid package
        ),
        (
            "tenders_releases_1_release_with_closed_codelist.json",
            ["Failed structural checks"],
            ["Passed structural checks"],
            True,
        ),
        (
            "tenders_releases_1_release_with_tariff_codelist.json",
            ["releases/contracts/tariffs", "chargePaidBy.csv", "notADocumentType", "notAPaidByCodelist"],
            ["notADocumentType, tariffIllustration"],
            True,
        ),
        (
            "tenders_releases_1_release_with_various_codelists.json",
            [
                "needsAssessment, notADocumentType",
                "-documentType.csv: References non-existing code(s): notACodelistValueAtAll",
                "+method.csv: Has non-UTF-8 characters",
                "chargePaidBy.csv",
                "notAPaidByCodelist",
            ],
            ['Has no "Code" column'],
            True,
        ),
        (
            "tenders_releases_2_releases.xlsx",
            ["Convert", "Schema", *SCHEMA_VERSIONS_DISPLAY],
            ["Missing OCDS package"],
            True,
        ),
    ],
)
@pytest.mark.django_db
def test_url_input(server_url, client, filename, expected, not_expected, conversion_successful):
    excel = filename.endswith(".xlsx")

    response = submit_file(client, filename)

    if conversion_successful and not excel:
        response = make_request(client, "POST", server_url, response.request["PATH_INFO"], {"flatten": "true"})

    responses = [response]

    # Do this additional test for only one case, to speed up tests.
    if filename == "tenders_releases_2_releases_invalid.json":
        responses.append(make_request(client, "GET", server_url, response.request["PATH_INFO"]))

    for response in responses:
        assert response.status_code == 200

        document = lxml.html.fromstring(response.content)
        for script in document.xpath("//script"):
            script.getparent().remove(script)
        text = WHITESPACE.sub(" ", document.text_content())

        assert "Data Review Tool" in text
        assert "Load New File" in text or "Try Again" in text
        if conversion_successful is None:
            assert "Convert to Spreadsheet" in text
        else:
            assert "Convert to Spreadsheet" not in text  # the button isn't present after clicking
        for value in expected:
            assert value in text
        for value in not_expected:
            assert value not in text

        if conversion_successful:
            links = document.xpath("//div[contains(@class, 'conversion')]//a")

            file = links[0]
            path = file.attrib["href"]

            if REMOTE:
                static_file = requests.get(f"{server_url}{path}")

                assert static_file.status_code == 200
                assert int(static_file.headers["content-length"]) > 0

            assert not file.getnext().text_content().startswith("0")
            assert filename in path
            assert file.text_content().strip() == f"{'Excel Spreadsheet (.xlsx)' if excel else 'JSON'} (Original)"

            file = links[1]
            path = file.attrib["href"]

            if REMOTE:
                static_file = requests.get(f"{server_url}{path}")

                assert static_file.status_code == 200
                assert int(static_file.headers["content-length"]) > 0

            assert not file.getnext().text_content().startswith("0")
            assert "unflattened.json" if excel else "flattened.xlsx" in path
            assert file.text_content().startswith(
                f"{'JSON' if excel else 'Excel Spreadsheet (.xlsx)'} " "(Converted from Original using schema version "
            )


@pytest.mark.django_db
def test_validation_error_messages(client):
    content = submit_file(client, "badfile_all_validation_errors.json").content

    for value in (
        b"<code>&quot;&quot;</code> is too short",
        b"<code>version</code> does not match the regex <code>^(\\d+\\.)(\\d+)$</code>",
        b"<code>id</code> is missing but required within <code>tender</code>",
        b"<code>initiationType</code> is missing but required",
        b'Incorrect date format. Dates should use the form YYYY-MM-DDT00:00:00Z. Learn more about <a href="https://standard.open-contracting.org/latest/en/schema/reference/#date">dates in OCDS</a>.',  # noqa: E501
        b"<code>numberOfTenderers</code> is not a integer",
        b"<code>amount</code> is not a number. Check that the value  doesn\xe2\x80\x99t contain any characters other than 0-9 and dot (<code>.</code>).",  # noqa: E501
        b"<code>ocid</code> is not a string. Check that the value is not null, and has quotes at the start and end. Escape any quotes in the value with <code>\\</code>",  # noqa: E501
        b'For more information see the <a href="https://standard.open-contracting.org/1.1/en/schema/identifiers/">Open Contracting Identifier guidance</a>',  # noqa: E501
        b"<code>title</code> is not a string. Check that the value  has quotes at the start and end. Escape any quotes in the value with <code>\\</code>",  # noqa: E501
        b"<code>parties</code> is not a JSON array",
        b"<code>buyer</code> is not a JSON object",
        b"<code>[]</code> is too short.",
        b'One or more values from the closed <a href="https://standard.open-contracting.org/1.1/en/schema/codelists/#release-tag">releaseTag</a> codelist',  # noqa: E501
    ):
        assert value in content


@pytest.mark.django_db
def test_extension_validation_error_messages(client):
    content = submit_file(client, "badfile_extension_validation_errors.json").content

    for value in (
        b"&lt;script&gt;alert('badscript');&lt;/script&gt;",
        b"<a>test</a>",
    ):
        assert value in content

    for value in (
        b"<script>alert('badscript');</script>",
        b"badlink",  # <a href="javascript:alert('badlink')">test</a>
    ):
        assert value not in content


@pytest.mark.parametrize("uuid", ["0", "324ea8eb-f080-43ce-a8c1-9f47b28162f3"])
@pytest.mark.django_db
def test_url_invalid_dataset_request(server_url, client, uuid):
    response = make_request(client, "GET", server_url, f"/data/{uuid}")

    assert response.status_code == 404
    assert b"We don&#x27;t seem to be able to find the data you requested" in response.content


@pytest.mark.parametrize(
    ("filename", "expected", "not_expected", "expected_additional_field", "not_expected_additional_field"),
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
            "✅",  # skip this assertion
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
@pytest.mark.django_db
def test_url_input_with_version(
    server_url, client, filename, expected, not_expected, expected_additional_field, not_expected_additional_field
):
    response = submit_file(client, filename)
    document = lxml.html.fromstring(response.content)
    text = document.text_content()
    additional_field_box = document.cssselect("#additionalFieldTable")[0].text_content()

    assert expected in text
    assert not_expected not in text
    assert expected_additional_field in additional_field_box
    assert not_expected_additional_field not in additional_field_box

    # Refresh page to check if tests still work after caching the data
    response = make_request(client, "GET", server_url, response.request["PATH_INFO"])
    document = lxml.html.fromstring(response.content)
    text = document.text_content()
    additional_field_box = document.cssselect("#additionalFieldTable")[0].text_content()

    assert expected in text
    assert not_expected not in text
    assert expected_additional_field in additional_field_box
    assert not_expected_additional_field not in additional_field_box


@pytest.mark.parametrize(
    ("filename", "expected", "not_expected"),
    [
        (
            "tenders_releases_1_release_with_extensions_1_1.json",
            [
                "Organization scale",
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
                "Organization scale",
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
            ["Organization scale", "Get a copy of the schema with extension patches applied"],
        ),
        (
            "tenders_releases_2_releases_with_metatab_version_1_1_extensions.xlsx",
            [
                "Organization scale",
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
@pytest.mark.django_db
def test_url_input_with_extensions(server_url, client, filename, expected, not_expected):
    response = submit_file(client, filename)
    document = lxml.html.fromstring(response.content)
    schema_extension_box = document.cssselect("#schema-extensions")[0].text_content()

    for text in expected:
        assert text in schema_extension_box
    for text in not_expected:
        assert text not in schema_extension_box

    # Refresh page to check if tests still work after caching the data
    response = make_request(client, "GET", server_url, response.request["PATH_INFO"])
    document = lxml.html.fromstring(response.content)
    schema_extension_box = document.cssselect("#schema-extensions")[0].text_content()

    for text in expected:
        assert text in schema_extension_box
    for text in not_expected:
        assert text not in schema_extension_box


@pytest.mark.parametrize("flatten_or_unflatten", ["flatten", "unflatten"])
@pytest.mark.django_db
@pytest.mark.skipif(REMOTE, reason="Uses mocks")
def test_flattentool_warnings(monkeypatch, server_url, client, flatten_or_unflatten):
    def mockflatten(input_name, output_name, *args, **kwargs):
        with open(f"{output_name}.xlsx", "w") as f:
            f.write("{}")

    def mockunflatten(input_name, output_name, *args, **kwargs):
        with open(kwargs["cell_source_map"], "w") as f:
            f.write("{}")
        with open(kwargs["heading_source_map"], "w") as f:
            f.write("{}")
        with open(output_name, "w") as f:
            f.write("{}")

    monkeypatch.setattr(
        flattentool, flatten_or_unflatten, mockflatten if flatten_or_unflatten == "flatten" else mockunflatten
    )

    # Actual input file doesn't matter, as we override flattentool behavior with a mock below.
    filename = f"tenders_releases_2_releases.{'json' if flatten_or_unflatten == 'flatten' else 'xlsx'}"

    response = submit_file(client, filename)
    if flatten_or_unflatten == "flatten":
        response = make_request(client, "POST", server_url, response.request["PATH_INFO"], {"flatten": "true"})
    document = lxml.html.fromstring(response.content)
    text = document.text_content()

    assert "conversion Errors" not in text
    assert "Conversion Warnings" not in text


@pytest.mark.parametrize(
    ("filename", "expected", "not_expected"),
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
@pytest.mark.django_db
def test_url_input_extension_headlines(client, filename, expected, not_expected):
    response = submit_file(client, filename)

    assert_in(lxml.html.fromstring(response.content).cssselect(".message"), expected, not_expected)


@pytest.mark.django_db
def test_additional_checks_section(client):
    response = submit_file(client, "basic_release_empty_fields.json")
    element = lxml.html.fromstring(response.content).cssselect("#additionalChecksTable")[0]
    element_text = element.text_content()

    for text in (
        "Check Description",
        "Location of first 3 errors",
        "The data includes fields that are empty or contain only whitespaces. "
        "Fields that are not being used, or that have no value, "
        "should be excluded in their entirety (key and value) from the data",
        "releases/0/buyer/name",
        "releases/0/parties/0/address",
        "releases/0/planning/budget/id",
        "releases/0/tender/items/0/additionalClassifications",
    ):
        assert text in element_text
    # This appears in the "see all" modal.
    assert not any(
        "releases/0/tender/items/0/additionalClassifications" in li.text_content() for li in element.cssselect("li")
    )


@pytest.mark.django_db
def test_additional_checks_section_not_being_displayed(client):
    response = submit_file(client, "full_record.json")

    assert lxml.html.fromstring(response.content).cssselect("#additionalChecksTable") == []


@pytest.mark.parametrize(
    ("filename", "total", "items", "subtotal"),
    [
        ("30_releases.json", 30, "releases", 25),
        ("tenders_releases_7_releases_check_ocids.json", 7, "releases", 7),
        ("30_records.json", 30, "records", 25),
        ("7_records.json", 7, "records", 7),
    ],
)
@pytest.mark.django_db
@pytest.mark.skipif(REMOTE, reason="Depends on RELEASES_OR_RECORDS_TABLE_LENGTH = 25 (default)")
def test_table_rows(client, filename, total, items, subtotal):
    response = submit_file(client, filename)

    document = lxml.html.fromstring(response.content)
    panel = document.cssselect(f"#{items}-table-panel")[0].text_content()

    assert f"This file contains {total} {items}" in document.cssselect(".key-facts ul li")[0].text_content()
    assert "first" not in panel if total <= subtotal else f"first 25 {items}" in panel
    assert len(document.cssselect(f"#{items}-table-panel table tbody tr")) == subtotal


@pytest.mark.parametrize(
    ("filename", "total", "items", "subtotal"),
    [
        ("30_releases.json", 30, "releases", 10),
        ("tenders_releases_7_releases_check_ocids.json", 7, "releases", 7),
        ("30_records.json", 30, "records", 10),
        ("7_records.json", 7, "records", 7),
    ],
)
@pytest.mark.django_db
@override_settings(RELEASES_OR_RECORDS_TABLE_LENGTH=10)
@pytest.mark.skipif(REMOTE, reason="Depends on RELEASES_OR_RECORDS_TABLE_LENGTH = 10")
def test_table_rows_settings(client, filename, total, items, subtotal):
    response = submit_file(client, filename)

    document = lxml.html.fromstring(response.content)
    panel = document.cssselect(f"#{items}-table-panel")[0].text_content()

    assert f"This file contains {total} {items}" in document.cssselect(".key-facts ul li")[0].text_content()
    assert "first" not in panel if total <= subtotal else f"first 10 {items}" in panel
    assert len(document.cssselect(f"#{items}-table-panel table tbody tr")) == subtotal


@pytest.mark.django_db
def test_records_table_releases_count(client):
    response = submit_file(client, "30_records.json")

    document = lxml.html.fromstring(response.content)

    assert "release" in document.cssselect("#records-table-panel table thead th")[1].text_content()
    assert document.cssselect("#records-table-panel table tbody tr")[0].cssselect("td")[1].text_content() == "5"
