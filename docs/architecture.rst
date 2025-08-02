Architecture
============

The OCDS Data Review tool comprises two main parts, which are documented here.

* cove-ocds (`this repository <https://github.com/open-contracting/cove-ocds>`_): a web application which makes light use of Django components.
* lib-cove-ocds (`open-contracting/lib-cove-ocds <https://github.com/open-contracting/lib-cove-ocds>`_): a library containing most of the functions for performing validation and transformation on OCDS data.

cove-ocds
---------

``tests/`` also contains fixtures for testing, and the tests themselves; templates and related static files; code for the CLI version of the DRT; and locale files for translations.

``cove_ocds/views.py`` does most of the heavy lifting of taking an input file from the web interface and carrying out the various validation checks, then piping the output back to the right templates.

``core/`` contains the Django components (settings, URL paths, server).

lib-cove-ocds
-------------

lib-cove-ocds contains OCDS data specific functions, but in a way that means they can be reused by other software and scripts without having to import the whole of the DRT to do so. It includes the SchemaOCDS object. Most of the validation checks for OCDS data are here.

lib-cove-ocds produces results in the form of dictionaries with meaningful keys. cove-ocds is responsible for mapping these keys onto a suitable UI. It's worth noting that cove-ocds is not the only tool that consumes the output of lib-cove-ocds. Different tools can produce the best UI for their particular context, so any UI or display work is done in the tool and not in the underlying library. This also means that the respective UIs can be translated or localized independently, according to the needs or usage of the tools. Having machine readable output from the library also means that we can take a database of output and easily parse it to create statistics about results or errors, etc.

External libraries
------------------

The OCDS Data Review Tool is just one manifestation of software historically known as 'CoVE' (Convert, Validate, Explore). Instances of CoVE exist for other standards as well as OCDS. We modularize and reuse code where possible, so as a result the DRT has dependencies on external libraries related to CoVE:

* lib-cove (`opendataservices/lib-cove <https://github.com/opendataservices/lib-cove>`_): contains functions and helpers that may be useful for data validation and review, regardless of the particular data standard.

Configuration
-------------

Some configuration variables are set in ``COVE_CONFIG``, found in ``core/settings.py``.

* ``schema_version_choices`` (``version: (display, url, tag)``), ``schema_codelists``: point to JSON schema files that the DRT uses for validating data. Since there is more than one version of the Open Contracting Data Standard, this lets the user choose which version of the scheme they are validating against.

Path through the code
---------------------

1. The input form on the landing page can be found in the ``input`` template (``cove_ocds/templates``).
2. Submitting the form calls the `explore_ocds` function (``cove_ocds/views.py``).

  * This checks for basic problems with the input file, and adds metadata.
  * It then performs OCDS specific JSON checks, if the input data is JSON.
  * And then schema-specific OCDS checks, depending on the version specified, using ``SchemaOCDS`` and ``common_checks`` from lib-cove-ocds. Functions from lib-cove-ocds also takes care of handling any extension data included in the input. lib-cove-ocds calls on lib-cove to perform schema validation that is not specific to OCDS, using JSON Schema and JSONRef, as well as common things like checking for duplicate identifiers.
  * lib-cove-ocds runs additional checks, which are basic data quality checks outside of the OCDS schema.
  * The results of the various stages of validation are added to the context so they can be displayed on the frontend. The JSON schema error messages are currently set in lib-cove and OCDS schema specific messages are set in lib-cove-ocds or in this repo.

3. The results of the validation, as well as some basic statistics on the data, are output to the ``explore`` html templates in ``cove_ocds/templates``.
