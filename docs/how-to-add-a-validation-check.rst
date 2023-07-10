How to add a validation check
=============================

Data validation takes place in the `lib-cove-ocds <https://github.com/open-contracting/lib-cove-ocds>`_ library and are presented in the UI via templates in cove-ocds.

'Common checks' process the various different objects in a release, so the data can be validated against the schema and statistics about different aspects of the data (eg. the number of contracts, the range of dates, or number of unique organizations present) can be presented in the UI. This happens in ``lib/common_checks.py``.

'Additional checks' are for data validation beyond what is covered by validation against the `OCDS Schema <https://github.com/open-contracting/lib-cove-ocds/blob/main/libcoveocds/schema.py>`_ - that is, the results of these checks may suggest an issue with the data where the issue does not cause data to be invalid against the schema - and are implemented in ``lib/additional_checks.py``. An example of such a check is identifying when fields, objects and arrays exist but are empty or contain only whitespace.

What follows is an outline of how to add a check. This will involve making changes in both `lib-cove-ocds` and `cove-ocds`.

Changes to ``lib-cove-ocds``
----------------------------

Make a new function for your check in ``lib/additional_checks.py``. The function must yield a dict for each check failure. The dict contains any information to be displayed in the template. See the ``empty_field`` function as an example.

Add the new function to the list of checks, so that it runs when ``run_additional_checks()`` is called from `the top-level common_checks.py <https://github.com/open-contracting/lib-cove-ocds/blob/main/libcoveocds/common_checks.py>`_).

.. code-block:: python

    CHECKS = {"all": [empty_field, my_new_function], "none": []}

Add tests for the new function in ``tests/test_additional_checks.py`` and any fixtures in ``tests/fixtures/additional_checks/``.

Changes to ``cove-ocds``
------------------------

The templates need updating to display the results of your additional checks. It's likely that the only file you need to modify is ``templates/cove_ocds/additional_checks_table.html``. 

Add a clause for your new check using ``{% if type == 'sample_check' %}`` (where ``sample_check`` is the ``type`` you set in the output) and then display the results how you see fit. You can integrate them into the existing additional checks table, or output them some other way if that makes more sense. Iterate through the output you set, eg:

.. code-block:: html

    {% for value in values|slice:":3" %}
      <li>{{ value.something_useful }}</li>
    {% endfor %}

If you add new copy to the template, don't forget the :doc:`translations`.

Releasing changes
-----------------

When you make changes in `lib-cove-ocds` that changes in `cove-ocds` are dependent upon, remember to update the version number of `lib-cove-ocds` in the same PR, and make a new release once the PR is merged. Then in your PR against `cove-ocds` you can also update the version of the `lib-cove-ocds` dependency to match your update.