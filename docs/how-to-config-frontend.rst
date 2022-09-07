How to replace something hardcoded in the frontend with a configurable variable
================================================================================

Pick a name for the environment variable you want to configure cove with. In this example we use `MY_ENV_VAR`.

Edit `cove_project/settings.py`.

First, and add a line to the `environ.Env`:

.. code:: python

    env = environ.Env(
	# set casting, default value
	DB_NAME=(str, str(BASE_DIR / "db.sqlite3")),
	HOTJAR_ID=(str, ""),
	HOTJAR_SV=(str, ""),
	...
	MY_ENV_VAR=(int, 0),
    )

You must set a casting function (usually `str` or `int`, we've picked `int` for this example), and a default value (we've picked `0`).

Next, map this to a variable within the settings file. Often this will have the same name as the environment variable:

.. code:: python

    MY_ENV_VAR = env("MY_ENV_VAR")


Edit `cove_project/context_processors.py`, and add a mapping between the setting name, and what name you want use in the template: we've picked `my_var`.

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
