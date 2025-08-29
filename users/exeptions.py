from rest_framework.exceptions import APIException


class AccountNotActivated(APIException):
    """Exception raised when a user's account has not been activated yet."""
    status_code = 403
    default_detail = "Your account is not activated yet."
    default_code = "account_not_activated"
