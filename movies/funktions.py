from django.http import Http404


def parse_limit(request, default=3, min_value=1, max_value=10):
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
    val = request.query_params.get("random")
    if val is None:
        return default
    return str(val).lower() in ("1", "true", "yes", "on")


def pick_random(qs, limit):
    ids = list(qs.values_list("id", flat=True))
    if not ids:
        return []
    if limit >= len(ids):
        selected_ids = ids
    else:
        import random

        selected_ids = random.sample(ids, k=limit)
    objs = list(qs.model.objects.filter(id__in=selected_ids))
    objs.sort(key=selected_ids.index)
    return objs


def choose_quality(has_1080, has_720, has_480, screen_h=None, downlink_mbps=None):

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

    if downlink_mbps is not None:
        want = None
        if downlink_mbps >= 7 and "1080" in candidates:
            want = "1080"
        elif downlink_mbps >= 3 and "720" in candidates:
            want = "720"
        else:
            want = "480" if "480" in candidates else None

        if want and available.get(want):
            return want, "video.autoBySpeedAndResolution"

        for q in candidates:
            if available.get(q):
                return q, "video.autoBySpeedAndResolution"

        for q in ["720", "480", "1080"]:
            if available.get(q):
                return q, "video.autoBySpeedAndResolution"

        return "480", "video.autoBySpeedAndResolution"

    for q in candidates:
        if available.get(q):
            return q, "video.autoByResolution"

    # fallback
    for q in ["720", "480", "1080"]:
        if available.get(q):
            return q, "video.autoByResolution"

    return "480", "video.autoByResolution"



def getSource(movie, q):
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
    if not file_field or not getattr(file_field, "name", None):
        raise Http404("File not available")
    return file_field.storage.open(file_field.name, "rb")