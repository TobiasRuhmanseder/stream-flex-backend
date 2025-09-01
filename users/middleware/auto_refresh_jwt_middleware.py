# users/middleware/auto_refresh_jwt.py
from datetime import datetime, timezone
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

DEFAULT_EXEMPT_PREFIXES = (
    "/admin",
    "/static",
    "/media",
    "/favicon.ico",
    "/api/users/login",
    "/api/users/logout",
    "/api/users/refresh",
    "/api/users/verify-email/" 
    "/api/users/csrf",   
)


class AutoRefreshJWTMiddleware(MiddlewareMixin):
    """
    Only handle Access/Refresh cookies:
    - If Access is valid => do nothing
    - If Access is missing/expired + Refresh is valid => create new Access (request + cookie)
    - If Refresh is invalid => delete cookies on response
    - Never block the request
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        sj = settings.SIMPLE_JWT
        self.access_name = sj["AUTH_COOKIE"]
        self.refresh_name = sj["AUTH_REFRESH_COOKIE"]
        self.cookie_path = sj.get("AUTH_COOKIE_PATH", "/")
        self.cookie_domain = sj.get("AUTH_COOKIE_DOMAIN", None)
        self.cookie_secure = bool(sj.get("AUTH_COOKIE_SECURE", True))
        self.cookie_samesite = sj.get("AUTH_COOKIE_SAMESITE", "Lax")
        self.cookie_maxage = sj.get("ACCESS_TOKEN_LIFETIME", None)
        self.exempt_prefixes = tuple(
            getattr(settings, "JWT_MW_EXEMPT_PATH_PREFIXES",
                    DEFAULT_EXEMPT_PREFIXES)
        )

    # ---------- helpers ----------
    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.exempt_prefixes)

    def _now_ts(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    def _delete_auth_cookies(self, response):
        params = dict(path=self.cookie_path,
                      domain=self.cookie_domain, samesite=self.cookie_samesite)
        response.delete_cookie(self.access_name, **params)
        response.delete_cookie(self.refresh_name, **params)

    # ---------- main ----------
    def process_request(self, request):
        if self._is_exempt(request.path):
            return None

        access_tok = request.COOKIES.get(self.access_name)
        refresh_tok = request.COOKIES.get(self.refresh_name)

        if access_tok:
            try:
                at = AccessToken(access_tok)
                # gültig?
                if int(at["exp"]) > self._now_ts():
                    return None
            except TokenError:
                pass

        if not refresh_tok:
            return None

        try:
            rt = RefreshToken(refresh_tok)
            new_access = rt.access_token
        except TokenError:
            request._invalidate_auth_cookies = True
            return None

        request._new_access_token = str(new_access)
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {request._new_access_token}"
        return None

    def process_response(self, request, response):
        if getattr(request, "_invalidate_auth_cookies", False):
            self._delete_auth_cookies(response)
            return response

        if getattr(request, "_new_access_token", None):
            response.set_cookie(
                key=self.access_name,
                value=request._new_access_token,
                max_age=self.cookie_maxage,
                httponly=True,
                secure=self.cookie_secure,
                samesite=self.cookie_samesite,
                domain=self.cookie_domain,
                path=self.cookie_path,
            )
        return response
