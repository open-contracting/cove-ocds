How to add key field information
================================

Key Field Information is a summary of key statistics about the data that's been provided.

Before you start
----------------

These instructions assume that you are familiar with OCDS, Django and Python development. The index page of these documents give instructions on how to set up and run the Data Review Tool locally, for development purposes. These instructions also assume that you're working on improvements to the live OCDS Data Review Tool, but they're equally relevant if you're modifying the DRT for a particular local use case. If you're contributing to the live DRT but aren't part of a team doing so for OCP, please contact the Data Support Team to let us know what you're working on, so that we can help make sure that your work is relevant. 

Because adding to KFI requires changes in both lib-cove-ocds and cove-ocds, you might find it helpful to install lib-cove-ocds using ``pip``'s ``-e`` option, which will ensure that changes that you make to your lib-cove-ocds installation are immediately available in your cove-ocds installation. To do this, simply run ``pip install -e /path/to/lib-cove-ocds`` after installing the normal development requirements. 

Because the code changes over time, links are to lines in specific versions of files; some copy/paste/search may be required to cross-reference with newer versions of files. 

Overview
--------

The Key Field Information section of the results page presents summary statistics that are generated in the `lib-cove-ocds <https://github.com/open-contracting/lib-cove-ocds>`_ library and are presented in the UI via templates in cove-ocds. To make a change, we're going to add the code that generates the statistic to lib-cove-ocds's `common_checks.py <https://github.com/open-contracting/lib-cove-ocds/blob/main/libcoveocds/lib/common_checks.py>`_, and then present it in the explore_additional_content block of of the `results page template <https://github.com/open-contracting/cove-ocds/blob/main/cove_ocds/templates/cove_ocds/explore_release.html>`_

For this article, we'll be using a real-life example that was `reported on GitHub <https://github.com/open-contracting/cove-ocds/issues/69>`_ - adding a count of unique item IDs to KFI. To achieve this, we'll carry out three steps:

* Generate the stats in common.py
* Present the stats in the template
* Write appropriate tests

This article doesn't cover getting your work merged and deployed; please contact data@open-contracting.org if you're looking to contribute to the Data Review Tool and need help with this. 


Generating the statistics in common.py
--------------------------------------

common.py contains a function called ``get_release_aggregates``, which broadly comprises three parts:

* Set up variables
* Iterate through the data, adding to various counters and collections as it goes
* Return a ``dict``, which contains either variables verbatim or with minimal processing (eg sorting)

KFIs are generated on a best-effort basis, so be aware that the data might be invalid, missing fields, or use unexpected formats. For this reason, and for reasons of performance, KFI checks are typically small, high-level and not computationally expensive.

.. tip:: Safely accessing data 
	Because KFIs are generated from data that might not be using the standard, it's important to use safe ways of accessing the data. The existing code already always uses get() to access attributes (because get() doesn't throw an exception if the key doesn't exist), and always tests that a value isn't null before using it. It also uses default values to ensure that types are correct - for example if an attribute is a list, then the default value should be an empty list in order to avoid a TypeError. New KFIs should follow these same patterns. 

In this case, KFIs already has some code that iterates through the items in each of the `tender <https://github.com/open-contracting/lib-cove-ocds/blob/388df45/libcoveocds/lib/common_checks.py#L153-158>`_, `award <https://github.com/open-contracting/lib-cove-ocds/blob/388df45/libcoveocds/lib/common_checks.py#L177-L182>`_ and `contract <https://github.com/open-contracting/lib-cove-ocds/blob/388df45/libcoveocds/lib/common_checks.py#L200-205>`_ stages, so we'll be adding to that. 

First, we're going to need a new variable. We don't care about how many times an item ID appears, just the number of item IDs that appear in the whole of the data, so we'll use a ``set``:

.. literalinclude:: code_examples/kfi-variables-added.py
	:diff: code_examples/kfi-variables-orig.py

Next, we'll add the IDs of each item to that ``set`` when we're iterating through them:

For tenders:

.. literalinclude:: code_examples/kfi-item-ids.txt
	:language: python
	:diff: code_examples/kfi-item-ids.orig

Next, make the same change to the similar code for both awards and contracts. This is left as an exercise for the reader. 

Finally, add the new ``set`` to the return ``dict``:

