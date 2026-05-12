from __future__ import annotations

from app.triggers.trigger_engine import TriggerEngine


def test_trigger_engine_calls_llm_for_completed_modes():
    engine = TriggerEngine()

    assert engine.should_call_llm("exercise", "session_completed")


def test_trigger_engine_does_not_call_llm_for_frame_update_or_unknown_events():
    engine = TriggerEngine()

    assert not engine.should_call_llm("exercise", "frame_update")
    assert not engine.should_call_llm("grooming", "analysis_completed")
    assert not engine.should_call_llm("outfit", "analysis_completed")
    assert not engine.should_call_llm("outing", "analysis_completed")
