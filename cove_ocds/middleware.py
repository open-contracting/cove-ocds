from http import HTTPStatus

from django.shortcuts import render
from django.utils.translation import gettext as _

from cove_ocds.exceptions import InputError


class ExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, InputError):
            return None

        return render(
            request,
            "error.html",
            {
                "heading": exception.heading,
                "message": exception.message,
                "link_text": _("Go to Home page") if exception.status == HTTPStatus.NOT_FOUND else _("Try Again"),
            },
            status=exception.status,
        )
