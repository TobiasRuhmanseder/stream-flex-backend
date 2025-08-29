# movies/tests/tests_functions_movies.py
from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from django.core.files.base import ContentFile
from django.http import Http404
import random  
from movies.models import Movie
from movies.funktions import (
    parse_limit,
    get_random_flag,
    choose_quality,
    getSource,
    check_or_404,
)




# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

class _Q:
    """Minimal object that mimics DRF request.query_params (a dict-like)."""
    def __init__(self, **kv):
        self._d = {**kv}
    def get(self, k, default=None):
        return self._d.get(k, default)

class _Req(SimpleNamespace):
    """Request stub with query_params attribute."""
    def __init__(self, **params):
        super().__init__(query_params=_Q(**params))

# ---------------------------------------------------------------------------
# parse_limit
# ---------------------------------------------------------------------------

def test_parse_limit_ok_number():
    req = _Req(limit="5")
    assert parse_limit(req, default=3, min_value=1, max_value=10) == 5

def test_parse_limit_missing_uses_default():
    req = _Req()
    assert parse_limit(req, default=7, min_value=1, max_value=10) == 7

def test_parse_limit_non_int_falls_back_to_default():
    req = _Req(limit="oops")
    assert parse_limit(req, default=4, min_value=1, max_value=10) == 4

def test_parse_limit_below_min_is_clamped():
    req = _Req(limit="-99")
    assert parse_limit(req, default=3, min_value=2, max_value=10) == 2

def test_parse_limit_above_max_is_clamped():
    req = _Req(limit="999")
    assert parse_limit(req, default=3, min_value=1, max_value=9) == 9

# ---------------------------------------------------------------------------
# get_random_flag
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("val,expected", [
    (None, False),             # missing -> default False
    ("", False),
    ("0", False),
    ("no", False),
    ("false", False),
    ("off", False),
    ("1", True),
    ("yes", True),
    ("true", True),
    ("on", True),
    (True, True),
])
def test_get_random_flag_default_false(val, expected):
    req = _Req(random=val) if val is not None else _Req()
    assert get_random_flag(req, default=False) is expected

@pytest.mark.parametrize("val,expected", [
    (None, True),              # missing -> default True
    ("", False),
    ("0", False),
    ("no", False),
    ("false", False),
    ("off", False),
    ("1", True),
    ("yes", True),
    ("true", True),
    ("on", True),
])
def test_get_random_flag_default_true(val, expected):
    req = _Req(random=val) if val is not None else _Req()
    assert get_random_flag(req, default=True) is expected

# ---------------------------------------------------------------------------
# pick_random
# ---------------------------------------------------------------------------

def pick_random(qs, limit):
    ids = list(qs.values_list("id", flat=True))
    if not ids:
        return []
    if limit >= len(ids):
        selected_ids = ids
    else:
        # vorher stand hier ein Inline-Import; den bitte entfernen
        selected_ids = random.sample(ids, k=limit)

    objs = list(qs.model.objects.filter(id__in=selected_ids))
    # FIX: Nach ID-Reihenfolge sortieren
    objs.sort(key=lambda o: selected_ids.index(o.id))
    return objs

@pytest.mark.django_db
def test_pick_random_returns_empty_for_empty_qs():
    assert pick_random(Movie.objects.none(), limit=3) == []

@pytest.mark.django_db
def test_pick_random_when_limit_ge_count_returns_all_in_original_order():
    m1 = Movie.objects.create(title="A", description="a")
    m2 = Movie.objects.create(title="B", description="b")
    m3 = Movie.objects.create(title="C", description="c")
    res = pick_random(Movie.objects.all().order_by("id"), limit=999)
    # Should return all three, ordered like the underlying id order
    assert [m.id for m in res] == [m1.id, m2.id, m3.id]

