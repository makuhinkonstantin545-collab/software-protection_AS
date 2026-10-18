import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"healthy": True}

@app.get("/cpu")
def cpu():
    load1, load5, load15 = os.getloadavg()
    return {"load_1m": load1, "load_5m": load5, "load_15m": load15}

@app.get("/metrics")
def metrics():
    return {"cpu_count": os.cpu_count()}
