def validate_stream(events):
    seen = set()
    for _, event_id, _ in events:
        if event_id in seen:
            raise ValueError(f"duplicate id: {event_id}")
        seen.add(event_id)
    keys = [(timestamp, event_id) for timestamp, event_id, _ in events]
    for previous, current in zip(keys, keys[1:]):
        if not previous < current:
            raise ValueError(f"unsorted at {current}")
    return None


def diff_events(old, new):
    validate_stream(old)
    validate_stream(new)
    old_by_id = {event_id: (timestamp, payload) for timestamp, event_id, payload in old}
    new_ids = {event_id for _, event_id, _ in new}
    result = {"added": [], "removed": [], "moved": [], "changed": []}
    for timestamp, event_id, payload in new:
        if event_id not in old_by_id:
            result["added"].append(event_id)
            continue
        old_timestamp, old_payload = old_by_id[event_id]
        if old_timestamp != timestamp:
            result["moved"].append(event_id)
        if old_payload != payload:
            result["changed"].append(event_id)
    result["removed"] = [event_id for _, event_id, _ in old if event_id not in new_ids]
    return result


def merge_streams(a, b):
    validate_stream(a)
    validate_stream(b)
    b_ids = {event_id for _, event_id, _ in b}
    merged = [event for event in a if event[1] not in b_ids] + list(b)
    return sorted(merged, key=lambda event: (event[0], event[1]))
