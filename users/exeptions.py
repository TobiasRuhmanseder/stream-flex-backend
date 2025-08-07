from rest_framework.exceptions import APIException

class AccountNotActivated(APIException):
    status_code = 403
    default_detail = 'Your account is not activated yet.'
    default_code = 'account_not_activated'