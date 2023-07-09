import io
import json
import os
from unittest.mock import patch

import libcove.lib.common as cove_common
import pytest
from cove.input.models import SuppliedData
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from libcove.lib.converters import convert_json, convert_spreadsheet
from libcoveocds.api import APIException, ocds_json_output
from libcoveocds.lib.api import context_api_transform
from libcoveocds.lib.common_checks import get_bad_ocid_prefixes, get_releases_aggregates
from libcoveocds.schema import SchemaOCDS

OCDS_DEFAULT_SCHEMA_VERSION = settings.COVE_CONFIG["schema_version"]
DEFAULT_OCDS_VERSION = settings.COVE_CONFIG["schema_version"]
METRICS_EXT = "https://raw.githubusercontent.com/open-contracting-extensions/ocds_metrics_extension/master/extension.json"  # noqa: E501
CODELIST_EXT = "https://raw.githubusercontent.com/INAImexico/ocds_extendedProcurementCategory_extension/0ed54770c85500cf21f46e88fb06a30a5a2132b1/extension.json"  # noqa: E501


def test_get_schema_validation_errors():
    schema_obj = SchemaOCDS(select_version="1.0")

    with open(os.path.join("tests", "fixtures", "tenders_releases_2_releases.json")) as fp:
        error_list = cove_common.get_schema_validation_errors(json.load(fp), schema_obj, "-", {}, {})
        assert len(error_list) == 0
    with open(os.path.join("tests", "fixtures", "tenders_releases_2_releases_invalid.json")) as fp:
        error_list = cove_common.get_schema_validation_errors(json.load(fp), schema_obj, "-", {}, {})
        assert len(error_list) > 0


def test_get_json_data_generic_paths():
    with open(
        os.path.join(
            "tests",
            "fixtures",
            "tenders_releases_2_releases_with_deprecated_fields.json",
        )
    ) as fp:
        json_data_w_deprecations = json.load(fp)

    generic_paths = cove_common.get_json_data_generic_paths(json_data_w_deprecations, generic_paths={})
    assert len(generic_paths.keys()) == 36
    assert generic_paths[("releases", "buyer", "name")] == {
        ("releases", 1, "buyer", "name"): "Parks Canada",
        ("releases", 0, "buyer", "name"): "Agriculture & Agrifood Canada",
    }


def test_get_json_data_deprecated_fields():
    with open(
        os.path.join(
            "tests",
            "fixtures",
            "tenders_releases_2_releases_with_deprecated_fields.json",
        )
    ) as fp:
        json_data_w_deprecations = json.load(fp)

    schema_obj = SchemaOCDS()
    schema_obj.schema_host = os.path.join("tests", "fixtures/")  # "/" is for urljoin in lib-cove
    schema_obj.pkg_schema_name = "release_package_schema_ref_release_schema_deprecated_fields.json"
    schema_obj._test_override_package_schema = os.path.join(schema_obj.schema_host, schema_obj.pkg_schema_name)
    json_data_paths = cove_common.get_json_data_generic_paths(json_data_w_deprecations, generic_paths={})
    deprecated_data_fields = cove_common.get_json_data_deprecated_fields(json_data_paths, schema_obj)
    expected_result = {
        "initiationType": {
            "paths": ("releases/0", "releases/1"),
            "explanation": ("1.1", "Not a useful field as always has to be tender"),
        },
        "quantity": {
            "paths": ("releases/0/tender/items/0",),
            "explanation": ("1.1", "Nobody cares about quantities"),
        },
    }
    for field_name in expected_result.keys():
        assert field_name in deprecated_data_fields
        assert expected_result[field_name]["paths"] == deprecated_data_fields[field_name]["paths"]
        assert expected_result[field_name]["explanation"] == deprecated_data_fields[field_name]["explanation"]


