OCDS Data Review Tool
=====================

.. include:: ../README.rst

This documentation is for people who wish to contribute to or modify the Data Review Tool (DRT).

The `CoVE <https://cove.readthedocs.io/en/latest/>`__ documentation might also be relevant.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   architecture
   how-to-add-a-validation-check

There are `drafts <https://docs.google.com/document/d/1EER_GjXi7F0SPZ_Mra9JuQBY5JxU0NGRSS9mYzB4guU/edit>`__ of another couple how-tos for adding headlines and modifying validation error messages.

.. _run_locally:

Run server
----------

Install dependencies:

.. code:: bash

    pip install -r requirements_dev.txt

Set up the database (sqlite3):

.. code:: bash

    python manage.py migrate

Compile translations:

.. code:: bash

    python manage.py compilemessages

Run the development server:

.. code:: bash

    python manage.py runserver

Edit stylesheets
----------------

Edit a file in the ``cove_ocds/sass`` directory:

* ``_bootstrap-variables-ocds.sass`` to change variables used by bootstrap (e.g. colors)
* ``_custom-ocds.sass`` to add extra CSS blocks.

Generate the CSS files:

.. code-block:: bash

    pysassc -t compressed -I bootstrap cove_ocds/sass/styles-ocds.sass cove_ocds/static/css/bootstrap-ocds.css

Run tests
---------

.. code:: bash

    coverage run --source=cove_ocds,core -m pytest

See ``tests/fixtures`` for good and bad JSON and XML files for testing the DRT.

Tests are found in the following files:

* Input tests (``test_input.py``): Test the input form and responses.
* Functional tests (``tests_functional.py``): Do roundtrip testing of the whole DRT using `Selenium <https://github.com/SeleniumHQ/selenium>`_. Some of these tests involve hardcoded frontend text, so if you change any of the templates you might need to update a test here.
* `Hypothesis <https://hypothesis.works/>`_ tests (``test_hypothesis.py``): Generate JSON for some unit and some functional tests.
* The rest of the tests (``test.py``): Are unit tests for the various validation functions. Some of these test code in lib-cove-ocds.
