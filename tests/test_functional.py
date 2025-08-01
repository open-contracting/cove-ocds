import flattentool
import pytest
from django.test import override_settings

from tests import OCDS_SCHEMA_VERSIONS_DISPLAY, assert_in

WAIT = 350


@pytest.mark.django_db
def test_accordion(server_url, page):
    page.goto(server_url)

    for click, index in (
        ("", 0),
        ("text=Upload", 1),
        ("text=Paste", 2),
        ("#headingOne", 0),
        ("#headingTwo", 1),
        ("#headingThree", 2),
    ):
        if click:
            page.click(click)
            page.wait_for_timeout(WAIT)

        for i, button in enumerate(page.locator("button").all()):
            assert button.is_visible() == (index == i)


@pytest.mark.django_db
def test_500_error(server_url, page):
    page.goto(f"{server_url}/test/500")
    icon = page.locator(".panel-danger span").first

    # Check that our nice error message is there.
    assert "Something went wrong" in page.text_content("body")
    # Check for the exclamation icon. This helps to check that the theme including the css has been loaded properly.
    assert "Glyphicons Halflings" in icon.evaluate("element => getComputedStyle(element).fontFamily")
    assert icon.evaluate("element => getComputedStyle(element).color") in "rgb(255, 255, 255)"


@pytest.mark.parametrize(
    ("filename", "expected_text", "not_expected_text", "conversion_successful"),
    [
        (
            "tenders_releases_2_releases.xlsx",
            ["Convert", "Schema", *OCDS_SCHEMA_VERSIONS_DISPLAY],
            ["Missing OCDS package"],
            True,
        ),
    ],
)
def test_url_input(
    server_url,
    submit_url,
    httpserver,
    filename,
    expected_text,
    not_expected_text,
    conversion_successful,
):
    page = submit_url(filename)
    text = page.text_content("body")

    assert "Data Review Tool" in text
    assert "Load New File" in text
    for value in expected_text:
        assert value in text
    for value in not_expected_text:
        assert value not in text

    if conversion_successful:
        links = page.locator("div.conversion a")

        # Original
        file = links.nth(0)

        assert not file.locator("xpath=following-sibling::*[1]").text_content().startswith("0")
        assert filename in file.get_attribute("href")
        assert file.text_content().strip() == "Excel Spreadsheet (.xlsx) (Original)"

        with page.expect_download() as download_info:
            file.click()
        download = download_info.value

        assert download.failure() is None
        assert download.path().stat().st_size > 0

        # Converted
        file = links.nth(1)

        assert not file.locator("xpath=following-sibling::*[1]").text_content().startswith("0")
        assert "unflattened.json" in file.get_attribute("href")
        assert file.text_content().startswith("JSON (Converted from Original using schema version ")

        # JSON files are rendered, not downloaded.
        file.click()

        assert page.url.endswith("unflattened.json")
        assert '"releases"' in page.text_content("body")


DARK_RED = "rgb(169, 68, 66)"
DARK_GREEN = "rgb(155, 175, 0)"


@pytest.mark.parametrize(
    ("filename", "heading_color"),
    [
        ("tenders_releases_2_releases.json", DARK_GREEN),
        ("record_minimal_valid.json", DARK_GREEN),
        # Not valid against the schema
        ("tenders_releases_2_releases_invalid.json", DARK_RED),
        ("full_record.json", DARK_RED),
        # Disallowed values on closed codelists
        ("tenders_releases_1_release_with_closed_codelist.json", DARK_RED),
        # Bad extensions
        ("tenders_releases_1_release_with_all_invalid_extensions.json", DARK_RED),
        ("tenders_records_1_record_with_invalid_extensions.json", DARK_RED),
    ],
)
def test_headlines_class(submit_url, filename, heading_color):
    page = submit_url(filename)
    headlines = page.locator(".panel").first

    # Check this is the headlines panel.
    assert headlines.text_content().strip().startswith("Headlines")
    assert (
        headlines.locator(".panel-heading").first.evaluate("element => getComputedStyle(element).backgroundColor")
        == heading_color
    )


# Skip if remote, as we can't set up the mocks.
@pytest.mark.parametrize("flatten_or_unflatten", ["flatten", "unflatten"])
def test_flattentool_warnings(skip_if_remote, submit_url, httpserver, monkeypatch, flatten_or_unflatten):
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

    page = submit_url(filename)
    if flatten_or_unflatten == "flatten":
        page.click('button[name="flatten"]')
    text = page.text_content("body")

    assert "conversion Errors" not in text
    assert "Conversion Warnings" not in text


