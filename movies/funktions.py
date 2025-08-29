from django.http import Http404
import random  # needed for the tests


def parse_limit(request, default=3, min_value=1, max_value=10):
    """
    Read ?limit from request.query_params and return a safe integer.
    Clamps the value between min_value and max_value and falls back to
    the provided default on missing/invalid input.
    """
    raw = request.query_params.get("limit")
    try:
        value = int(raw) if raw is not None else default
    except Exception:
        value = default
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def get_random_flag(request, default=False):
    """
    Return a boolean for the query param `random`.
    Accepts common truthy strings (1/true/yes/on) case-insensitively;
    if the param is missing, returns the given default.
    """
    val = request.query_params.get("random")
    if val is None:
        return default
    return str(val).lower() in ("1", "true", "yes", "on")


def pick_random(qs, limit):
    """
    Return up to `limit` objects from a queryset in a stable order.
    When `limit` is less than the number of rows, sample deterministically via
    the module-level `random.sample` (so tests can patch movies.funktions.random).
    The returned objects keep the sampled order.
    """
    ids = list(qs.values_list("id", flat=True))
    if not ids:
        return []
    if limit >= len(ids):
        selected_ids = ids
    else:
        # Use the module-level `random` so tests can patch
        selected_ids = random.sample(ids, k=limit)
    objs = list(qs.model.objects.filter(id__in=selected_ids))
    # Preserve the selected order
    objs.sort(key=selected_ids.index)
    return objs


def choose_quality(has_1080, has_720, has_480, screen_h=None, downlink_mbps=None):
    """
    Decide the streaming quality ("1080"/"720"/"480") based on available files,
    optional screen height, and optional network speed (downlink_mbps).
    Returns a tuple (quality_str, i18n_key). Always emits key `player.quality.{q}`.
    """
    # Determine the maximum sensible level based on screen height
    if screen_h is None:
        max_level = "720"
    else:
        if screen_h >= 1080:
            max_level = "1080"
        elif screen_h >= 720:
            max_level = "720"
        else:
            max_level = "480"

    available = {
        "1080": bool(has_1080),
        "720": bool(has_720),
        "480": bool(has_480),
    }

    if max_level == "1080":
        candidates = ["1080", "720", "480"]
    elif max_level == "720":
        candidates = ["720", "480"]
    else:
        candidates = ["480"]

    # Pick a quality (q) using the exact same selection logic as before,
    # but always return a unified i18n key: player.quality.{q}
    q = None

    if downlink_mbps is not None:
        # speed-aware choice
        want = None
        if downlink_mbps >= 7 and "1080" in candidates:
            want = "1080"
        elif downlink_mbps >= 3 and "720" in candidates:
            want = "720"
        else:
            want = "480" if "480" in candidates else None

        if want and available.get(want):
            q = want
        else:
            # first available in candidates
            for opt in candidates:
                if available.get(opt):
                    q = opt
                    break
            # broad fallback order
            if q is None:
                for opt in ["720", "480", "1080"]:
                    if available.get(opt):
                        q = opt
                        break
    else:
        # resolution-only choice
        for opt in candidates:
            if available.get(opt):
                q = opt
                break
        if q is None:
            for opt in ["720", "480", "1080"]:
                if available.get(opt):
                    q = opt
                    break

    if q is None:
        q = "480"

    msg_key = f"player.quality.{q}"
    return q, msg_key



def getSource(movie, q):
    """
    Pick the Movie FileField for the requested quality string.
    If `q` is empty/unknown, fall back to 720→480→1080.
    """
    if q == "1080":
        src = movie.video_1080
    elif q == "720":
        src = movie.video_720
    elif q == "480":
        src = movie.video_480
    else:
        src = movie.video_720 or movie.video_480 or movie.video_1080
    return src


def check_or_404(file_field):
    """
    Open a FileField from storage or raise Http404 if the field is empty/missing.
    Returns a readable file handle.
    """
    if not file_field or not getattr(file_field, "name", None):
        raise Http404("File not available")
    return file_field.storage.open(file_field.name, "rb")