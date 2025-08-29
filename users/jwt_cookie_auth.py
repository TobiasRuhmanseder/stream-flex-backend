from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions
from rest_framework_simplejwt.exceptions import InvalidToken


def enforce_csrf(request):
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


class CustomAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)

        if header is None:
            raw_token = request.COOKIES.get("access_token")
        else:
            raw_token = self.get_raw_token(header)

        if not raw_token:
            return None
        try:
            validated = self.get_validated_token(raw_token)
        except InvalidToken:
            return None

        if request.method not in ("GET", "HEAD", "OPTIONS"):
            enforce_csrf(request)

        return self.get_user(validated), validated




#
# class CustomAuthentication(JWTAuthentication):
#     def authenticate(self, request):
#         header = self.get_header(request)
        
#         if header is None:
#             raw_token = request.COOKIES.get("access_token")
#         else:
#             raw_token = self.get_raw_token(header)
#         if not raw_token:
#             return None
#         validated = self.get_validated_token(raw_token)
#         enforce_csrf(request)
#         return self.get_user(validated), validated
