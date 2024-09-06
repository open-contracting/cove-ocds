Tests
=====

Run the tests with:

.. code:: bash

    coverage run --source=cove_ocds,cove_project -m pytest

See ``tests/fixtures`` for good and bad JSON and XML files for testing the DRT.

Tests are found in the following files:

* Input tests (``test_input.py``): Test the input form and responses.
* Functional tests (``tests_functional.py``): Do roundtrip testing of the whole DRT using `Selenium <https://github.com/SeleniumHQ/selenium>`_. Some of these tests involve hardcoded frontend text, so if you change any of the templates you might need to update a test here.
* `Hypothesis <https://hypothesis.works/>`_ tests (``test_hypothesis.py``): Generate JSON for some unit and some functional tests.
* The rest of the tests (``test.py``): Are unit tests for the various validation and conversion functions. Some of these test code in lib-cove-ocds. 