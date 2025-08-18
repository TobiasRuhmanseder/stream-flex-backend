# movies/tasks.py
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, List

from django.conf import settings
from django.core.files import File
from django.db import transaction

from .models import Movie

# Binaries must be available in the container PATH
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


# -----------------------------
# Low-level helpers
# -----------------------------

def _run(cmd: list[str]) -> None:
    """
    Run a subprocess and raise with captured stderr on non-zero exit.
    """
    proc = subprocess.run(
        cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr
        )


def _probe_duration(src: Path) -> Optional[int]:
    """
    Return media duration (seconds) using ffprobe, or None if unknown.
    """
    try:
        cmd = [
            FFPROBE,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1",
            str(src),
        ]
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return int(float(proc.stdout.strip()))
    except Exception:
        return None


def _transcode(src: Path, out_tmp: Path, height: int) -> None:
    """
    Transcode to MP4 (H.264/AAC), fixed height, keep aspect ratio (no padding),
    even width, normalized SAR. Use a temp path (`out_tmp`).
    """
    out_tmp.parent.mkdir(parents=True, exist_ok=True)
    # Robust: compute even width from output height (oh) & aspect (a)
    vf = f"scale=trunc(oh*a/2)*2:{height},setsar=1"
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-vf", vf,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(out_tmp),
    ]
    _run(cmd)


def _safe_transcode(src: Path, out_tmp: Path, height: int, errors: List[str]) -> bool:
    """
    Transcode a single variant; collect readable error instead of raising.
    """
    try:
        _transcode(src, out_tmp, height)
        return True
    except subprocess.CalledProcessError as e:
        msg = f"[{height}p] rc={e.returncode} err={(e.stderr or '').strip()[:4000]}"
        errors.append(msg)
        return False
    except Exception as e:
        errors.append(f"[{height}p] unexpected: {e!r}")
        return False


def _frame_to_image(src: Path, out_tmp: Path, w: int, h: int, ss: int) -> None:
    """
    Extract a single frame as JPEG at second `ss`, scaled+letterboxed to (w,h).
    """
    out_tmp.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale=w={w}:h={h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(ss), "-i", str(src),
        "-frames:v", "1",
        "-vf", vf,
        "-q:v", "3",
        str(out_tmp),
    ]
    _run(cmd)


def _cut_teaser(src: Path, out_tmp: Path, start: int, duration: int, w: int = 1280, h: int = 720) -> None:
    """
    Cut a short teaser MP4 (H.264/AAC) from `start` with given `duration`, scaled+letterboxed to (w,h).
    """
    out_tmp.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale=w={w}:h={h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(start), "-i", str(src),
        "-t", str(duration),
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-vf", vf,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(out_tmp),
    ]
    _run(cmd)


def _save_tmp_to_field(field, tmp_path: Path, final_rel_name: str) -> None:
    """
    Store a temp file into the FileField's storage under `final_rel_name`, then remove the temp file.
    Ensures no duplicate/suffixed filenames by deleting any pre-existing final file first.
    """
    storage = field.storage
    if storage.exists(final_rel_name):
        storage.delete(final_rel_name)
    with open(tmp_path, "rb") as fh:
        field.save(final_rel_name, File(fh), save=False)
    try:
        tmp_path.unlink()
    except Exception:
        pass


# -----------------------------
# Main task entry
# -----------------------------

