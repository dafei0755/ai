# -*- coding: utf-8 -*-
"""
v7.128 Core Routing Verification

Directly check key strings in source code
"""

import os
import sys

# Force UTF-8 output
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

print("=" * 80)
print("v7.128 Questionnaire Step Swap Verification")
print("=" * 80)
print()

# Read progressive_questionnaire.py
file_path = os.path.join("..", "intelligent_project_analyzer", "interaction", "nodes", "progressive_questionnaire.py")

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

print("[Backend] progressive_questionnaire.py Check:")
print()

passed = 0
failed = 0

# Test 1: Step 1 routing
if 'return Command(update=update_dict, goto="progressive_step3_gap_filling")' in content:
    if content.find("def step1_core_task") < content.find('goto="progressive_step3_gap_filling"'):
        print("[PASS] Step 1 routes to progressive_step3_gap_filling")
        passed += 1
    else:
        print("[WARN] Found progressive_step3_gap_filling but not in step1")
        failed += 1
else:
    print("[FAIL] Step 1 routing not found")
    failed += 1

# Test 2: Step 2 routing and numbering
if 'return Command(update=update_dict, goto="project_director")' in content:
    step2_start = content.find("def step2_radar")
    step3_start = content.find("def step3_gap_filling")
    project_director_pos = content.find('goto="project_director"')

    if step2_start < project_director_pos < step3_start:
        print("[PASS] Step 2 routes to project_director")
        passed += 1
    else:
        print("[WARN] Found project_director but position incorrect")
        failed += 1
else:
    print("[FAIL] Step 2 routing not found")
    failed += 1

if '"step": 3,' in content and '"interaction_type": "progressive_questionnaire_step2"' in content:
    print("[PASS] Step 2 payload has step=3")
    passed += 1
else:
    print("[FAIL] Step 2 payload step number incorrect")
    failed += 1

# Test 3: Step 3 routing and numbering
if 'return Command(update=update_dict, goto="progressive_step2_radar")' in content:
    step3_start = content.find("def step3_gap_filling")
    step2_radar_pos = content.find('goto="progressive_step2_radar"')

    if step3_start < step2_radar_pos:
        print("[PASS] Step 3 routes to progressive_step2_radar")
        passed += 1
    else:
        print("[WARN] Found progressive_step2_radar but position incorrect")
        failed += 1
else:
    print("[FAIL] Step 3 routing not found")
    failed += 1

if '"step": 2,' in content and '"interaction_type": "progressive_questionnaire_step3"' in content:
    print("[PASS] Step 3 payload has step=2")
    passed += 1
else:
    print("[FAIL] Step 3 payload step number incorrect")
    failed += 1

# Test 4: Intelligent defaults
if "gap_filling_answers = state.get" in content and "default_values" in content:
    print("[PASS] Step 2 has intelligent defaults logic")
    passed += 1
else:
    print("[FAIL] Step 2 missing intelligent defaults logic")
    failed += 1

print()
print("[Frontend] UnifiedProgressiveQuestionnaireModal.tsx Check:")
print()

# Read frontend file
frontend_path = os.path.join("..", "frontend-nextjs", "components", "UnifiedProgressiveQuestionnaireModal.tsx")

try:
    with open(frontend_path, "r", encoding="utf-8") as f:
        frontend_content = f.read()

    # Check step labels
    if "{ number: 2, label: '信息补全'" in frontend_content:
        print("[PASS] Step 2 label is 'Info Completion'")
        passed += 1
    else:
        print("[FAIL] Step 2 label incorrect")
        failed += 1

    if "{ number: 3, label: '偏好雷达图'" in frontend_content:
        print("[PASS] Step 3 label is 'Radar Chart'")
        passed += 1
    else:
        print("[FAIL] Step 3 label incorrect")
        failed += 1

    # Check rendering logic
    if "case 2: return renderStep3Content();" in frontend_content:
        print("[PASS] case 2 renders Step3Content")
        passed += 1
    else:
        print("[FAIL] case 2 rendering logic incorrect")
        failed += 1

    if "case 3: return renderStep2Content();" in frontend_content:
        print("[PASS] case 3 renders Step2Content")
        passed += 1
    else:
        print("[FAIL] case 3 rendering logic incorrect")
        failed += 1

    # Check validation logic
    if "currentStep === 2 && !validateStep3Required()" in frontend_content:
        print("[PASS] Step 2 validation logic correct")
        passed += 1
    else:
        print("[FAIL] Step 2 validation logic incorrect")
        failed += 1

except Exception as e:
    print(f"[FAIL] Cannot read frontend file: {e}")
    failed += 5

print()
print("=" * 80)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 80)

if failed == 0:
    print("\nSUCCESS! All v7.128 changes verified!")
    sys.exit(0)
else:
    print(f"\nFAILURE! {failed} checks failed")
    sys.exit(1)
