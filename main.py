from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

import psv_calc

BASE = Path(__file__).parent
app = FastAPI(title="PSV Sizing Manager")


class SizingRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    fluid: str
    unit_set: str = "bar"


@app.post("/api/size")
def api_size(req: SizingRequest):
    try:
        return psv_calc.size(req.model_dump())
    except (ValueError, KeyError, ZeroDivisionError) as e:
        raise HTTPException(status_code=422, detail=f"Check your inputs: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
