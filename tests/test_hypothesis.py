import json

import pytest
from cove.input.models import SuppliedData
from django.core.files.base import ContentFile
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st
from libcoveocds.lib.common_checks import get_releases_aggregates

"""
## Suggested testing patterns (from CamPUG talk)
* simple fuzzing
* round trip
* invariants and idempotents
* test oracle
"""

general_json = st.recursive(
    st.floats(allow_subnormal=False) | st.integers() | st.booleans() | st.text() | st.none(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
)


@given(general_json)
def test_get_releases_aggregates(json_data):
    get_releases_aggregates(json_data)


@given(general_json)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_get_releases_aggregates_dict(json_data):
    assume(type(json_data) is dict)
    get_releases_aggregates(json_data)


@pytest.mark.xfail
@pytest.mark.django_db
@pytest.mark.parametrize("current_app", ["cove-ocds"])
@given(
    general_json | st.fixed_dictionaries({"releases": general_json}) | st.fixed_dictionaries({"records": general_json})
)
def test_explore_page(client, current_app, json_data):
    data = SuppliedData.objects.create()
    data.original_file.save("test.json", ContentFile(json.dumps(json_data)))
    data.current_app = current_app
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("current_app", ["cove-ocds"])
@given(general_json)
@example(1)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_explore_page_duplicate_ids(client, current_app, json_data):
    duplicate_id_releases = {"releases": [{"id": json_data}, {"id": json_data}]}
    data = SuppliedData.objects.create()
    data.original_file.save("test.json", ContentFile(json.dumps(duplicate_id_releases)))
    data.current_app = current_app
    resp = client.get(data.get_absolute_url())
    assert resp.status_code == 200