def test_get_schema_deprecated_paths():
    schema_obj = SchemaOCDS()
    schema_obj.schema_host = os.path.join("tests", "fixtures/")  # "/" is for urljoin in lib-cove
    schema_obj.pkg_schema_name = "release_package_schema_ref_release_schema_deprecated_fields.json"
    schema_obj._test_override_package_schema = os.path.join(schema_obj.schema_host, schema_obj.pkg_schema_name)
    deprecated_paths = cove_common._get_schema_deprecated_paths(schema_obj)
    expected_results = [
        (
            ("releases", "initiationType"),
            ("1.1", "Not a useful field as always has to be tender"),
        ),
        (
            (
                "releases",
                "planning",
            ),
            ("1.1", "Testing deprecation for objects with '$ref'"),
        ),
        (("releases", "tender", "hasEnquiries"), ("1.1", "Deprecated just for fun")),
        (
            ("releases", "contracts", "items", "quantity"),
            ("1.1", "Nobody cares about quantities"),
        ),
        (
            ("releases", "tender", "items", "quantity"),
            ("1.1", "Nobody cares about quantities"),
        ),
        (
            ("releases", "awards", "items", "quantity"),
            ("1.1", "Nobody cares about quantities"),
        ),
    ]
    for path in expected_results:
        assert path in deprecated_paths
    assert len(deprecated_paths) == 6


@pytest.mark.django_db
@pytest.mark.parametrize(
    "json_data",
    [
        # A selection of JSON strings we expect to give a 200 status code, even
        # though some of them aren't valid OCDS
        "true",
        "null",
        "1",
        "{}",
        "[]",
        "[[]]",
        '{"releases":{}}',
        '{"releases" : 1.0}',
        '{"releases" : 2}',
        '{"releases" : true}',
        '{"releases" : "test"}',
        '{"releases" : null}',
        '{"releases" : {"a":"b"}}',
        '{"releases" : [["test"]]}',
        '{"records":{}}',
        '{"records" : 1.0}',
        '{"records" : 2}',
        '{"records" : true}',
        '{"records" : "test"}',
        '{"records" : null}',
        '{"records" : {"a":"b"}}',
        '{"records" : [["test"]]}',
        '{"version": "1.1", "releases" : 1.0}',
        '{"version": "1.1", "releases" : 2}',
        '{"version": "1.1", "releases" : true}',
        '{"version": "1.1", "releases" : "test"}',
        '{"version": "1.1", "releases" : null}',
        '{"version": "1.1", "releases" : {"version": "1.1", "a":"b"}}',
        '{"version": "1.1", "records" : 1.0}',
        '{"version": "1.1", "records" : 2}',
        '{"version": "1.1", "records" : true}',
        '{"version": "1.1", "records" : "test"}',
        '{"version": "1.1", "records" : {"version": "1.1", "a":"b"}}',
        '{"version": "1.1", "releases":{"buyer":{"additionalIdentifiers":[]}}}',
        '{"version": "1.1", "releases":{"parties":{"roles":[["a","b"]]}}}',  # test an array in a codelist position
        """{
            "extensions": [
                "https://raw.githubusercontent.com/open-contracting-extensions/ocds_bid_extension/v1.1.1/extension.jso"
            ],
            "releases": []
        }""",
        '{"extensions":[{}], "releases":[]}'
        """{
            "extensions": [
                "https://raw.githubusercontent.com/open-contracting-extensions/ocds_bid_extension/v1.1.1/extension.jso"
            ],
            "releases": [],
            "version": "1.1"
        }""",
        '{"extensions":[{}], "releases":[], "version": "1.1"}',
    ],
)
def test_explore_page(client, json_data):
    data = SuppliedData.objects.create()
    data.original_file.save("test.json", ContentFile(json_data))
    data.current_app = "cove_ocds"
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200


@pytest.mark.django_db
def test_explore_page_convert(client):
    data = SuppliedData.objects.create()
    data.original_file.save("test.json", ContentFile('{"releases":[]}'))
    data.current_app = "cove_ocds"
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
    assert resp.context["conversion"] == "flattenable"

    resp = client.post(data.get_absolute_url(), {"flatten": "true"})
    assert resp.status_code == 200
    assert resp.context["conversion"] == "flatten"
    assert "converted_file_size" in resp.context
    assert "converted_file_size_titles" not in resp.context


