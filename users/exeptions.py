from rest_framework.exceptions import APIException

class AccountNotActivated(APIException):
    status_code = 403
    defaul_detail = 'Your account is not activated yet.'
    default_code = 'account not activated'