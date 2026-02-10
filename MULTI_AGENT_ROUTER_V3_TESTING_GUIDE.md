# Multi-Agent Router V3 - Testing Guide

## Pre-Testing Setup

1. **Backup Current Configuration** (if upgrading):
   ```bash
   cp /config/custom_components/multi_agent_router/config_flow.py /config/custom_components/multi_agent_router/config_flow.py.backup
   cp /config/custom_components/multi_agent_router/strings.json /config/custom_components/multi_agent_router/strings.json.backup
   ```

2. **Restart Home Assistant**:
   - Go to Settings → System → Restart
   - Wait for Home Assistant to fully restart

## Test Scenario 1: Fresh Installation

### Step 1: Initial Configuration
1. Navigate to Settings → Devices & Services → Add Integration
2. Search for "Multi-Agent Router"
3. Click to start configuration

**Expected Result:**
- Should see summary page with status showing:
  ```
  ✗ Prompt AI not configured
  ✗ Router AI not configured
  ✗ No Custom AIs configured
  ```
- Menu should show only 3 options (no Submit button yet):
  - Edit Prompt AI
  - Edit Router AI
  - Manage Custom AIs

### Step 2: Configure Prompt AI
1. Click "Edit Prompt AI"
2. Select a conversation agent (e.g., `conversation.jarvis_prompt_generator`)
3. Verify the prompt field auto-fills (or use default)
4. Click Submit

**Expected Result:**
- Returns to summary page
- Status now shows: `✓ Prompt AI configured`

### Step 3: Configure Router AI
1. Click "Edit Router AI"
2. Select a conversation agent (e.g., `conversation.jarvis_router`)
3. Click Submit (note: NO prompt field here)

**Expected Result:**
- Returns to summary page
- Status now shows: `✓ Router AI configured`

### Step 4: Try to Submit (Should Fail)
1. Look for Submit button

**Expected Result:**
- Submit button should NOT be visible (no custom AIs yet)

### Step 5: Add First Custom AI
1. Click "Manage Custom AIs"
2. Should see "No Custom AIs configured yet."
3. Click "Add Custom AI"
4. Fill in:
   - Name: "Jarvis Think"
   - Agent: `conversation.jarvis_think`
   - Description: "Handles questions and analysis"
   - Keywords: "question, what, why, how, analyze"
   - Prompt: (optional, should auto-fill)
5. Click Submit

**Expected Result:**
- Returns to Manage Custom AIs menu
- Shows "- Jarvis Think (conversation.jarvis_think)"
- Menu now shows Edit and Delete options

### Step 6: Add Second Custom AI
1. Click "Add Custom AI" again
2. Fill in:
   - Name: "Home Control"
   - Agent: `conversation.jarvis_do`
   - Description: "Executes home automation commands"
   - Keywords: "turn, set, control, adjust"
3. Click Submit

**Expected Result:**
- Returns to Manage Custom AIs menu
- Shows both agents in list

### Step 7: Return to Summary
1. Click "Back to Configuration"

**Expected Result:**
- Status shows:
  ```
  ✓ Prompt AI configured
  ✓ Router AI configured
  ✓ Custom AIs (2): Jarvis Think, Home Control
  ```
- Submit button NOW visible

### Step 8: Submit Configuration
1. Click "Submit & Review"
2. Wait for AI to generate prompt (may take a few seconds)

**Expected Result:**
- Should see "Review Router Prompt" page
- Prompt field should contain AI-generated text with:
  - Instructions for router behavior
  - List of available agents (Jarvis Think, Home Control)
  - Example routing decisions
  - "ROUTE: [AgentName]" format instructions

### Step 9: Review and Finalize
1. Review the generated prompt
2. Optionally edit if needed
3. Click Submit

**Expected Result:**
- Integration created successfully
- Shows success message
- Integration appears in Devices & Services

## Test Scenario 2: Editing Existing Configuration

### Step 1: Open Options
1. Go to Settings → Devices & Services
2. Find Multi-Agent Router integration
3. Click "Configure"

**Expected Result:**
- Should see summary page with current configuration status
- All fields should show ✓ marks
- Submit button visible

### Step 2: Edit Prompt AI
1. Click "Edit Prompt AI"
2. Change the prompt text
3. Click Submit

**Expected Result:**
- Returns to summary page
- Changes preserved

### Step 3: Edit Router AI
1. Click "Edit Router AI"
2. Change the agent selection
3. Click Submit

**Expected Result:**
- Returns to summary page
- Changes preserved

### Step 4: Edit Custom AI
1. Click "Manage Custom AIs"
2. Click "Edit Custom AI"
3. Select an agent from dropdown
4. Change description or keywords
5. Click Submit

