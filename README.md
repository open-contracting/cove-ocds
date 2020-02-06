# OCDS Data Review Tool

The DRT is a web application that allows you to review Open Contracting data, validate it against the Open Contracting Data Standard, and review it for errors or places for improvement. You can also use it to covert data between JSON and Excel spreadsheet formats.

It runs at [standard.open-contracting.org/review/](https://standard.open-contracting.org/review/).

## Running it locally

* Clone the repository
* Change into the cloned repository
* Create a virtual environment (note this application uses python3)
* Activate the virtual environment
* Install dependencies
* Set up the database (sqlite3)
* Compile the translations
* Run the development server

```
git clone https://github.com/open-contracting/cove-ocds.git
cd cove-ocds
python3 -m venv .ve
source .ve/bin/activate
pip install -r requirements_dev.txt
python manage.py migrate
python manage.py compilemessages
python manage.py runserver 0.0.0.0:8000
```

## Commandline interface

You can pass a JSON file for review to the DRT at the commandline after installing it in a virtual environment.

```
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
```

## Development

Please see the [Developer Documentation](#).

## Translations

For more information about Django's translation framework, see https://docs.djangoproject.com/en/1.8/topics/i18n/translation/

If you add new text to the interface, ensure to wrap it in the relevant gettext blocks/functions.

In order to generate messages and post them on Transifex:

First check the `Transifex lock <https://opendataservices.plan.io/projects/co-op/wiki/CoVE_Transifex_lock>`, because only one branch can be translated on Transifex at a time.

Then:

    python manage.py makemessages -l en
    tx push -s

In order to fetch messages from transifex:

    tx pull -a

In order to compile them:

    python manage.py compilemessages

Keep the makemessages and pull messages steps in thier own commits seperate from the text changes.

To check that all new text is written so that it is able to be translated you could install and run `django-template-i18n-lint`

    pip install django-template-i18n-lint
    django-template-i18n-lint cove
