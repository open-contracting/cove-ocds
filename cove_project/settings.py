import os
from pathlib import Path

from cove import settings

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parents[1]

# We use the setting to choose whether to show the section about Sentry in the
# terms and conditions
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import ignore_logger

    ignore_logger("django.security.DisallowedHost")
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()])

FATHOM = {
    "domain": os.getenv("FATHOM_ANALYTICS_DOMAIN", "cdn.usefathom.com"),
    "id": os.getenv("FATHOM_ANALYTICS_ID", ""),
}
HOTJAR = {
    "id": os.getenv("HOTJAR_ID", ""),
    "sv": os.getenv("HOTJAR_SV", ""),
    "date_info": os.getenv("HOTJAR_DATE_INFO", ""),
}
RELEASES_OR_RECORDS_TABLE_LENGTH = int(os.getenv("RELEASES_OR_RECORDS_TABLE_LENGTH", 25))
VALIDATION_ERROR_LOCATIONS_LENGTH = settings.VALIDATION_ERROR_LOCATIONS_LENGTH
VALIDATION_ERROR_LOCATIONS_SAMPLE = settings.VALIDATION_ERROR_LOCATIONS_SAMPLE
DELETE_FILES_AFTER_DAYS = int(os.getenv("DELETE_FILES_AFTER_DAYS", 90))

# We can't take MEDIA_ROOT and MEDIA_URL from cove settings,
# ... otherwise the files appear under the BASE_DIR that is the Cove library install.
# That could get messy. We want them to appear in our directory.
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

SECRET_KEY = os.getenv("SECRET_KEY", "7ur)dt+e%1^e6$8_sd-@1h67_5zixe2&39%r2$$8_7v6fr_7ee")
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
TEMPLATES[0]["DIRS"] = [BASE_DIR / "cove_project" / "templates"]
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "cove_project.context_processors.from_settings",
)

WSGI_APPLICATION = "cove_project.wsgi.application"

# We can't take DATABASES from cove settings,
# ... otherwise the files appear under the BASE_DIR that is the Cove library install.
# That could get messy. We want them to appear in our directory.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(BASE_DIR / "db.sqlite3")}}

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

LOCALE_PATHS = (BASE_DIR / "cove_ocds" / "locale",)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

# We can't take STATIC_URL and STATIC_ROOT from cove settings,
# ... otherwise the files appear under the BASE_DIR that is the Cove library install.
# and that doesn't work with our standard Apache setup.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

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
    "schema_version_choices": {
        # version: (display, url, tag),
        "1.0": ("1.0", "https://standard.open-contracting.org/1.0/{lang}/", "1__0__3"),
        "1.1": ("1.1", "https://standard.open-contracting.org/1.1/{lang}/", "1__1__5"),
    },
    "schema_codelists": {
        # version: codelist_dir,
        "1.1": "https://raw.githubusercontent.com/open-contracting/standard/1.1/schema/codelists/",
    },
    "root_list_path": "releases",
    "root_id": "ocid",
    "convert_titles": False,
    "input_methods": ["upload", "url", "text"],
    "input_template": "cove_ocds/input.html",
    "support_email": "data@open-contracting.org",
}

# Set default schema version to the latest version
COVE_CONFIG["schema_version"] = list(COVE_CONFIG["schema_version_choices"])[-1]

# Because of how the standard site proxies traffic, we want to use this
USE_X_FORWARDED_HOST = True

# https://docs.djangoproject.com/en/3.2/ref/settings/#data-upload-max-memory-size
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 5 MB
