import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TigerGraph Agentic Fraud Investigation Console", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CASES_DIR = r"c:\Users\Mukul\Desktop\Tark\cases"

@app.get("/api/cases")
def list_cases():
    if not os.path.exists(CASES_DIR):
        return []
    cases = []
    for f in sorted(os.listdir(CASES_DIR)):
        if f.endswith(".json"):
            path = os.path.join(CASES_DIR, f)
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                cases.append({
                    "case_id": data["case_id"],
                    "verdict": data["case"]["verdict"],
                    "pattern": data["case"]["pattern"],
                    "exposure_usd": data["case"]["exposure_usd"],
                    "fraud_probability": data["case"]["fraud_probability"],
                    "sar_filed": data["sar"]["file"],
                    "actions": [a["action"] for a in data["next_best_actions"]["final"]]
                })
    return cases

@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    path = os.path.join(CASES_DIR, f"{case_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Case not found")
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    with open(r"c:\Users\Mukul\Desktop\Tark\web\index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
