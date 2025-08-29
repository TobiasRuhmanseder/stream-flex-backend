# users/test_email_functions.py
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from django.contrib.auth import get_user_model

from users import functions as fns

User = get_user_model()


@pytest.mark.django_db
def test_ensure_email_verification_token_creates_when_missing():
    u = User.objects.create_user(username="a@b.com", email="a@b.com", password="x")
    # Fall 1: kein Token -> Methode soll eins erzeugen
    u.email_verification_token = ""
    u.save()
    # mocke generate_email_verification_token, damit wir keinen echten Algo brauchen
    with patch.object(u, "generate_email_verification_token") as gen:
        token = fns.ensure_email_verification_token(u)
        gen.assert_called_once()
        assert token == u.email_verification_token


@pytest.mark.django_db
def test_ensure_email_verification_token_returns_existing():
    u = User.objects.create_user(username="c@d.com", email="c@d.com", password="x")
    u.email_verification_token = "EXISTING"
    u.save()
    with patch.object(u, "generate_email_verification_token") as gen:
        token = fns.ensure_email_verification_token(u)
        gen.assert_not_called()
        assert token == "EXISTING"


@pytest.mark.django_db
@override_settings(FRONTEND_URL="http://frontend.example")
def test_build_verify_url_uses_frontend_and_token():
    u = User.objects.create_user(username="e@f.com", email="e@f.com", password="x")
    u.email_verification_token = "T123"
    url = fns.build_verify_url(u)
    assert url.startswith("http://frontend.example/home/verify-email?")
    assert "token=T123" in url
    assert "email=e%40f.com" in url  # URL-encoded


@pytest.mark.django_db
def test_render_verification_bodies_prefers_text_and_fallsback_to_strip_html():
    u = User.objects.create_user(username="g@h.com", email="g@h.com", password="x")
    verify_url = "http://x/verify?token=1"

    # 1) Beide Templates liefern Inhalte
    with patch("users.functions.render_to_string") as r2s:
        r2s.side_effect = ["TEXTCONTENT", "<b>HTML</b>"]
        subject, text_body, html_body = fns.render_verification_bodies(u, verify_url)
        assert subject.startswith("Please confirm")
        assert text_body == "TEXTCONTENT"
        assert html_body == "<b>HTML</b>"

    # 2) Text leer -> fallback auf strip_tags(html)
    with patch("users.functions.render_to_string") as r2s:
        r2s.side_effect = ["   ", "<b>HTML</b>"]
        subject, text_body, html_body = fns.render_verification_bodies(u, verify_url)
        assert text_body == "HTML"  # strip_tags entfernt <b>


@pytest.mark.django_db
@override_settings(DEFAULT_FROM_EMAIL="no-reply@example.com")
def test_send_verification_email_builds_and_sends_message():
    u = User.objects.create_user(username="i@j.com", email="i@j.com", password="x")
    u.email_verification_token = "VVV"
    with (
        patch("users.functions.render_to_string") as r2s,
        patch("users.functions.EmailMultiAlternatives") as EMA,
    ):
        # zwei Render-Aufrufe für txt + html
        r2s.side_effect = ["TXT", "<p>HTML</p>"]
        msg = MagicMock()
        EMA.return_value = msg

        fns.send_verification_email(u)

        EMA.assert_called_once()
        msg.attach_alternative.assert_called_once_with("<p>HTML</p>", "text/html")
        msg.send.assert_called_once()


@pytest.mark.django_db
@override_settings(FRONTEND_URL="http://frontend.example")
def test_build_password_reset_url_contains_uid_and_token():
    u = User.objects.create_user(username="k@l.com", email="k@l.com", password="x")
    url = fns.build_password_reset_url(u)
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    assert parsed.path.endswith("/home/password-reset")
    params = parse_qs(parsed.query)
    assert "uid" in params and params["uid"][0]
    assert "token" in params and params["token"][0]
    assert "email" in params and params["email"][0]


