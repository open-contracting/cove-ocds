Translations
============

The OCDS DRT uses `Django's translation framework <https://docs.djangoproject.com/en/4.2/topics/i18n/translation/>`_. This means you should wrap text in templates in ``{% trans 'Text to translate' %}`` tags and human readable strings embedded in code should be wrapped with ``_('text to translate')``.

When new strings are added or existing ones edited, extract them and push them to Transifex for translation:

.. code:: bash

    python manage.py makemessages -l en --ignore "docs"
    tx push -s

In order to fetch translated strings from Transifex:

.. code:: bash

    tx pull -a

In order to compile them:

.. code:: bash

    python manage.py compilemessages

Keep the makemessages and pull messages steps in their own commits separate from the text changes.

To check that all new text is written so that it is able to be translated you could install and run ``django-template-i18n-lint``

.. code:: bash

    pip install django-template-i18n-lint
    django-template-i18n-lint cove

Translatable strings may also be found in lib-cove-web. If a new language is added for the OCDS DRT, the strings in lib-cove-web will also need to be translated.

