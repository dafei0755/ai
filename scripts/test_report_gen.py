import requests
import time
import sys
import os
import json

BASE_URL = "http://127.0.0.1:8000/api/analysis"
REPORTS_DIR = "reports"

def run_test():
    print("1. Starting Analysis for Report Generation Test...")
    try:
        start_resp = requests.post(
            f"{BASE_URL}/start",
            json={
                "user_id": "test_report_gen",
                "user_input": "设计一个现代简约风格的客厅，要求有落地窗和阅读区。"
            }
        )
        start_resp.raise_for_status()
        session_id = start_resp.json()["session_id"]
        print(f"   Session Started: {session_id}")
    except Exception as e:
        print(f"   Failed to start analysis: {e}")
        return

    print("2. Polling Status...")
    start_time = time.time()
    while True:
        try:
            status_resp = requests.get(f"{BASE_URL}/status/{session_id}")
            status_data = status_resp.json()
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            
            sys.stdout.write(f"\r   Status: {status} | Progress: {progress*100:.1f}%")
            sys.stdout.flush()

            if status == "completed":
                print("\n   ✅ Workflow Completed Successfully!")
                break
            
            if status == "failed":
                print(f"\n   ❌ Workflow Failed: {status_data.get('error')}")
                break
            
            if status == "waiting_for_input":
                print(f"\n   Interaction required. Interrupt Data: {status_data.get('interrupt_data')}")
                # Auto-answer to proceed
                resume_val = "approve"
                if status_data.get('interrupt_data'):
                    # If it's a questionnaire, provide dummy answers
                    questions = status_data.get('interrupt_data', {}).get('questions', [])
                    if questions:
                        resume_val = {q['id']: "Test Answer" for q in questions}
                    else:
                         # Check if it is a simple question
                         resume_val = "Test Answer"
                
                print(f"   Sending resume_value: {resume_val}")
                requests.post(
                    f"{BASE_URL}/resume",
                    json={"session_id": session_id, "resume_value": resume_val}
                )

            if time.time() - start_time > 600: # 10 minute timeout
                print("\n   ❌ Timeout waiting for completion")
                break
                
            time.sleep(2)
        except Exception as e:
            print(f"\n   Error polling status: {e}")
            break

    print("3. Verifying Report Generation...")
    
    # Check API
    try:
        report_resp = requests.get(f"{BASE_URL}/report/{session_id}")
        if report_resp.status_code == 200:
            print("   ✅ API returned report successfully.")
            content = report_resp.json().get("report_text", "")
            if content:
                print(f"   Report content length: {len(content)} chars")
            else:
                print("   ⚠️ Report content is empty!")
        else:
            print(f"   ❌ Failed to retrieve report from API: {report_resp.status_code}")
    except Exception as e:
        print(f"   Error retrieving report from API: {e}")

    # Check File System
    print("4. Checking File System...")
    found = False
    for filename in os.listdir(REPORTS_DIR):
        if session_id in filename and filename.endswith(".txt"):
            print(f"   ✅ Found report file: {filename}")
            found = True
            break
    
    if not found:
        print(f"   ❌ Report file not found in {REPORTS_DIR} for session {session_id}")

if __name__ == "__main__":
    run_test()