@pytest.mark.django_db
def test_explore_page_csv(client):
    data = SuppliedData.objects.create()
    data.original_file.save("test.csv", ContentFile("a,b"))
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
    assert resp.context["conversion"] == "unflatten"
    assert resp.context["converted_file_size"] == 22


@pytest.mark.django_db
def test_explore_not_json(client):
    data = SuppliedData.objects.create()
    with open(os.path.join("tests", "fixtures", "tenders_releases_2_releases_not_json.json")) as fp:
        data.original_file.save("test.json", UploadedFile(fp))
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
    assert b"not well formed JSON" in resp.content


@pytest.mark.django_db
def test_explore_unconvertable_spreadsheet(client):
    data = SuppliedData.objects.create()
    with open(os.path.join("tests", "fixtures", "bad.xlsx"), "rb") as fp:
        data.original_file.save("basic.xlsx", UploadedFile(fp))
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
    assert b"We think you tried to supply a spreadsheet, but we failed to convert it." in resp.content


@pytest.mark.django_db
def test_explore_unconvertable_json(client):
    data = SuppliedData.objects.create()
    with open(os.path.join("tests", "fixtures", "unconvertable_json.json")) as fp:
        data.original_file.save("unconvertable_json.json", UploadedFile(fp))
    resp = client.post(data.get_absolute_url(), {"flatten": "true"})
    assert resp.status_code == 200
    assert b"could not be converted" in resp.content


@pytest.mark.django_db
def test_explore_page_null_tag(client):
    data = SuppliedData.objects.create()
    data.original_file.save("test.json", ContentFile('{"releases":[{"tag":null}]}'))
    data.current_app = "cove_ocds"
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "json_data",
    [
        '{"version": "1.1", "releases": [{"ocid": "xx"}]}',
        '{"version": "112233", "releases": [{"ocid": "xx"}]}',
        '{"releases": [{"ocid": "xx"}]}',
    ],
)
def test_explore_schema_version(client, json_data):
    data = SuppliedData.objects.create()
    data.original_file.save("test.json", ContentFile(json_data))
    data.current_app = "cove_ocds"

    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
    if "version" not in json_data:
        assert "/1.0/" in resp.context["schema_url"]
        assert resp.context["version_used"] == "1.0"
        assert resp.context["version_used_display"] == "1.0"
        resp = client.post(data.get_absolute_url(), {"version": "1.1"})
        assert resp.status_code == 200
        assert "/1.1/" in resp.context["schema_url"]
        assert resp.context["version_used"] == "1.1"
    else:
        assert "/1.1/" in resp.context["schema_url"]
        assert resp.context["version_used"] == "1.1"
        assert resp.context["version_used_display"] == "1.1"
        resp = client.post(data.get_absolute_url(), {"version": "1.0"})
        assert resp.status_code == 200
        assert "/1.0/" in resp.context["schema_url"]
        assert resp.context["version_used"] == "1.0"
        assert resp.context["version_used_display"] == "1.0"


@pytest.mark.django_db
def test_wrong_schema_version_in_data(client):
    data = SuppliedData.objects.create()
    data.original_file.save("test.json", ContentFile('{"version": "1.bad", "releases": [{"ocid": "xx"}]}'))
    data.current_app = "cove_ocds"
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
    assert resp.context["version_used"] == OCDS_DEFAULT_SCHEMA_VERSION


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("file_type", "converter", "replace_after_post"),
    [("xlsx", convert_spreadsheet, True), ("json", convert_json, False)],
)
def test_explore_schema_version_change(client, file_type, converter, replace_after_post):
    data = SuppliedData.objects.create()
    with open(
        os.path.join("tests", "fixtures", f"tenders_releases_2_releases.{file_type}"),
        "rb",
    ) as fp:
        data.original_file.save(f"test.{file_type}", UploadedFile(fp))
    data.current_app = "cove_ocds"

    with patch(
        f"cove_ocds.views.{converter.__name__}",
        side_effect=converter,
        autospec=True,
    ) as mock_object:
        resp = client.get(data.get_absolute_url())
        args, kwargs = mock_object.call_args
        assert resp.status_code == 200
        assert resp.context["version_used"] == "1.0"
        assert mock_object.called
        assert "/1.0/" in kwargs["schema_url"]
        assert kwargs["replace"] is False
        mock_object.reset_mock()

        resp = client.post(data.get_absolute_url(), {"version": "1.1"})
        args, kwargs = mock_object.call_args
        assert resp.status_code == 200
        assert resp.context["version_used"] == "1.1"
        assert mock_object.called
        assert "/1.1/" in kwargs["schema_url"]
        assert kwargs["replace"] is replace_after_post


