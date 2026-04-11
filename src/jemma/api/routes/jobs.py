from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["jobs"])


@router.get("/jobs")
def list_jobs(request: Request) -> dict[str, object]:
    return {"jobs": request.app.state.jobs.list_jobs()}


@router.get("/jobs/{job_id}")
def get_job(request: Request, job_id: str) -> dict[str, object]:
    record = request.app.state.jobs.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": record}


@router.get("/jobs/{job_id}/events")
async def stream_job_events(request: Request, job_id: str, after: int = 0) -> StreamingResponse:
    jobs = request.app.state.jobs
    if jobs.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_stream() -> object:
        cursor = after
        while True:
            events = jobs.get_events(job_id, after=cursor)
            for event in events:
                cursor = max(cursor, int(event["sequence"]))
                yield f"data: {json.dumps(event)}\n\n"
            record = jobs.get_job(job_id)
            if record and record["status"] in {"succeeded", "failed", "cancelled"} and not events:
                break
            if await request.is_disconnected():
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

