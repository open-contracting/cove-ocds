OCDS Data Review Tool: Developer Documentation
==============================================

.. include:: ../README.rst


This documentation is for people who wish to contribute to or modify the DRT.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   architecture
   template-structure
   translations
   how-to-add-a-validation-check
   how-to-edit-stylesheet
   how-to-config-frontend
   tests
   ocds-show

.. _run_locally:

Running it locally
------------------

* Clone the repository
* Change into the cloned repository
* Create a virtual environment (note this application uses python3)
* Activate the virtual environment
* Install dependencies
* Set up the database (sqlite3)
* Compile the translations
* Run the development server

.. code:: bash

    git clone https://github.com/open-contracting/cove-ocds.git
    cd cove-ocds
    python3 -m venv .ve
    source .ve/bin/activate
    pip install -r requirements_dev.txt
    python manage.py migrate
    python manage.py compilemessages
    python manage.py runserver

This will make the test site available on the local machine only. If you are running in some kind of container, you may need to do:

.. code:: bash

    python manage.py runserver 0.0.0.0:8000

Commandline interface
---------------------

You can pass a JSON file for review to the DRT at the commandline after installing it in a virtual environment.

.. code:: bash

    $ python manage.py ocds_cli [-h]
                                [--version] [-v {0,1,2,3}]
                                [--settings SETTINGS]
                                [--pythonpath PYTHONPATH]
                                [--traceback]
                                [--no-color]
                                [--schema-version SCHEMA_VERSION]
                                [--convert]
                                [--output-dir OUTPUT_DIR]
                                [--delete]
                                [--exclude-file]
                                file


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