@pytest.mark.django_db
@patch("cove_ocds.views.convert_json", side_effect=convert_json, autospec=True)
def test_explore_schema_version_change_with_json_to_xlsx(mock_object, client):
    data = SuppliedData.objects.create()
    with open(os.path.join("tests", "fixtures", "tenders_releases_2_releases.json")) as fp:
        data.original_file.save("test.json", UploadedFile(fp))
    data.current_app = "cove_ocds"

    resp = client.get(data.get_absolute_url())
    args, kwargs = mock_object.call_args
    assert resp.status_code == 200
    assert "/1.0/" in kwargs["schema_url"]
    assert kwargs["replace"] is False
    mock_object.reset_mock()

    resp = client.post(data.get_absolute_url(), {"version": "1.1"})
    args, kwargs = mock_object.call_args
    assert resp.status_code == 200
    assert kwargs["replace"] is False
    mock_object.reset_mock()

    # Convert to spreadsheet
    resp = client.post(data.get_absolute_url(), {"flatten": "true"})
    assert kwargs["replace"] is False
    mock_object.reset_mock()

    # Do replace with version change now that it's been converted once
    resp = client.post(data.get_absolute_url(), {"version": "1.0"})
    args, kwargs = mock_object.call_args
    assert resp.status_code == 200
    assert kwargs["replace"] is True
    mock_object.reset_mock()

    # Do not replace if the version does not changed
    resp = client.post(data.get_absolute_url(), {"version": "1.0"})
    args, kwargs = mock_object.call_args
    assert resp.status_code == 200
    assert kwargs["replace"] is False
    mock_object.reset_mock()

    resp = client.post(data.get_absolute_url(), {"version": "1.1"})
    args, kwargs = mock_object.call_args
    assert resp.status_code == 200
    assert kwargs["replace"] is True
    mock_object.reset_mock()


@pytest.mark.django_db
def test_data_supplied_schema_version(client):
    data = SuppliedData.objects.create()
    with open(os.path.join("tests", "fixtures", "tenders_releases_2_releases.xlsx"), "rb") as fp:
        data.original_file.save("test.xlsx", UploadedFile(fp))
    data.current_app = "cove_ocds"

    assert data.schema_version == ""

    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
    assert resp.context["version_used"] == "1.0"
    assert SuppliedData.objects.get(id=data.id).schema_version == "1.0"

    resp = client.post(data.get_absolute_url(), {"version": "1.1"})
    assert resp.status_code == 200
    assert resp.context["version_used"] == "1.1"
    assert SuppliedData.objects.get(id=data.id).schema_version == "1.1"


def test_get_additional_codelist_values():
    with open(os.path.join("tests", "fixtures", "tenders_releases_2_releases_codelists.json")) as fp:
        json_data_w_additial_codelists = json.load(fp)

    schema_obj = SchemaOCDS(select_version="1.1")
    additional_codelist_values = cove_common.get_additional_codelist_values(schema_obj, json_data_w_additial_codelists)

    assert additional_codelist_values == {
        ("releases/tag"): {
            "codelist": "releaseTag.csv",
            "codelist_url": "https://raw.githubusercontent.com/open-contracting/standard/1.1/schema/codelists/releaseTag.csv",  # noqa: E501
            "codelist_amend_urls": [],
            "field": "tag",
            "extension_codelist": False,
            "isopen": False,
            "path": "releases",
            "values": ["oh no"],
        },
        ("releases/tender/items/classification/scheme"): {
            "codelist": "itemClassificationScheme.csv",
            "codelist_url": "https://raw.githubusercontent.com/open-contracting/standard/1.1/schema/codelists/itemClassificationScheme.csv",  # noqa: E501
            "codelist_amend_urls": [],
            "extension_codelist": False,
            "field": "scheme",
            "isopen": True,
            "path": "releases/tender/items/classification",
            "values": ["GSINS"],
        },
    }


