def fetch_with_retry(fetch, sleep, max_attempts=3, max_delay=30):
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    delay = 1
    for attempt in range(max_attempts):
        try:
            return fetch()
        except ConnectionError:
            if attempt == max_attempts - 1:
                raise
            sleep(min(delay, max_delay))
            delay *= 2
