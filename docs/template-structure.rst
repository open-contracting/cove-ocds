Template structure
==================

The DRT uses `Django templating <https://docs.djangoproject.com/en/4.2/topics/templates/>`_. Generic templates are defined in `lib-cove-web <https://github.com/opendataservices/lib-cove-web>`_ and include various blocks which can be overridden here if necessary.

In lib-cove-web you will find:

* The base template for the landing page.
* Include templates for data input and tables for the results.
* Various error pages.
* Terms and conditions, usage statistics, analytics.

In cove-ocds (this repo) you will find specializations of these, either some blocks or entire templates.

* The base, input, and some of the result table templates customize text and appearance for the OCDS DRT.
* ``explore_base``, ``explore_record`` and ``explore_release`` modify the base ``explore`` template depending on the data input.
* Additional template partials which are included in other templates.
