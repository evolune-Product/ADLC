"""
Celery task for running a persona simulation.

One task, unlike the two-task approval-gate pattern `run_tasks.py` uses for
SDLC runs — a simulation has no human-approval pause to stop and resume
around. It either finishes (with a status of completed/failed) inside one
task, or it doesn't; there is nothing here that ships a change, so there is
nothing here that needs a gate.
"""
from __future__ import annotations

import logging

from celery_app import celery_app
from app.database import SessionLocal

log = logging.getLogger(__name__)


@celery_app.task(name="simulation_tasks.run_simulation")
def task_run_simulation(simulation_run_id: str) -> None:
    from app.agents.simulation_agent import run_simulation

    db = SessionLocal()
    try:
        run_simulation(db, simulation_run_id)
    except Exception:
        log.exception("Simulation task failed outright for run %s", simulation_run_id)
        # run_simulation already commits a terminal status on every path it
        # controls; this only covers something raising before that, e.g. the
        # SimulationRun row itself having vanished.
        try:
            from datetime import datetime, timezone

            from app.models.simulation import SimulationRun

            run = db.query(SimulationRun).filter(SimulationRun.id == simulation_run_id).first()
            if run and run.status not in ("completed", "failed"):
                run.status = "failed"
                run.error_message = "Simulation task failed unexpectedly — see server logs."
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            log.exception("Could not even mark simulation run %s failed", simulation_run_id)
    finally:
        db.close()