@pytest.mark.django_db
def test_schema_ocds_extended_schema_file():
    data = SuppliedData.objects.create()
    with open(
        os.path.join(
            "tests",
            "fixtures",
            "tenders_releases_1_release_with_extensions_1_1.json",
        )
    ) as fp:
        data.original_file.save("test.json", UploadedFile(fp))
        fp.seek(0)
        json_data = json.load(fp)
    schema = SchemaOCDS(package_data=json_data)
    assert not schema.extended

    schema.get_schema_obj()
    assert schema.extended
    assert not schema.extended_schema_file
    assert not schema.extended_schema_url

    schema.create_extended_schema_file(data.upload_dir(), data.upload_url())
    assert schema.extended_schema_file == os.path.join(data.upload_dir(), "extended_schema.json")
    assert schema.extended_schema_url == os.path.join(data.upload_url(), "extended_schema.json")

    json_data = json.loads('{"version": "1.1", "extensions": [], "releases": [{"ocid": "xx"}]}')
    schema = SchemaOCDS(package_data=json_data)
    schema.get_schema_obj()
    schema.create_extended_schema_file(data.upload_dir(), data.upload_url())
    assert not schema.extended
    assert not schema.extended_schema_file
    assert not schema.extended_schema_url


@pytest.mark.django_db
def test_schema_after_version_change(client):
    data = SuppliedData.objects.create()
    with open(
        os.path.join(
            "tests",
            "fixtures",
            "tenders_releases_1_release_with_invalid_extensions.json",
        )
    ) as fp:
        data.original_file.save("test.json", UploadedFile(fp))

    resp = client.post(data.get_absolute_url(), {"version": "1.1"})
    assert resp.status_code == 200

    with open(os.path.join(data.upload_dir(), "extended_schema.json")) as extended_release_fp:
        assert "mainProcurementCategory" in json.load(extended_release_fp)["definitions"]["Tender"]["properties"]

    with open(os.path.join(data.upload_dir(), "validation_errors-3.json")) as validation_errors_fp:
        assert "'version' is missing but required" in validation_errors_fp.read()

    # test link is still there.
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
    assert "extended_schema.json" in resp.content.decode()

    with open(os.path.join(data.upload_dir(), "extended_schema.json")) as extended_release_fp:
        assert "mainProcurementCategory" in json.load(extended_release_fp)["definitions"]["Tender"]["properties"]

    with open(os.path.join(data.upload_dir(), "validation_errors-3.json")) as validation_errors_fp:
        assert "'version' is missing but required" in validation_errors_fp.read()

    resp = client.post(data.get_absolute_url(), {"version": "1.0"})
    assert resp.status_code == 200

    with open(os.path.join(data.upload_dir(), "extended_schema.json")) as extended_release_fp:
        assert "mainProcurementCategory" not in json.load(extended_release_fp)["definitions"]["Tender"]["properties"]

    with open(os.path.join(data.upload_dir(), "validation_errors-3.json")) as validation_errors_fp:
        assert "'version' is missing but required" not in validation_errors_fp.read()