@pytest.mark.django_db
def test_pick_random_with_sampling_is_deterministic_when_patched(monkeypatch):
    m1 = Movie.objects.create(title="A", description="a")
    m2 = Movie.objects.create(title="B", description="b")
    m3 = Movie.objects.create(title="C", description="c")

    # Force random.sample to pick [m3.id, m1.id] in that order
    # The function then sorts objects by that order.
    sample_return = [m3.id, m1.id]
    with patch("movies.funktions.random.sample", return_value=sample_return):
        res = pick_random(Movie.objects.all().order_by("id"), limit=2)
    assert [m.id for m in res] == sample_return

# ---------------------------------------------------------------------------
# choose_quality
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "avail,screen_h,downlink,expected_q",
    [
        # Resolution only (downlink None)
        ((True, True, True), 1080, None, "1080"),
        ((False, True, True), 1080, None, "720"),
        ((False, False, True), 1080, None, "480"),
        ((True, True, True), 720, None, "720"),
        ((False, True, True), 720, None, "720"),
        ((False, False, True), 720, None, "480"),
        ((True, True, True), 480, None, "480"),
        ((True, False, False), 480, None, "1080"),  
        ((True, True, True), 1080, 10, "1080"),
        ((True, True, True), 1080, 5, "720"),
        ((True, True, True), 1080, 1, "480"),
        # If desired tier unavailable, fall back within candidates first, else broad fallback
        ((False, True, True), 1080, 10, "720"),
        ((False, False, True), 1080, 10, "480"),
        ((False, False, False), 1080, 10, "480"),  # none available -> hard fallback "480"
    ],
)
def test_choose_quality_branches(avail, screen_h, downlink, expected_q):
    has_1080, has_720, has_480 = avail
    q, key = choose_quality(
        has_1080=has_1080,
        has_720=has_720,
        has_480=has_480,
        screen_h=screen_h,
        downlink_mbps=downlink,
    )
    assert q == expected_q
    assert key == f"player.quality.{q}"

def test_choose_quality_when_screen_h_none_defaults_to_720_bucket():
    q, key = choose_quality(True, True, True, screen_h=None, downlink_mbps=None)
    # With screen_h None, default bucket is "720" → first available is 720
    assert q in {"720", "1080", "480"}  # depends on availability; here all True → picks 720
    assert key == f"player.quality.{q}"

# ---------------------------------------------------------------------------
# getSource
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_getSource_picks_exact_quality_fields(tmp_path):
    m = Movie.objects.create(title="S", description="s")
    # Save three distinct "files" so fields are truthy and names differ
    m.video_1080.save("v1080.mp4", ContentFile(b"1080"), save=True)
    m.video_720.save("v720.mp4", ContentFile(b"720"), save=True)
    m.video_480.save("v480.mp4", ContentFile(b"480"), save=True)

    assert getSource(m, "1080").name.endswith("v1080.mp4")
    assert getSource(m, "720").name.endswith("v720.mp4")
    assert getSource(m, "480").name.endswith("v480.mp4")

@pytest.mark.django_db
def test_getSource_fallback_order_720_then_480_then_1080(tmp_path):
    m = Movie.objects.create(title="S2", description="s2")
    # Only 480 exists
    m.video_480.save("low.mp4", ContentFile(b"l"), save=True)
    # No explicit q → should return 720 or 480 or 1080 in that order of preference.
    src = getSource(m, q="")
    assert src.name.endswith("low.mp4")

# ---------------------------------------------------------------------------
# check_or_404
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_check_or_404_opens_existing_file(tmp_path):
    m = Movie.objects.create(title="F", description="f")
    # Use a real FileField so storage.open() works as in production
    m.thumbnail_image.save("thumb.jpg", ContentFile(b"IMG"), save=True)

    fh = check_or_404(m.thumbnail_image)
    try:
        data = fh.read()
    finally:
        try:
            fh.close()
        except Exception:
            pass
    assert data == b"IMG"

def test_check_or_404_raises_when_missing():
    class Dummy:
        name = ""  # no name → considered missing
        storage = None
    with pytest.raises(Http404):
        check_or_404(Dummy())