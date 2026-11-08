import pytest

from rosetta_bench.timing import StageTimer


def _clock(*ticks):
    values = iter(ticks)
    return lambda: next(values)


def test_stage_timer_records_each_stage_in_ms():
    timer = StageTimer(clock=_clock(0.0, 0.25, 1.0, 1.5))
    with timer.stage("generation"):
        pass
    with timer.stage("scoring"):
        pass
    assert timer.timings_ms == {"generation": 250.0, "scoring": 500.0}


def test_stage_timer_records_time_even_when_the_stage_raises():
    timer = StageTimer(clock=_clock(0.0, 2.0))
    with pytest.raises(RuntimeError):
        with timer.stage("generation"):
            raise RuntimeError("provider down")
    assert timer.timings_ms == {"generation": 2000.0}


def test_repeated_stage_accumulates():
    timer = StageTimer(clock=_clock(0.0, 0.1, 1.0, 1.3))
    for _ in range(2):
        with timer.stage("decision"):
            pass
    assert timer.timings_ms["decision"] == pytest.approx(400.0)
