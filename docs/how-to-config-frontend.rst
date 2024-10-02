How to replace frontend hardcoding with a configurable variable
===============================================================

Pick a name for the environment variable you want to configure cove with. In this example we use `MY_ENV_VAR`.

Edit `core/settings.py`, and add a setting. The setting's name typically matches the environment variable's name. Set a default value, if appropriate. For example:

.. code:: python

    MY_ENV_VAR = os.getenv("MY_ENV_VAR", "default value")


Edit `core/context_processors.py`, and add a mapping between the setting name, and what name you want use in the template: we've picked `my_var`.

.. code:: python

    def from_settings(request):
	return {
	    'hotjar': settings.HOTJAR,
            ...
	    'my_var': settings.MY_ENV_VAR,
	}

Edit a template, and use the variable, e.g.:

.. code:: django

    My var is: {{ my_var }}
    {% if my_var > 5 %}Big{% endif %}
