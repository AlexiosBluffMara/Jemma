from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["runs"])


@router.get("/runs")
def list_runs(request: Request, limit: int = 50) -> dict[str, object]:
    store = request.app.state.store
    return {"runs": store.list_runs(limit=limit)}


@router.get("/runs/{run_id}")
def get_run(request: Request, run_id: str) -> dict[str, object]:
    store = request.app.state.store
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run": run, "summary": store.read_run_summary(run_id)}


@router.get("/runs/{run_id}/summary")
def get_run_summary(request: Request, run_id: str) -> dict[str, object]:
    store = request.app.state.store
    summary = store.read_run_summary(run_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Run summary not found")
    return {"run_id": run_id, "summary": summary}


@router.get("/runs/{run_id}/results")
def get_run_results(request: Request, run_id: str) -> dict[str, object]:
    store = request.app.state.store
    results = store.read_run_results(run_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Run results not found")
    return {"run_id": run_id, "results": results}


@router.get("/runs/{run_id}/events")
def get_run_events(request: Request, run_id: str, limit: int = 500) -> dict[str, object]:
    store = request.app.state.store
    return {"run_id": run_id, "events": store.list_events(run_id, limit=limit)}

