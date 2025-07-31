OCDS Data Review Tool
=====================

.. include:: ../README.rst


This documentation is for people who wish to contribute to or modify the Data Review Tool (DRT).

The `CoVE <https://cove.readthedocs.io/en/latest/>`__ documentation might also be relevant.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   architecture
   template-structure
   translations
   how-to-add-a-validation-check
   how-to-edit-stylesheet
   how-to-config-frontend
   how-to-add-kfi

There are `drafts <https://docs.google.com/document/d/1EER_GjXi7F0SPZ_Mra9JuQBY5JxU0NGRSS9mYzB4guU/edit>`__ of another couple how-tos for adding headlines and modifying validation error messages.

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

This will make the test site available on the local machine only. If you are running in some kind of container, or on a remote development machine you will need to run:

.. code:: bash

    ALLOWED_HOSTS='XXX.XXX.XXX.XXX' python manage.py runserver 0.0.0.0:8000

where XXX.XXX.XXX.XXX is the IP address that you'll be using to access the running service. 
