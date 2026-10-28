from pathlib import Path

import pandas as pd
from fastapi import FastAPI

# built from __file__ so the same path works under vercel dev, docker and production
DATA_DIR = Path(__file__).parent / "data"

# docs live under /api because only that prefix is routed to this service
app = FastAPI(
    title="Windsight API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
def health():
    sample = pd.read_csv(DATA_DIR / "sample.csv")
    return {
        "ok": True,
        "pandas": pd.__version__,
        "rows": int(len(sample)),
        "first_generation_mw": float(sample["generation"].iloc[0]),
    }
