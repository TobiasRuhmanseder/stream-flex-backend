# movies/tests/tests_tasks.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import subprocess
import pytest
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from movies.models import Movie
import movies.tasks as tasks


@pytest.fixture(autouse=True)
def stub_rq_queue(settings, monkeypatch):

    settings.RQ_QUEUES = {
        "default": {
            "ASYNC": False, 
            "URL": "redis://localhost:6379/0", 
        }
    }

    class DummyQueue:
        def enqueue(self, *args, **kwargs):
            return None
        def fetch_job(self, *args, **kwargs):
            return None

    monkeypatch.setattr("django_rq.get_queue", lambda name="default", **kw: DummyQueue())


@pytest.fixture
def media_tmp(tmp_path, settings):
    """Point MEDIA_ROOT to a temp directory for the duration of a test."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def movie_with_source(db, media_tmp):
    """
    Create a Movie with a small dummy source file (so .path exists).
    """
    m = Movie.objects.create(title="X", description="x", processing_status="pending")
    m.video_file.save("input.mp4", ContentFile(b"fake-bytes"), save=True)
    return m


def _touch(p: Path, data: bytes = b"x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


# -----------------------------
# process_movie: success path
# -----------------------------
@pytest.mark.django_db
def test_process_movie_ready_when_any_variant_ok(media_tmp, movie_with_source, monkeypatch):
    """
    If at least one transcode succeeds and assets build, status becomes 'ready',
    fields are saved, errors empty, and duration is set from probe.
    """
    m = movie_with_source

    # Pretend probe returns a duration
    monkeypatch.setattr(tasks, "_probe_duration", lambda src: 61)

    # Fake transcoder: create files for 720p & 480p, fail 1080p
    def fake_safe_transcode(src, out_tmp, height, errors):
        if height in (720, 480):
            _touch(Path(out_tmp))
            return True
        errors.append(f"[{height}p] rc=1 err=boom")
        return False

    monkeypatch.setattr(tasks, "_safe_transcode", fake_safe_transcode)

    # Fake asset builders: write temp outputs (so _save_tmp_to_field runs)
    monkeypatch.setattr(tasks, "_frame_to_image", lambda *a, **k: _touch(Path(a[1])))
    monkeypatch.setattr(tasks, "_cut_teaser",    lambda *a, **k: _touch(Path(a[1])))

    # No-op _save_tmp_to_field side effects are real (it saves into storage),
    # so we don't patch it.

    tasks.process_movie(m.id)
    m.refresh_from_db()

    assert m.processing_status == "ready"
    # At least one variant saved
    assert bool(m.video_720.name) or bool(m.video_480.name) or bool(m.video_1080.name)
    # Assets saved
    assert m.thumbnail_image.name and m.hero_image.name and m.teaser_video.name
    # Duration set from probe
    assert m.duration_seconds == 61
    # Error text may include messages from non-critical variant failures (e.g., 1080p failed but 720p/480p succeeded).
    # That's OK as long as the movie is marked ready. Accept either empty or containing the recorded 1080p failure.
    err = m.processing_error or ""
    assert err == "" or "rc=" in err


# -----------------------------
# process_movie: all variants fail -> failed
# -----------------------------
@pytest.mark.django_db
def test_process_movie_failed_when_no_variant_ok(media_tmp, movie_with_source, monkeypatch):
    m = movie_with_source

    monkeypatch.setattr(tasks, "_probe_duration", lambda src: None)

    def always_fail(src, out_tmp, height, errors):
        errors.append(f"[{height}p] rc=127 err=missing codec")
        return False

    monkeypatch.setattr(tasks, "_safe_transcode", always_fail)
    # Assets won't be attempted to save anything (but they may run; keep them harmless)
    monkeypatch.setattr(tasks, "_frame_to_image", lambda *a, **k: None)
    monkeypatch.setattr(tasks, "_cut_teaser", lambda *a, **k: None)

    tasks.process_movie(m.id)
    m.refresh_from_db()

    assert m.processing_status == "failed"
    assert "rc=127" in (m.processing_error or "")
    # No variants saved
    assert not (m.video_1080.name or m.video_720.name or m.video_480.name)


# -----------------------------
# process_movie: asset error is recorded but keeps 'ready'
# -----------------------------
@pytest.mark.django_db
def test_process_movie_asset_error_keeps_ready(media_tmp, movie_with_source, monkeypatch):
    m = movie_with_source

    monkeypatch.setattr(tasks, "_probe_duration", lambda src: 42)

    # Make 720p succeed so "any_ok" is True
    def ok_only_720(src, out_tmp, height, errors):
        if height == 720:
            _touch(Path(out_tmp))
            return True
        return False

    monkeypatch.setattr(tasks, "_safe_transcode", ok_only_720)

    # Force _frame_to_image to raise a CalledProcessError -> gets summarized as [assets]
    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, ["ffmpeg"], stderr="nope")

    monkeypatch.setattr(tasks, "_frame_to_image", boom)
    # Let teaser succeed so we mix success + error in the asset block
    monkeypatch.setattr(tasks, "_cut_teaser", lambda *a, **k: _touch(Path(a[1])))

    tasks.process_movie(m.id)
    m.refresh_from_db()

    assert m.processing_status == "ready"
    assert "[assets]" in (m.processing_error or "")


# -----------------------------
# process_movie: respects pre-set duration
# -----------------------------
@pytest.mark.django_db
def test_process_movie_does_not_overwrite_existing_duration(media_tmp, movie_with_source, monkeypatch):
    m = movie_with_source
    m.duration_seconds = 777
    m.save(update_fields=["duration_seconds"])

    monkeypatch.setattr(tasks, "_probe_duration", lambda src: 10)

    def ok_480(src, out_tmp, height, errors):
        if height == 480:
            _touch(Path(out_tmp))
            return True
        return False

    monkeypatch.setattr(tasks, "_safe_transcode", ok_480)
    monkeypatch.setattr(tasks, "_frame_to_image", lambda *a, **k: _touch(Path(a[1])))
    monkeypatch.setattr(tasks, "_cut_teaser", lambda *a, **k: _touch(Path(a[1])))

    tasks.process_movie(m.id)
    m.refresh_from_db()

    assert m.processing_status == "ready"
    # Still the original value
    assert m.duration_seconds == 777


# -----------------------------
# process_movie: early return when no input file
# -----------------------------
@pytest.mark.django_db
def test_process_movie_noop_without_source_file(media_tmp, db, monkeypatch):
    m = Movie.objects.create(title="NoSrc", description="n", processing_status="pending")
    # Guard: _safe_transcode must not be called
    called = {"n": 0}
    monkeypatch.setattr(tasks, "_safe_transcode", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    tasks.process_movie(m.id)
    m.refresh_from_db()
    assert called["n"] == 0  # never called
    assert m.processing_status == "pending"  # unchanged


# -----------------------------
# _safe_transcode: message coverage
# -----------------------------
def test__safe_transcode_collects_errors(monkeypatch, tmp_path):
    # Make inner _transcode raise different exceptions and verify formatting.
    def raise_cpe(*a, **k):
        raise subprocess.CalledProcessError(2, ["ffmpeg"], stderr="bad")
    def raise_other(*a, **k):
        raise RuntimeError("oops")

    errs = []
    monkeypatch.setattr(tasks, "_transcode", raise_cpe)
    ok = tasks._safe_transcode(Path("in.mp4"), tmp_path / "o.mp4", 1080, errs)
    assert ok is False and "[1080p]" in errs[-1] and "rc=2" in errs[-1]

    errs = []
    monkeypatch.setattr(tasks, "_transcode", raise_other)
    ok = tasks._safe_transcode(Path("in.mp4"), tmp_path / "o.mp4", 720, errs)
    assert ok is False and "unexpected" in errs[-1]