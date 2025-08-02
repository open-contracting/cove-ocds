from http import HTTPStatus


class DataReviewToolError(Exception):
    """Base class for exceptions from within this module."""


class InputError(DataReviewToolError):
    """Raised if the input data is irretriavable or unprocessabe."""

    def __init__(self, message="", heading="", status=HTTPStatus.OK):
        self.message = message
        self.heading = heading
        self.status = status
