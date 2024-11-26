import pytest

from cove_ocds.util import get_file_type


@pytest.mark.parametrize("file_name", ["basic.xlsx", "basic.XLSX"])
def test_get_file_type_xlsx(file_name):
    assert get_file_type(file_name) == "xlsx"


@pytest.mark.parametrize("file_name", ["test.csv", "test.CSV"])
def test_get_file_type_csv(file_name):
    assert get_file_type(file_name) == "csv"


@pytest.mark.parametrize("file_name", ["test.json", "test.JSON"])
def test_get_file_type_json(file_name):
    assert get_file_type(file_name) == "json"


def test_get_file_type_byte(tmp_path):
    path = tmp_path / "test"
    path.write_text("{}")

    assert get_file_type(str(path)) == "json"


def test_get_file_type_error(tmp_path):
    assert get_file_type("test") is None
