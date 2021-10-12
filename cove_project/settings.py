import os
from collections import OrderedDict

import environ
from cove import settings

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = environ.Env(
    # set casting, default value
    DB_NAME=(str, os.path.join(BASE_DIR, "db.sqlite3")),
    FATHOM_ANALYTICS_DOMAIN=(str, "cdn.usefathom.com"),
    FATHOM_ANALYTICS_ID=(str, ""),
    HOTJAR_ID=(str, ""),
    HOTJAR_SV=(str, ""),
    HOTJAR_DATE_INFO=(str, ""),
    RELEASES_OR_RECORDS_TABLE_LENGTH=(int, 25),
    DELETE_FILES_AFTER_DAYS=(int, 90),
    SENTRY_DSN=(str, ''),
)

# We use the setting to choose whether to show the section about Sentry in the
# terms and conditions
SENTRY_DSN = env('SENTRY_DSN')

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import ignore_logger

    ignore_logger('django.security.DisallowedHost')
    sentry_sdk.init(
        dsn=env('SENTRY_DSN'),
        integrations=[DjangoIntegration()]
    )

FATHOM = {
    "domain": env("FATHOM_ANALYTICS_DOMAIN"),
    "id": env("FATHOM_ANALYTICS_ID"),
}
HOTJAR = {
    "id": env("HOTJAR_ID"),
    "sv": env("HOTJAR_SV"),
    "date_info": env("HOTJAR_DATE_INFO"),
}
RELEASES_OR_RECORDS_TABLE_LENGTH = env("RELEASES_OR_RECORDS_TABLE_LENGTH")
VALIDATION_ERROR_LOCATIONS_LENGTH = settings.VALIDATION_ERROR_LOCATIONS_LENGTH
VALIDATION_ERROR_LOCATIONS_SAMPLE = settings.VALIDATION_ERROR_LOCATIONS_SAMPLE
DELETE_FILES_AFTER_DAYS = env("DELETE_FILES_AFTER_DAYS")

# We can't take MEDIA_ROOT and MEDIA_URL from cove settings,
# ... otherwise the files appear under the BASE_DIR that is the Cove library install.
# That could get messy. We want them to appear in our directory.
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

SECRET_KEY = settings.SECRET_KEY
DEBUG = settings.DEBUG
ALLOWED_HOSTS = settings.ALLOWED_HOSTS

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bootstrap3",
    "cove",
    "cove.input",
    "cove_ocds",
]


MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "cove.middleware.CoveConfigCurrentApp",
)


ROOT_URLCONF = "cove_project.urls"

TEMPLATES = settings.TEMPLATES
TEMPLATES[0]["DIRS"] = [os.path.join(BASE_DIR, "cove_project", "templates")]
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "cove_project.context_processors.from_settings",
)

WSGI_APPLICATION = "cove_project.wsgi.application"

# We can't take DATABASES from cove settings,
# ... otherwise the files appear under the BASE_DIR that is the Cove library install.
# That could get messy. We want them to appear in our directory.
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": env("DB_NAME")}
}

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = settings.LANGUAGE_CODE
TIME_ZONE = settings.TIME_ZONE
USE_I18N = settings.USE_I18N
USE_L10N = settings.USE_L10N
USE_TZ = settings.USE_TZ

LANGUAGES = settings.LANGUAGES

LOCALE_PATHS = (os.path.join(BASE_DIR, "cove_ocds", "locale"),)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

# We can't take STATIC_URL and STATIC_ROOT from cove settings,
# ... otherwise the files appear under the BASE_DIR that is the Cove library install.
# and that doesn't work with our standard Apache setup.
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Misc

LOGGING = settings.LOGGING
LOGGING["handlers"]["null"] = {
    "class": "logging.NullHandler",
}
LOGGING["loggers"]["django.security.DisallowedHost"] = {
    "handlers": ["null"],
    "propagate": False,
}

# OCDS Config

COVE_CONFIG = {
    "app_name": "cove_ocds",
    "app_base_template": "cove_ocds/base.html",
    "app_verbose_name": "Open Contracting Data Review Tool",
    "app_strapline": "Review your OCDS data.",
    "schema_name": {
        "release": "release-package-schema.json",
        "record": "record-package-schema.json",
    },
    "schema_item_name": "release-schema.json",
    "schema_host": None,
    "schema_version_choices": OrderedDict(
        (  # {version: (display, url)}
            ("1.0", ("1.0", "https://standard.open-contracting.org/1.0/{lang}/")),
            ("1.1", ("1.1", "https://standard.open-contracting.org/1.1/{lang}/")),
        )
    ),
    "schema_codelists": OrderedDict(
        (  # {version: codelist_dir}
            (
                "1.1",
                "https://raw.githubusercontent.com/open-contracting/standard/1.1/schema/codelists/",
            ),
        )
    ),
    "root_list_path": "releases",
    "root_id": "ocid",
    "convert_titles": False,
    "input_template": "cove_ocds/input.html",
    "input_methods": ["upload", "url", "text"],
    "support_email": "data@open-contracting.org",
}

# Set default schema version to the latest version
COVE_CONFIG["schema_version"] = list(COVE_CONFIG["schema_version_choices"].keys())[-1]

URL_PREFIX = r"review/"

# Because of how the standard site proxies traffic, we want to use this
USE_X_FORWARDED_HOST = True

# https://docs.djangoproject.com/en/3.2/ref/settings/#data-upload-max-memory-size
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 5 MB