@pytest.mark.django_db
def test_render_password_reset_bodies_with_fallback():
    u = User.objects.create_user(username="m@n.com", email="m@n.com", password="x")
    reset_url = "http://x/reset?uid=1&token=2"
    # 1) normal
    with patch("users.functions.render_to_string") as r2s:
        r2s.side_effect = ["TXT", "<i>HTML</i>"]
        subject, txt, html = fns.render_password_reset_bodies(u, reset_url)
        assert subject.startswith("Reset your password")
        assert txt == "TXT"
        assert html == "<i>HTML</i>"

    # 2) Text leer -> fallback strip_tags
    with patch("users.functions.render_to_string") as r2s:
        r2s.side_effect = ["", "<i>HTML</i>"]
        subject, txt, html = fns.render_password_reset_bodies(u, reset_url)
        assert txt == "HTML"


@pytest.mark.django_db
@override_settings(DEFAULT_FROM_EMAIL="no-reply@example.com")
def test_send_password_reset_email_sends_message():
    u = User.objects.create_user(username="o@p.com", email="o@p.com", password="x")
    with (
        patch("users.functions.render_to_string") as r2s,
        patch("users.functions.EmailMultiAlternatives") as EMA,
    ):
        r2s.side_effect = ["TXT_RESET", "<p>HTML_RESET</p>"]
        msg = MagicMock()
        EMA.return_value = msg

        fns.send_password_reset_email(u)

        EMA.assert_called_once()
        msg.attach_alternative.assert_called_once_with("<p>HTML_RESET</p>", "text/html")
        msg.send.assert_called_once()


@pytest.mark.django_db
def test_ensure_email_verification_token_no_change_if_exists():
    u = User.objects.create_user(username="existing@token.com", email="existing@token.com", password="x")
    u.email_verification_token = "ALREADY_SET"
    u.save()
    with patch.object(u, "generate_email_verification_token") as gen:
        token = fns.ensure_email_verification_token(u)
        gen.assert_not_called()
        assert token == "ALREADY_SET"


@pytest.mark.django_db
def test_build_verify_url_encodes_token_and_email():
    u = User.objects.create_user(username="user+test@example.com", email="user+test@example.com", password="x")
    u.email_verification_token = "token+with+plus"
    url = fns.build_verify_url(u)
    assert "token=token%2Bwith%2Bplus" in url
    assert "email=user%2Btest%40example.com" in url


@pytest.mark.django_db
@override_settings(DEFAULT_FROM_EMAIL="no-reply@example.com")
def test_send_verification_email_renders_and_sends():
    u = User.objects.create_user(username="send@verify.com", email="send@verify.com", password="x")
    u.email_verification_token = "VERIFYTOKEN"
    with patch("users.functions.render_to_string") as r2s, patch("users.functions.EmailMultiAlternatives") as EMA:
        r2s.side_effect = ["Plain text body", "<html>HTML body</html>"]
        msg = MagicMock()
        EMA.return_value = msg

        fns.send_verification_email(u)

        assert r2s.call_count == 2  # text + html bodies only
        EMA.assert_called_once()
        msg.attach_alternative.assert_called_once_with("<html>HTML body</html>", "text/html")
        msg.send.assert_called_once()


@pytest.mark.django_db
@override_settings(DEFAULT_FROM_EMAIL="no-reply@example.com")
def test_send_password_reset_email_passes_correct_args():
    u = User.objects.create_user(username="send@reset.com", email="send@reset.com", password="x")
    with patch("users.functions.render_to_string") as r2s, patch("users.functions.EmailMultiAlternatives") as EMA:
        r2s.side_effect = ["Reset text body", "<html>Reset HTML body</html>"]
        msg = MagicMock()
        EMA.return_value = msg

        fns.send_password_reset_email(u)

        assert r2s.call_count == 2  # text + html bodies only
        EMA.assert_called_once()
        msg.attach_alternative.assert_called_once_with("<html>Reset HTML body</html>", "text/html")
        msg.send.assert_called_once()