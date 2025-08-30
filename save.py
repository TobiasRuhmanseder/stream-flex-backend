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
