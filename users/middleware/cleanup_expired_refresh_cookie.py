from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

class CleanupExpiredRefreshCookie(MiddlewareMixin):
    def process_response(self, request, response):
        name = settings.SIMPLE_JWT["AUTH_REFRESH_COOKIE"]
        tok = request.COOKIES.get(name)
        if not tok:
            return response
        try:
            RefreshToken(tok)
        except TokenError:
            params = dict(
                path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
                domain=settings.SIMPLE_JWT.get("AUTH_COOKIE_DOMAIN", None),
                samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
            )
            response.delete_cookie(settings.SIMPLE_JWT["AUTH_REFRESH_COOKIE"], **params)
            response.delete_cookie(settings.SIMPLE_JWT["AUTH_COOKIE"], **params)
        return response