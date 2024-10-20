import json

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from cove_ocds.models import SuppliedData

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


@pytest.mark.xfail
@pytest.mark.django_db
@given(
    general_json | st.fixed_dictionaries({"releases": general_json}) | st.fixed_dictionaries({"records": general_json})
)
def test_explore_page(client, json_data):
    data = SuppliedData.objects.create()
    data.original_file.save("test.json", ContentFile(json.dumps(json_data)))
    resp = client.get(reverse("explore", args=(data.pk,)))
    assert resp.status_code == 200


@pytest.mark.django_db
@given(general_json)
@example(1)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_explore_page_duplicate_ids(client, json_data):
    duplicate_id_releases = {"releases": [{"id": json_data}, {"id": json_data}]}
    data = SuppliedData.objects.create()
    data.original_file.save("test.json", ContentFile(json.dumps(duplicate_id_releases)))
    resp = client.get(reverse("explore", args=(data.pk,)))
    assert resp.status_code == 200
