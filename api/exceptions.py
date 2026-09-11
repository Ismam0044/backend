from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class ApiValidationError(APIException):
    """A 400 error with a stable machine-readable `code` the Flutter app can branch
    on (e.g. "insufficient_stock"), instead of string-matching `detail`."""

    status_code = 400
    default_code = "validation_error"

    def __init__(self, detail, code=None):
        super().__init__(detail={"detail": detail, "code": code or self.default_code})


def api_exception_handler(exc, context):
    """DRF's default handler first, then normalize anything that isn't already
    {"detail": ..., "code": ...}-shaped. Serializer field-error dicts are left
    alone - mobile forms want field-level messages, not a flattened envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(response.data, dict) and "detail" in response.data and len(response.data) <= 2:
        return response  # already {"detail": ...} or {"detail": ..., "code": ...}

    if isinstance(response.data, (list, dict)):
        response.data = {"detail": response.data, "code": exc.__class__.__name__}
    return response