@pytest.mark.django_db
def test_schema_after_version_change_record(client):
    data = SuppliedData.objects.create()
    with open(
        os.path.join(
            "tests",
            "fixtures",
            "tenders_records_1_record_with_invalid_extensions.json",
        )
    ) as fp:
        new_json = json.load(fp)
        # Test without version field
        new_json.pop("version")
        new_json_file = io.StringIO(json.dumps(new_json))
        data.original_file.save("test.json", UploadedFile(new_json_file))

    resp = client.post(data.get_absolute_url(), {"version": "1.1"})
    assert resp.status_code == 200

    with open(os.path.join(data.upload_dir(), "extended_schema.json")) as extended_release_fp:
        assert "mainProcurementCategory" in json.load(extended_release_fp)["definitions"]["Tender"]["properties"]

    with open(os.path.join(data.upload_dir(), "validation_errors-3.json")) as validation_errors_fp:
        assert "'version' is missing but required" in validation_errors_fp.read()

    # test link is still there.
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
    assert "extended_schema.json" in resp.content.decode()

    with open(os.path.join(data.upload_dir(), "extended_schema.json")) as extended_release_fp:
        assert "mainProcurementCategory" in json.load(extended_release_fp)["definitions"]["Tender"]["properties"]

    with open(os.path.join(data.upload_dir(), "validation_errors-3.json")) as validation_errors_fp:
        assert "'version' is missing but required" in validation_errors_fp.read()

    resp = client.post(data.get_absolute_url(), {"version": "1.0"})
    assert resp.status_code == 200

    with open(os.path.join(data.upload_dir(), "extended_schema.json")) as extended_release_fp:
        assert "mainProcurementCategory" not in json.load(extended_release_fp)["definitions"]["Tender"]["properties"]

    with open(os.path.join(data.upload_dir(), "validation_errors-3.json")) as validation_errors_fp:
        assert "'version' is missing but required" not in validation_errors_fp.read()


@pytest.mark.parametrize(
    "json_data",
    [
        '{"version":"1.1", "releases":{"buyer":{"additionalIdentifiers":[]}, "initiationType": "tender"}}',
        # TODO: add more ...
    ],
)
def test_corner_cases_for_deprecated_data_fields(json_data):
    data = json.loads(json_data)
    schema = SchemaOCDS(package_data=data)
    json_data_paths = cove_common.get_json_data_generic_paths(data, generic_paths={})
    deprecated_fields = cove_common.get_json_data_deprecated_fields(json_data_paths, schema)

    assert deprecated_fields["additionalIdentifiers"]["explanation"][0] == "1.1"
    assert (
        "parties section at the top level of a release" in deprecated_fields["additionalIdentifiers"]["explanation"][1]
    )
    assert deprecated_fields["additionalIdentifiers"]["paths"] == ("releases/buyer",)
    assert len(deprecated_fields.keys()) == 1
    assert len(deprecated_fields["additionalIdentifiers"]["paths"]) == 1


@pytest.mark.django_db
@pytest.mark.parametrize("json_data", ["{[,]}", '{"version": "1.bad"}'])
def test_ocds_json_output_bad_data(json_data):
    data = SuppliedData.objects.create()
    data.original_file.save("bad_data.json", ContentFile(json_data))
    with pytest.raises(APIException):
        ocds_json_output(
            data.upload_dir(),
            data.original_file.path,
            schema_version="",
            convert=False,
        )


def test_get_schema_non_required_ids():
    schema_obj = SchemaOCDS(select_version="1.1")
    non_required_ids = cove_common._get_schema_non_required_ids(schema_obj)
    results = [
        ("releases", "awards", "amendments", "id"),
        ("releases", "awards", "suppliers", "id"),
        ("releases", "contracts", "amendments", "id"),
        ("releases", "contracts", "relatedProcesses", "id"),
        ("releases", "parties", "id"),
        ("releases", "relatedProcesses", "id"),
        ("releases", "tender", "amendments", "id"),
        ("releases", "tender", "tenderers", "id"),
    ]

    assert sorted(non_required_ids) == results


def test_get_json_data_missing_ids():
    file_name = os.path.join(
        "tests",
        "fixtures",
        "tenders_releases_2_releases_1_1_tenderers_with_missing_ids.json",
    )
    with open(os.path.join(file_name)) as fp:
        user_data = json.load(fp)

    schema_obj = SchemaOCDS(package_data=user_data)
    results = [
        "releases/0/tender/tenderers/1/id",
        "releases/0/tender/tenderers/2/id",
        "releases/0/tender/tenderers/5/id",
        "releases/1/tender/tenderers/1/id",
        "releases/1/tender/tenderers/2/id",
        "releases/1/tender/tenderers/4/id",
    ]
    user_data_paths = cove_common.get_json_data_generic_paths(user_data, generic_paths={})
    missin_ids_paths = cove_common.get_json_data_missing_ids(user_data_paths, schema_obj)

    assert missin_ids_paths == results
