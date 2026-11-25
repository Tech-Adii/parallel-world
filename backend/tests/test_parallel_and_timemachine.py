"""Unit tests for Parallel Universes (A vs B), Time Machine stack rewind, and AI City Administrator."""

from app.db.storage import SimulationDatabase
from app.engine.ai_advisor import AICityAdministrator
from app.engine.simulation import ParallelWorldManager


def test_parallel_universes_diverge_under_intervention(tmp_path):
    db = SimulationDatabase(tmp_path / "test.db")
    mgr = ParallelWorldManager(db=db)

    for _ in range(12):
        mgr.step_all()

    comp = mgr.parallel_comparison()
    assert comp.universe_b.interventions.emergency_response_active is True
    assert comp.universe_a.interventions.emergency_response_active is False
    # Universe B (optimized emergency response) should achieve higher stability & fewer affected citizens than Universe A
    assert comp.universe_b.metrics.city_stability > comp.universe_a.metrics.city_stability
    assert comp.universe_b.metrics.citizens_affected < comp.universe_a.metrics.citizens_affected


def test_time_machine_rewind_and_branch(tmp_path):
    db = SimulationDatabase(tmp_path / "test.db")
    mgr = ParallelWorldManager(db=db)
    start_tick = mgr.primary.tick

    for _ in range(5):
        mgr.primary.step()

    assert mgr.primary.tick == start_tick + 5
    depth_before = mgr.primary.time_machine.depth()

    ok = mgr.primary.rewind(target_tick=start_tick + 1)
    assert ok is True
    assert mgr.primary.tick == start_tick + 1
    assert mgr.primary.time_machine.depth() < depth_before

    # Apply new decision and branch forward
    mgr.primary.apply_action("deploy_emergency_response")
    mgr.primary.step()
    assert mgr.primary.tick == start_tick + 2
    assert mgr.primary.interventions.emergency_response_active is True


def test_ai_administrator_recommendations(tmp_path):
    db = SimulationDatabase(tmp_path / "test.db")
    mgr = ParallelWorldManager(db=db)
    advisor = AICityAdministrator(ollama_url="http://127.0.0.1:59999")

    snap = mgr.universe_a.snapshot()
    advice = advisor.analyze(snap, question="How is the power grid and evacuation?")
    assert advice.source == "deterministic-engine"
    assert len(advice.recommendations) >= 1
    assert advice.answer is not None
