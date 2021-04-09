How to edit the stylesheet
==========================

First: Run the setup from :ref:`run_locally`.

Edit a file in the ``cove_ocds/sass`` directory:

* ``_bootstrap-variables-ocds.sass`` to change variables used by bootstrap (e.g. colors)
* ``_custom-ocds.sass`` to add extra CSS blocks.

Then, run the build command to generate the CSS files:

.. code-block:: bash

    pysassc -t compressed -I bootstrap cove_ocds/sass/styles-ocds.sass cove_ocds/static/dataexplore/css/bootstrap-ocds.css

Finally, check the changes with runserver, as per usual.
