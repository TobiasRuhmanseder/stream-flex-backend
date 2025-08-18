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
    val = request.query_params.get('random')
    if val is None:
        return default
    return str(val).lower() in ('1', 'true', 'yes', 'on')


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
