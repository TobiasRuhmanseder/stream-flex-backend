from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions
from rest_framework_simplejwt.exceptions import InvalidToken


# auth.py (oder wo deine CustomAuthentication liegt)
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.authentication import get_authorization_header

SAFE_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")


def enforce_csrf(request):
    """
    Führt denselben CSRF-Check aus wie Djangos CsrfViewMiddleware.
    Nur für Cookie-basierte Auth bei unsicheren Methoden.
    """
    # CsrfViewMiddleware benötigt get_response
    csrf_mw = CsrfViewMiddleware(lambda req: None)
    # process_request ist optional; der eigentliche Check passiert in process_view
    reason = csrf_mw.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


class CustomAuthentication(JWTAuthentication):
    """
    JWTAuth:
    - Zuerst Authorization-Header auswerten (Bearer). -> kein CSRF nötig.
    - Wenn kein Header: JWT aus Cookie 'access_token' lesen. -> CSRF für unsichere Methoden erzwingen.
    """


class CustomAuthentication(JWTAuthentication):
    """
    JWT im Header: kein CSRF nötig.
    JWT im Cookie 'access_token': bei unsicheren Methoden CSRF erzwingen.
    """
    def authenticate(self, request):
        header = self.get_header(request)
        raw_token = None
        token_source = None  # 'header' | 'cookie'

        if header:
            raw_token = self.get_raw_token(header)
            token_source = "header"
        else:
            raw_token = request.COOKIES.get("access_token")
            token_source = "cookie" if raw_token else None

        if not raw_token:
            return None

        try:
            validated = self.get_validated_token(raw_token)
        except Exception:
            return None

        if token_source == "cookie" and request.method not in SAFE_METHODS:
            enforce_csrf(request)

        return (self.get_user(validated), validated)


# def enforce_csrf(request):
#     """
#     Run a CSRF check on unsafe HTTP methods and raise an error if the check fails.
#     """
#     if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
#         return
#     check = CSRFCheck(lambda req: None)
#     check.process_request(request)
#     reason = check.process_view(request, None, (), {})
#     if reason:
#         raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


# class CustomAuthentication(JWTAuthentication):
#     """
#     Extends JWTAuthentication to also read tokens from cookies and enforce CSRF for unsafe methods.
#     """
#     def authenticate(self, request):
#         """
#         Check header or cookie for token, validate it, run CSRF check if needed, and return user and token.
#         """
#         header = self.get_header(request)

#         if header is None:
#             raw_token = request.COOKIES.get("access_token")
#         else:
#             raw_token = self.get_raw_token(header)

#         if not raw_token:
#             return None
#         try:
#             validated = self.get_validated_token(raw_token)
#         except InvalidToken:
#             return None

#         if request.method not in ("GET", "HEAD", "OPTIONS"):
#             enforce_csrf(request)

#         return self.get_user(validated), validated


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
