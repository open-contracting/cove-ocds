import os

import pytest

from cove_ocds.models import SuppliedData


@pytest.mark.django_db
def test_input(client):
    resp = client.get("/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_input_post(client):
    resp = client.post(
        "/",
        {
            "source_url": "https://raw.githubusercontent.com/OpenDataServices/flatten-tool/main/flattentool/tests/fixtures/tenders_releases_2_releases.json"
        },
    )

    assert resp.status_code == 302
    assert SuppliedData.objects.count() == 1
    data = SuppliedData.objects.first()
    assert resp.url.endswith(str(data.pk))


@pytest.mark.django_db
def test_connection_error(client):
    resp = client.post("/", {"source_url": "http://localhost:1234"})
    assert b"Connection refused" in resp.content

    resp = client.post("/", {"source_url": "https://wrong.host.badssl.com/"})
    assert b"Hostname mismatch, certificate is not valid" in resp.content


@pytest.mark.django_db
def test_http_error(client):
    resp = client.post("/", {"source_url": "http://google.co.uk/cove"})
    assert b"Not Found" in resp.content


@pytest.mark.django_db
def test_extension_from_content_type(client, httpserver):
    httpserver.serve_content("{}", headers={"content-type": "text/csv"})
    client.post("/", {"source_url": httpserver.url})
    supplied_datas = SuppliedData.objects.all()
    assert len(supplied_datas) == 1
    assert supplied_datas[0].original_file.name.endswith(".csv")


@pytest.mark.django_db
def test_extension_from_content_disposition(client, httpserver):
    httpserver.serve_content("{}", headers={"content-disposition": 'attachment; filename="something.csv"'})
    client.post("/", {"source_url": httpserver.url})
    supplied_datas = SuppliedData.objects.all()
    assert len(supplied_datas) == 1
    assert supplied_datas[0].original_file.name.endswith(".csv")


@pytest.mark.django_db
def test_directory_for_empty_filename(client):
    """
    Check that URLs ending in / correctly create a directory, to test against
    regressions of https://github.com/OpenDataServices/cove/issues/426
    """
    client.post("/", {"source_url": "http://example.org/"})
    supplied_datas = SuppliedData.objects.all()
    assert len(supplied_datas) == 1
    assert os.path.isdir(supplied_datas[0].upload_dir())
