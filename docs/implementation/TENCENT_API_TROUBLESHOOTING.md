# Tencent Cloud Content Safety API Troubleshooting Report

## Current Status

**Date**: 2025-12-06
**Error Code**: `AuthFailure.SecretIdNotFound`
**RequestId**: `1c042399-53af-4efa-9c7f-26fb9e80fb54`

### Diagnostic Results

All configuration steps completed successfully:
- ✅ Tencent Cloud SDK installed (`tencentcloud-sdk-python>=3.0.1100`)
- ✅ Sub-account `sf2025` created
- ✅ API key generated for sf2025
  - SecretId: `AKIDYFx2Ar7RpzwJd4KhspeIwT0d2tJztm`
  - SecretKey: `mKTm1zNhrpa81pANRM7jAPTNaeV9g03v`
- ✅ QcloudTMSFullAccess permission assigned to sf2025
- ✅ Application created (ID: `1997127090860864256`)
- ✅ BizType configured (text: `txt`, image: `pic`)
- ✅ SDK client initialization successful
- ❌ API call failed with `AuthFailure.SecretIdNotFound`

### Error Analysis

**Error Message**: "SecretId不存在，请检查正确的密钥"

This specific error (`AuthFailure.SecretIdNotFound`) indicates that:
1. The API request reached Tencent Cloud servers (proven by RequestId)
2. The Tencent Cloud authentication system does NOT recognize this SecretId
3. This is not a permission issue - the SecretId itself is not found in their system

### Root Cause Investigation

Based on the error code, the most likely causes are:

#### Hypothesis 1: Content Safety Service Requires Main Account Activation (Most Likely)
Some Tencent Cloud services require the main account to explicitly activate the service before sub-accounts can use it, even with proper permissions.

**Evidence**:
- User can create applications (suggests service partially activated)
- But API calls with sub-account fail with "SecretId not found"
- This pattern is common when service activation is incomplete

**Next Steps**:
1. Check service activation status at: https://console.cloud.tencent.com/cms/text/overview
2. Look for any "Activate Service" or "Enable API" buttons
3. If service requires main account activation, complete that step

#### Hypothesis 2: Sub-Account API Key Not Recognized by Content Safety Service (Possible)
Some Tencent Cloud services have restrictions on sub-account API key usage, especially for content moderation services (due to compliance/security requirements).

**Evidence**:
- Sub-account key format is correct (starts with AKID, 34 characters)
- Credential object creates successfully locally
- But Tencent Cloud API rejects it completely

**Next Steps**:
1. Test with main account API key to isolate the issue
2. If main account works, this confirms sub-account restriction

#### Hypothesis 3: API Key State or Timing Issue (Less Likely)
The API key might be:
- In "Disabled" state
- Not fully propagated (though unlikely after current time elapsed)
- Created for a different Tencent Cloud account

**Next Steps**:
1. Visit: https://console.cloud.tencent.com/cam/capi
2. Click on user "sf2025"
3. Go to "API密钥" tab
4. Verify key status shows "已启用" (Enabled)
5. Verify the SecretId matches exactly: `AKIDYFx2Ar7RpzwJd4KhspeIwT0d2tJztm`

## Recommended Action Plan

### Option 1: Verify Service Activation (Priority 1 - Recommended)

**Step 1**: Check Content Safety service activation
```
Visit: https://console.cloud.tencent.com/cms/text/overview
Look for:
- Service status indicator
- Any "Activate" or "Enable" buttons
- Usage statistics (if showing data, service is fully active)
```

**Expected Outcomes**:
- If service shows "未开通" (Not activated) → Click activate button with main account
- If service shows usage stats and no activation prompts → Service is active, move to Option 2

### Option 2: Test with Main Account Key (Priority 2 - Diagnostic)

**Purpose**: Isolate whether issue is sub-account-specific or system-wide

**Step 1**: Temporarily switch to main account API key
```bash
# In .env file, replace:
TENCENT_CLOUD_SECRET_ID=AKIDYFx2Ar7RpzwJd4KhspeIwT0d2tJztm  # Sub-account sf2025
TENCENT_CLOUD_SECRET_KEY=mKTm1zNhrpa81pANRM7jAPTNaeV9g03v

# With main account key (use Key 1 from plan):
TENCENT_CLOUD_SECRET_ID=AKI04022vgDc8kftqpi...  # Main account (get full key)
TENCENT_CLOUD_SECRET_KEY=...  # Main account secret key
```

**Step 2**: Re-run diagnostic
```bash
python scripts/diagnose_tencent_api.py
```

**Expected Outcomes**:
- If **main account works** → Confirms sub-account has restrictions for this service
  - Solution: Use main account key for Content Safety API (acceptable for internal tools)
  - Or contact Tencent Cloud support to enable sub-account usage
- If **main account also fails** → Different issue (service not activated, wrong account, etc.)

### Option 3: Contact Tencent Cloud Support (Priority 3 - Last Resort)

If Options 1 and 2 don't resolve the issue, contact Tencent Cloud technical support:

**Information to Provide**:
- Error Code: `AuthFailure.SecretIdNotFound`
- RequestId: `1c042399-53af-4efa-9c7f-26fb9e80fb54`
- Service: Content Safety (TMS - Text Moderation Service)
- Application ID: `1997127090860864256`
- Sub-account: `sf2025`
- Issue: Sub-account API key not recognized by Content Safety API

**Questions to Ask**:
1. Does Content Safety service support sub-account API keys?
2. Is there special activation required for sub-accounts to use this service?
3. Why is the SecretId not found when QcloudTMSFullAccess permission is assigned?

## Security Note

If you decide to use the main account API key (Option 2 outcome):
- ✅ Acceptable for internal development tools
- ✅ Shared key usage is normal (COS + Content Safety can share same key)
- ⚠️ Keep .env file in .gitignore
- ⚠️ Rotate keys every 90 days
- ⚠️ Consider moving to sub-account after confirming service setup

## Implementation Status Summary

**Phase 3 (P0 Task - Tencent Cloud API Integration)**:
- Code Implementation: **100% Complete** (8/8 files)
  - ✅ SDK dependency added
  - ✅ Configuration templates created
  - ✅ API client implemented
  - ✅ ContentSafetyGuard integrated
  - ✅ Verification scripts created
  - ✅ Unit tests written
  - ✅ Integration tests written
  - ✅ Deployment documentation complete

- Configuration: **100% Complete**
  - ✅ Sub-account created with best practices
  - ✅ Permissions assigned
  - ✅ API keys generated
  - ✅ Environment variables configured

- Testing: **Blocked by Authentication**
  - ❌ API verification failing with `AuthFailure.SecretIdNotFound`
  - ⏸️ Unit tests pending (can't run without API access)
  - ⏸️ Integration tests pending

**Estimated Time to Resolution**: 30 minutes - 2 hours
- If service activation: 30 minutes
- If switching to main account: 5 minutes
- If needing Tencent Cloud support: 1-2 hours (or more)

## Next Immediate Action

**Please execute Option 1 first**:
1. Visit https://console.cloud.tencent.com/cms/text/overview with main account
2. Check if there's any "Activate" or "Enable API" button
3. Report back the status you see on that page

This will immediately tell us if the issue is service activation vs. sub-account restrictions.
