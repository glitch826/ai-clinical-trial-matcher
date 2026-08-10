import streamlit as st
import requests

st.set_page_config(page_title="AI Clinical Trial Matcher", layout="wide")

st.title("🩺 AI Clinical Trial Eligibility Matcher")
st.caption("Powered by ClinicalTrials.gov API & Google Gemini")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Patient Record Input")
    condition = st.text_input("Target Condition", value="Lung Cancer")
    patient_notes = st.text_area(
        "Unstructured Electronic Health Record (EHR) Notes",
        height=250,
        value="62-year-old male diagnosed with Stage III Non-Small Cell Lung Cancer. Normal renal function (Cr 0.9). No history of congestive heart failure. Prior chemotherapy completed 6 months ago."
    )
    submit_btn = st.button("Find Matching Trials", type="primary")

with col2:
    st.subheader("Trial Matching Results")
    if submit_btn:
        if not condition or not patient_notes:
            st.warning("Please fill out both fields before submitting.")
        else:
            with st.spinner("Fetching active clinical trials and evaluating eligibility..."):
                try:
                    res = requests.post(
                        "http://127.0.0.1:8000/trials/match",
                        json={"condition": condition, "patient_notes": patient_notes},
                        timeout=30
                    )
                    
                    if res.status_code == 200:
                        data = res.json()
                        results = data.get("results", [])
                        
                        if not results:
                            st.info("No active recruiting trials found for this condition.")
                        
                        for item in results:
                            eval_info = item["evaluation"]
                            status = eval_info.get("match_status", "MAYBE")
                            score = eval_info.get("match_score", 0)
                            
                            # Color coding badges
                            if status == "ELIGIBLE":
                                badge = "🟢 ELIGIBLE"
                            elif status == "INELIGIBLE":
                                badge = "🔴 INELIGIBLE"
                            else:
                                badge = "🟡 MAYBE"
                            
                            with st.expander(f"{badge} | {item['nct_id']} - {item['title']}"):
                                st.write(f"**Match Score:** {score}%")
                                st.write(f"**Reasoning:** {eval_info.get('reasoning', 'N/A')}")
                                
                                inc = eval_info.get("inclusion_matches", [])
                                if inc:
                                    st.write("**Met Inclusion Criteria:**")
                                    for match in inc:
                                        st.markdown(f"- ✅ {match}")
                                        
                                exc = eval_info.get("exclusion_violations", [])
                                if exc:
                                    st.write("**Exclusion Violations / Unmet Criteria:**")
                                    for violation in exc:
                                        st.markdown(f"- ❌ {violation}")
                    else:
                        st.error(f"Backend returned error code: {res.status_code}")
                except Exception as e:
                    st.error(f"Failed to connect to FastAPI backend: {e}")