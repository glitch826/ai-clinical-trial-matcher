import json
import re
import os
import requests
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# Initialize Gemini Client (usesenv:GEMINI_API_KEY or explicit key)
client = genai.Client(api_key="AQ.Ab8RN6KWRAaZ56V0cGNkKyfuxlhCGFmHEiE2HVOUNSy2S2jlPg")

CLINICAL_TRIALS_API = "https://clinicaltrials.gov/api/v2/studies"

# --- Pydantic Schema for Structured Gemini Output ---
class EvaluationResult(BaseModel):
    match_status: str = Field(description="Must be 'ELIGIBLE', 'INELIGIBLE', or 'MAYBE'")
    match_score: int = Field(description="Confidence score from 0 to 100")
    inclusion_matches: List[str] = Field(description="List of met inclusion criteria with short explanations")
    exclusion_violations: List[str] = Field(description="List of violated exclusion criteria or unmet prerequisites")
    reasoning: str = Field(description="Concise summary explaining why the patient matches or fails")

def fetch_clinical_trials(condition: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """Fetch active clinical trials for a condition from ClinicalTrials.gov API v2."""
    params = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING",
        "pageSize": max_results,
        "fields": "NCTId,BriefTitle,EligibilityModule"
    }
    
    try:
        response = requests.get(CLINICAL_TRIALS_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        trials = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            nct_id = protocol.get("identificationModule", {}).get("nctId", "N/A")
            title = protocol.get("identificationModule", {}).get("briefTitle", "No Title")
            eligibility = protocol.get("eligibilityModule", {}).get("eligibilityCriteria", "No criteria specified.")
            
            trials.append({
                "nct_id": nct_id,
                "title": title,
                "eligibility_criteria": eligibility
            })
        return trials
    except Exception as e:
        print(f"Error fetching trials: {e}")
        return []

def evaluate_patient_against_trial(patient_notes: str, trial: Dict[str, Any]) -> Dict[str, Any]:
    """Uses Gemini 2.5 Flash to evaluate patient eligibility against trial criteria."""
    prompt = f"""
    You are an expert clinical trial matching assistant.
    Analyze the following patient's medical notes against the clinical trial eligibility criteria.

    === PATIENT MEDICAL NOTES ===
    {patient_notes}

    === TRIAL CRITERIA (NCT ID: {trial['nct_id']}) ===
    {trial['eligibility_criteria']}

    Evaluate carefully:
    1. Check all age, diagnosis, stage, and organ function requirements.
    2. Identify any explicit exclusion criteria the patient triggers.
    3. Determine match_status ('ELIGIBLE', 'INELIGIBLE', or 'MAYBE').
    4. Provide a match_score between 0 and 100.
    """

    try:
        # Request strict JSON output conforming to the EvaluationResult schema
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EvaluationResult,
                temperature=0.1,
            )
        )
        
        # Parse JSON output
        raw_text = response.text.strip()
        # Clean potential markdown backticks just in case
        cleaned_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
        
        return json.loads(cleaned_text)

    except Exception as e:
        print(f"Evaluation error for {trial['nct_id']}: {e}")
        return {
            "match_status": "MAYBE",
            "match_score": 0,
            "inclusion_matches": [],
            "exclusion_violations": ["Evaluation error occurred."],
            "reasoning": f"Unable to process evaluation automatically: {str(e)}"
        }

def process_trial_matching(condition: str, patient_notes: str) -> Dict[str, Any]:
    """Pipeline: Fetch trials and evaluate each against patient notes."""
    trials = fetch_clinical_trials(condition, max_results=3)
    results = []
    
    for trial in trials:
        eval_data = evaluate_patient_against_trial(patient_notes, trial)
        results.append({
            "nct_id": trial["nct_id"],
            "title": trial["title"],
            "evaluation": eval_data
        })
        
    return {
        "condition": condition,
        "total_evaluated": len(results),
        "results": results
    }