.. literalinclude:: code_examples/kfi-return.txt
	:language: python
	:diff: code_examples/kfi-return.orig


Presenting the statistics in the template
-----------------------------------------

The `template <https://github.com/open-contracting/cove-ocds/blob/main/cove_ocds/templates/cove_ocds/explore_release.html>`_ is passed the returned dict from ``get_release_aggregates``, and names it ``ra``.

Therefore, we need to choose an appropriate place in the template, and use our new variable: 

.. literalinclude:: code_examples/kfi-template-added.html
	:diff: code_examples/kfi-template-orig.html

Because the DRT interface is fully translated, don't forget to add :doc:`translations` for the any new text in templates. 


Adding tests
------------

**Note:** Edit the tests in lib-cove-ocds instead.

Because the DRT has a lib+app architecture, we need to add tests to both the library (lib-cove-ocds) and the app (cove-ocds). This does mean that there's some duplication, but it helps to locate errors when they occur. Because there's already tests for the adjacent code, we will be modifying what's already there rather than adding new tests.

First, we'll look at the `unit tests in lib-cove-ocds <https://github.com/open-contracting/lib-cove-ocds/blob/main/tests/lib/test_common_checks.py>`_

The unit test file contains some setup at the top, and then a series of tests. 

So, we'll add our new values to the dicts that support the unit tests for the KFIs - ``EMPTY_RELEASE_AGGREGATE``, ``EXPECTED_RELEASE_AGGREGATE`` and ``EXPECTED_RELEASE_AGGREGATE_RANDOM``. 

``EMPTY_RELEASE_AGGREGATE`` is straightforward - we'll just add a row for our new variable, with a value of 0.

``EXPECTED_RELEASE_AGGREGATE`` is populated with the expected results from `fixtures/release_aggregate.json <https://github.com/open-contracting/cove-ocds/blob/main/tests/fixtures/release_aggregate.json>`_ , which is a small OCDS JSON file specifically to support testing KFIs. In order to work out the values here, calculate what the value should be based on that file, and insert the relevant result. If you've got a way of calculating the value in a way that's not the code that you've just written, this is a good chance to validate that your code is behaving correctly! If the KFI that you're adding can't be calculated from the existing data in that file, then add the relevant data, and update any other values that change as a result.

In this case, we can carry out the same calculation with ``jq`` and basic UNIX commandline tools:

.. code-block:: bash

	jq ".releases[] | (.tender?,.awards[]?,.contracts[]?) | .items[]?.id" tests/fixtures/release_aggregate.json | sort | uniq | wc -l
	2

(note that various values can be can be null or missing, hence using the ? so that jq doesn't stop with an error)

``EXPECTED_RELEASE_AGGREGATE_RANDOM`` is populated with the expected results from `fixtures/samplerubbish.json <https://github.com/open-contracting/cove-ocds/blob/main/tests/fixtures/samplerubbish.json>`_. This is a large OCDS JSON file that's nonsense, and is intended to provide a more robust test of the code. If the KFI that you're adding can't be calculated from the existing data in that file, then contact the Data Support Team to discuss generating a new version of the file that does include the relevant fields. 

.. code-block:: bash

	jq ".releases[] | (.tender?,.awards[]?,.contracts[]?) | .items[]?.id" tests/fixtures/samplerubbish.json | sort | uniq | wc -l
	4698


Then, we'll look at the `unit tests in cove-ocds <https://github.com/open-contracting/cove-ocds/blob/main/cove_ocds/tests.py>`_. These are very similar to the unit tests in lib-cove-ocds, so we'll just apply the same changes here. 

Then, we'll look at the `functional tests <https://github.com/open-contracting/cove-ocds/blob/main/cove_ocds/tests_functional.py>`_

There's a ``test_key_field_information`` already, so we'll just add our new value to that:

.. literalinclude:: code_examples/kfi-functional-test.txt
	:language: python
	:diff: code_examples/kfi-functional-test.orig


Finishing up
------------

If you're contributing to the OCP-maintained Data Review Tool, then you'll now need to:

* Make a PR against lib-cove-ocds with your work, and get it merged and released
* Then, make a PR against cove-ocds to use the new version of lib-cove-ocds and to include your new templates and tests. 

