from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from matcher import process_trial_matching

app = FastAPI(
    title="Clinical Trial Eligibility Matcher",
    description="Backend API combining ClinicalTrials.gov and Gemini for automated trial eligibility assessment.",
    version="1.0.0"
)

class MatchRequest(BaseModel):
    condition: str
    patient_notes: str

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "Clinical Trial Matcher API active. Access /docs for interactive testing."
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/trials/match")
def match_trials(request: MatchRequest):
    if not request.condition.strip() or not request.patient_notes.strip():
        raise HTTPException(status_code=400, detail="Condition and patient notes cannot be empty.")
    
    try:
        results = process_trial_matching(request.condition, request.patient_notes)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))