**Expected Result:**
- Returns to Manage Custom AIs menu
- Changes reflected in list

### Step 5: Delete Custom AI
1. In Manage Custom AIs menu, click "Delete Custom AI"
2. Select an agent to delete
3. Click Submit

**Expected Result:**
- Agent removed from list
- Remaining agents still shown

### Step 6: Submit Changes
1. Click "Back to Configuration"
2. Click "Submit & Review"
3. Wait for prompt regeneration

**Expected Result:**
- New prompt generated reflecting remaining agents
- Shows review page

### Step 7: Save Changes
1. Review prompt
2. Click Submit

**Expected Result:**
- Configuration updated successfully
- Integration reloaded with new settings

## Test Scenario 3: Edge Cases

### Test 3.1: Duplicate Name Detection
1. Manage Custom AIs → Add Custom AI
2. Use same name as existing agent
3. Try to submit

**Expected Result:**
- Error message: "An agent with this name already exists"
- Form does not submit

### Test 3.2: Delete All Custom AIs
1. Delete all custom AIs one by one
2. Return to summary

**Expected Result:**
- Status shows: `✗ No Custom AIs configured`
- Submit button disappears

### Test 3.3: AI Generation Failure Fallback
To test this, you would need to simulate AI failure (disconnect agent, etc.)

**Expected Result:**
- Log shows warning about AI failure
- Falls back to static prompt generation
- Continues to review page successfully

### Test 3.4: Empty Prompt Validation
1. In review prompt page, clear all text
2. Try to submit

**Expected Result:**
- Should show error or prevent submission (Home Assistant form validation)

## Log Monitoring

During testing, monitor Home Assistant logs:

```bash
tail -f /config/home-assistant.log | grep multi_agent_router
```

**Expected Log Messages:**
- `Generating router prompt with Prompt AI...` (on submit)
- `✓ Successfully generated router prompt using AI` (on success)
- `Using static fallback prompt` (on AI failure)
- `Added custom AI: [name]` (when adding)
- `Updated custom AI: [name]` (when editing)
- `Deleted custom AI: [name]` (when deleting)

## Validation Checklist

After testing, verify:

- [ ] All configuration saved correctly
- [ ] Router agent has correct prompt applied
- [ ] Prompt AI has correct prompt applied
- [ ] Custom AIs have their prompts applied (if specified)
- [ ] Router works correctly (test with actual queries)
- [ ] No errors in Home Assistant logs
- [ ] Integration can be reconfigured multiple times
- [ ] Navigation works smoothly between all screens
- [ ] Status display is accurate on summary page

## Testing Router Functionality

After configuration, test the router:

1. **Test Question Routing:**
   - Ask: "What's the weather like?"
   - Expected: Routed to thinking/analysis agent

2. **Test Command Routing:**
   - Ask: "Turn on the kitchen lights"
   - Expected: Routed to execution agent

3. **Check Logs:**
   ```bash
   tail -f /config/home-assistant.log | grep -i route
   ```
   - Should see routing decisions in logs

## Rollback Instructions

If issues occur:

1. **Stop Home Assistant:**
   ```bash
   # Via UI: Settings → System → Restart
   ```

2. **Restore Backups:**
   ```bash
   cp /config/custom_components/multi_agent_router/config_flow.py.backup /config/custom_components/multi_agent_router/config_flow.py
   cp /config/custom_components/multi_agent_router/strings.json.backup /config/custom_components/multi_agent_router/strings.json
   ```

3. **Restart Home Assistant**

4. **Report Issues:**
   - Check logs for error messages
   - Note which step caused the issue
   - Document expected vs actual behavior

## Known Limitations

1. **Menu Navigation:**
   - Multiple clicks required due to Home Assistant's menu-only interface
   - Cannot show inline buttons or single-page form

2. **Delete Custom AI:**
   - Separate menu option (not inline with each agent)
   - Home Assistant UI constraint

3. **Submit Button:**
   - Only appears when configuration is valid
   - Cannot be "grayed out" due to menu limitations

## Success Criteria

The implementation is successful if:

1. ✅ Configuration completes without errors
2. ✅ All fields can be edited in options flow
3. ✅ AI-generated prompt contains actual agent names
4. ✅ Status display accurately reflects configuration state
5. ✅ Router functions correctly with generated prompt
6. ✅ No errors in Home Assistant logs
7. ✅ Navigation is intuitive and works smoothly
8. ✅ Edge cases handled gracefully (duplicates, empty lists, etc.)

## Post-Testing

After successful testing:

1. Document any issues found
2. Remove backup files if no longer needed
3. Consider additional test cases based on findings
4. Update documentation with any clarifications