def process_movie(movie_id: int) -> None:
    """
    Queue task:
      1 mark movie as 'processing'
      2 transcode MP4 variants (1080/720/480) to temp files, then save into FileFields
      3 set duration if available
      4 build assets: thumbnail (640x360), hero (1280x720), teaser (~8s)
      5 mark 'ready' if any variant succeeded, else 'failed'; persist error summary
    """
    movie = Movie.objects.get(pk=movie_id)

    if not movie.video_file:
        # Nothing to do without an input file
        return

    media_root = Path(settings.MEDIA_ROOT)
    tmp_dir = media_root / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    source = Path(movie.video_file.path)

    # Mark processing (and clear previous error)
    Movie.objects.filter(pk=movie.pk).update(processing_status="processing", processing_error="")

    # Probe duration early (best effort)
    probed_duration = _probe_duration(source)

    errors: List[str] = []

    # --- 2 Transcode variants to temp files ---
    tmp1080 = tmp_dir / f"movie_{movie.id}.1080.mp4"
    tmp720  = tmp_dir / f"movie_{movie.id}.720.mp4"
    tmp480  = tmp_dir / f"movie_{movie.id}.480.mp4"

    ok1080 = _safe_transcode(source, tmp1080, 1080, errors)
    ok720  = _safe_transcode(source, tmp720,   720, errors)
    ok480  = _safe_transcode(source, tmp480,   480, errors)

    rel1080 = f"movie_{movie.id}.1080.mp4"
    rel720  = f"movie_{movie.id}.720.mp4"
    rel480  = f"movie_{movie.id}.480.mp4"

    # Save available variants into FileFields (no duplicates; temp files removed)
    with transaction.atomic():
        if ok1080 and tmp1080.exists():
            _save_tmp_to_field(movie.video_1080, tmp1080, rel1080)
        if ok720 and tmp720.exists():
            _save_tmp_to_field(movie.video_720, tmp720, rel720)
        if ok480 and tmp480.exists():
            _save_tmp_to_field(movie.video_480, tmp480, rel480)
        # Update duration if we probed one and it isn't set yet
        if probed_duration and not movie.duration_seconds:
            movie.duration_seconds = probed_duration
        movie.save()

    any_ok = ok1080 or ok720 or ok480

    # Choose best available source for assets: prefer variants, else original
    def _first_existing(paths: list[Optional[Path]]) -> Path:
        for p in paths:
            if p and p.exists():
                return p
        return source

    best_src = _first_existing([
        Path(movie.video_1080.path) if getattr(movie, "video_1080", None) and movie.video_1080 else None,
        Path(movie.video_720.path)  if getattr(movie, "video_720",  None) and movie.video_720  else None,
        Path(movie.video_480.path)  if getattr(movie, "video_480",  None) and movie.video_480  else None,
    ])

    # --- 4 Build assets (errors should not turn a successful transcode into "failed") ---
    asset_errors: List[str] = []
    try:
        # Determine a few reasonable timestamps
        dur = probed_duration or _probe_duration(best_src) or 0
        ss_frame  = max(1, dur // 3)   # still frame around 1/3
        ss_teaser = max(1, dur // 5)   # teaser start around 1/5

        # Temp output paths
        tmp_thumb  = tmp_dir / f"movie_{movie.id}_thumb.jpg"
        tmp_hero   = tmp_dir / f"movie_{movie.id}_hero.jpg"
        tmp_teaser = tmp_dir / f"movie_{movie.id}_teaser.mp4"

        # Render
        _frame_to_image(best_src, tmp_thumb, 640, 360, ss_frame)
        _frame_to_image(best_src, tmp_hero,  1280, 720, ss_frame)
        _cut_teaser(best_src, tmp_teaser, ss_teaser, duration=8)

        # Save into fields (final relative names)
        with transaction.atomic():
            if dur and not movie.duration_seconds:
                movie.duration_seconds = dur
            _save_tmp_to_field(movie.thumbnail_image, tmp_thumb,  f"movie_{movie.id}_thumb.jpg")
            _save_tmp_to_field(movie.hero_image,      tmp_hero,   f"movie_{movie.id}_hero.jpg")
            _save_tmp_to_field(movie.teaser_video,    tmp_teaser, f"movie_{movie.id}_teaser.mp4")
            movie.save()

    except subprocess.CalledProcessError as e:
        asset_errors.append(f"[assets] rc={e.returncode} err={(e.stderr or '').strip()[:4000]}")
    except Exception as e:
        asset_errors.append(f"[assets] unexpected: {e!r}")

    # --- 5 Final status & errors ---
    with transaction.atomic():
        movie.processing_status = "ready" if any_ok else "failed"
        combined = errors + asset_errors
        movie.processing_error = "" if not combined else "\n".join(combined)[:8000]
        movie.save()