@pytest.mark.parametrize(
    (
        "filename",
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
            "",  # skip this assertion
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
    submit_url,
    httpserver,
    select_version,
    filename,
    expected,
    not_expected,
    expected_additional_field,
    not_expected_additional_field,
):
    page = submit_url(filename)
    page.select_option('select[name="version"]', select_version)
    page.click('.btn-primary[value="Go"]')

    text = page.text_content("body")
    additional_field_box = page.text_content("#additionalFieldTable")

    assert expected in text
    assert not_expected not in text
    assert expected_additional_field in additional_field_box
    assert not_expected_additional_field not in additional_field_box

    # Refresh page to check if tests still work after caching the data
    page.reload()

    text = page.text_content("body")
    additional_field_box = page.text_content("#additionalFieldTable")

    assert expected in text
    assert not_expected not in text
    assert expected_additional_field in additional_field_box
    assert not_expected_additional_field not in additional_field_box


@pytest.mark.parametrize(
    ("filename", "expected", "not_expected"),
    [("tenders_releases_extra_data.json", ["uniquedata"], [])],
)
def test_ocds_show(submit_url, httpserver, filename, expected, not_expected):
    page = submit_url(filename)
    page.click("a[href='#extra']")
    text = page.text_content("body")

    for value in expected:
        assert value in text
    for value in not_expected:
        assert value not in text


@pytest.mark.parametrize("filename", ["basic_release_empty_fields.json"])
def test_additional_checks_error_modal(submit_url, httpserver, filename):
    page = submit_url(filename)
    page.click('a[data-target=".additional-checks-1"]')
    modal_text = page.locator(".additional-checks-1").text_content()

    assert "Location" in modal_text
    assert "releases/0/tender/items/0/additionalClassifications" in modal_text
    assert page.locator(".additional-checks-1 tbody tr").count() == 4

    page.click("div.modal.additional-checks-1 button.close")


@override_settings(VALIDATION_ERROR_LOCATIONS_LENGTH=1000)
def test_error_list_1000_lines(skip_if_remote, submit_url):
    """
    When there are more than 1000 error locations, the first 1000 are shown in the table, and there is a message.
    """
    page = submit_url("1001_empty_releases.json")

    assert "1001" in page.text_content(".key-facts ul li")

    page.click("text=1001")
    modal_body = page.locator(".modal-body").first
    modal_text = modal_body.text_content()

    assert modal_body.locator("table tbody tr").count() == 1000
    assert "first 1000 locations for this error" in modal_text
    assert "releases/999" in modal_text
    assert "releases/1000" not in modal_text


@override_settings(VALIDATION_ERROR_LOCATIONS_LENGTH=1000)
def test_error_list_999_lines(skip_if_remote, submit_url):
    """
    When there are less than 1000 error locations, they are all shown in the table, and there is no message.
    """
    page = submit_url("999_empty_releases.json")

    assert "999" in page.text_content(".key-facts ul li")

    page.click("text=999")
    modal_body = page.locator(".modal-body").first
    modal_text = modal_body.text_content()

    assert modal_body.locator("table tbody tr").count() == 999
    assert "first 999 locations for this error" not in modal_text
    assert "releases/998" in modal_text
    assert "releases/999" not in modal_text


@override_settings(VALIDATION_ERROR_LOCATIONS_LENGTH=1000, VALIDATION_ERROR_LOCATIONS_SAMPLE=True)
def test_error_list_1000_lines_sample(skip_if_remote, submit_url):
    """
    When there are more than 1000 error locations, a random 1000 are shown in the table, and there is a message.
    """
    page = submit_url("1001_empty_releases.json")

    assert "1001" in page.text_content(".key-facts ul li")

    page.click("text=1001")
    modal_body = page.locator(".modal-body").first
    modal_text = modal_body.text_content()

    assert modal_body.locator("table tbody tr").count() == 1000
    assert "random 1000 locations for this error" in modal_text


@override_settings(VALIDATION_ERROR_LOCATIONS_LENGTH=1000, VALIDATION_ERROR_LOCATIONS_SAMPLE=True)
def test_error_list_999_lines_sample(skip_if_remote, submit_url):
    """
    When there are less than 1000 error locations, they are all shown in the table, and there is no message.
    """
    page = submit_url("999_empty_releases.json")

    assert "999" in page.text_content(".key-facts ul li")

    page.click("text=999")
    modal_body = page.locator(".modal-body").first
    modal_text = modal_body.text_content()

    assert modal_body.locator("table tbody tr").count() == 999
    assert "first 999 locations for this error" not in modal_text
    assert "releases/998" in modal_text
    assert "releases/999" not in modal_text


@pytest.mark.parametrize(
    ("filename", "english", "spanish"),
    [
        (
            "extended_many_jsonschema_keys.json",
            [
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
            ],
            [
                "'a' no coincide con ninguna de las expresiones regulares: 'okay'",
                '"a" es una dependencia de "b"',
                '"a" no es un "email"',
                '"a" no es válido bajo ninguno de los esquemas dados',
                '"a" no es válido bajo ninguno de los esquemas dados',
                '"a" es muy corto',
                '"aaa" es muy largo',
                "1 es menor que el mínimo de 2",
                "1 es válido bajo cada uno de {'type': 'integer'}, {'type': 'number'}",
                "2 es mayor o igual que el máximo de 2",
                "2 es menor o igual que el mínimo de 2",
                "2 no es un múltiplo de 3",
                "3 es mayor que el máximo de 2",
                "Items adicionales no están permitidos (['a'] fue inesperado)",
                "Propiedades adicionales no están permitidas (['a'] fue inesperado)",
                '{"a": 1, "b": 2, "c": 3} tiene demasiadas propiedades',
                '["a", "a", "a"] es muy largo',
                '["a"] es muy corto',
                '"a" no es válido bajo ninguno de los esquemas dados',
                '{"type": "string"} no está permitido para "a"',
            ],
        ),
        (
            "badfile_all_validation_errors.json",
            [
                "id is missing but required within tender",
                "initiationType is missing but required",
                "version does not match the regex ^(\\d+\\.)(\\d+)$",
                "amount is not a number. Check that the value doesn’t contain any characters other than 0-9 and dot (.). Number values should not be in quotes.",  # noqa: E501
                "buyer is not a JSON object",
                "numberOfTenderers is not a integer. Check that the value doesn’t contain decimal points or any characters other than 0-9. Integer values should not be in quotes.",  # noqa: E501
                "ocid is not a string. Check that the value is not null, and has quotes at the start and end. Escape any quotes in the value with \\",  # noqa: E501
                "parties is not a JSON array",
                "title is not a string. Check that the value has quotes at the start and end. Escape any quotes in the value with \\",  # noqa: E501
                "Incorrect date format. Dates should use the form YYYY-MM-DDT00:00:00Z. Learn more about dates in OCDS.",  # noqa: E501
                "Invalid 'uri' found",
                '"" is too short. Strings must be at least one character. This error typically indicates a missing value.',  # noqa: E501
                "[] is too short. You must supply at least one value, or remove the item entirely (unless it’s required).",  # noqa: E501
            ],
            [
                "id falta pero se requiere dentro de tender",
                "initiationType falta pero se requiere",
                "version no coincide con la expresión regular ^(\\d+\\.)(\\d+)$",
                "amount no es un número. Compruebe que el valor no contenga ningún carácter más que 0-9 y el punto (.). Los valores numéricos no deben estar entre comillas",  # noqa: E501
                "buyer no es un objeto JSON.",
                "numberOfTenderers no es un entero. Compruebe que el valor no contenga puntos decimales ni ningún otro carácter que no sea 0-9. Los valores enteros no deben estar entre comillas.",  # noqa: E501
                "ocid no es un hilo. Revise que el valor no es 'null', y tenga comillas al principio y al final. Escapa de cualquier comillas con el valor \\",  # noqa: E501
                "parties no es una matriz JSON",
                "title no es un hilo. Revise que el valor tenga comillas al principio y al final. Escapa de cualquier comillas con el valor \\",  # noqa: E501
                "Formato de fecha inválido. Las fechas deben usar el formato YYYY-MM-DDT00:00:00Z. Lea más sobre fechas en OCDS",  # noqa: E501
                "Se ha encontrado una 'uri' inválida",
                '"" es muy corto. Las cadenas deben ser de al menos un caracter. Este error generalmente indica que hay un valor faltante.',  # noqa: E501
                "[] es muy corto. Debe proporcionar al menos un valor o eliminar el artículo por completo (a menos que sea necesario)",  # noqa: E501
            ],
        ),
    ],
)
def test_jsonschema_translation(submit_url, filename, english, spanish):
    page = submit_url(filename)
    elements = page.locator(".panel-danger td:first-child > p").all()

    assert_in(elements, english, spanish)

    page.locator("select[name='language']").select_option("es")
    page.wait_for_load_state("networkidle")
    elements = page.locator(".panel-danger td:first-child > p").all()

    assert_in(elements, spanish, english)
