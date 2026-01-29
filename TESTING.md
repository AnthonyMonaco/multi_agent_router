# Testing Guide

This guide provides a comprehensive testing plan for the Multi-Agent Router integration.

## Pre-Testing Setup

### 1. Create Test Conversation Agents

Before testing the router, you'll need at least 2-3 conversation agents. For testing purposes, you can use:

- **OpenAI** (recommended for testing)
- **Claude via OpenAI-compatible API**
- **Ollama** (local testing)
- **Mock agents** (for development)

### 2. Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.multi_agent_router: debug
    homeassistant.components.conversation: debug
```

Restart Home Assistant after adding this.

## Test Plan

### Phase 1: Installation & Configuration

#### Test 1.1: Installation
- [ ] Copy integration to `custom_components/multi_agent_router`
- [ ] Restart Home Assistant
- [ ] Check logs for errors during startup
- [ ] Verify no errors in `/config/home-assistant.log`

**Expected Result**: Integration loads without errors

#### Test 1.2: Add Integration via UI
- [ ] Go to Settings → Devices & Services
- [ ] Click "+ Add Integration"
- [ ] Search for "Multi-Agent Router"
- [ ] Integration appears in search results

**Expected Result**: Integration is discoverable

#### Test 1.3: Configure Router Agent
- [ ] Select a router agent from dropdown
- [ ] List shows all available conversation agents
- [ ] Selected agent is saved

**Expected Result**: Router agent is configured successfully

#### Test 1.4: Add First Specialized Agent
- [ ] Click "Add Agent"
- [ ] Fill in:
  - Name: "Test Agent 1"
  - Agent: (select any agent)
  - Description: "Test description for agent 1"
- [ ] Click Submit

**Expected Result**: Agent is added to configuration

#### Test 1.5: Add Multiple Specialized Agents
- [ ] Add second agent with different name
- [ ] Add third agent with different name
- [ ] Click "Finish"

**Expected Result**: Configuration completes with multiple agents

#### Test 1.6: Configuration Validation
- [ ] Try to finish with zero agents
- [ ] Should show error: "You must configure at least one specialized agent"
- [ ] Try to add agent with duplicate name
- [ ] Should show error: "An agent with this name already exists"

**Expected Result**: Validation prevents invalid configurations

### Phase 2: Basic Routing

#### Test 2.1: Router Agent Entity
- [ ] Go to Developer Tools → States
- [ ] Find entity: `conversation.multi_agent_router`
- [ ] Entity exists and shows as "Multi-Agent Router"

**Expected Result**: Router entity is registered

#### Test 2.2: Simple Classification
- [ ] Go to Developer Tools → Services
- [ ] Call `conversation.process`:
  ```yaml
  agent_id: conversation.multi_agent_router
  text: "test query for agent 1"
  ```
- [ ] Check response
- [ ] Check logs for routing decision

**Expected Result**: Request is routed to appropriate agent

#### Test 2.3: Multiple Different Queries
Test with queries that should route to different agents:

- [ ] Query 1: "what is the weather" → Agent 1
- [ ] Query 2: "turn on the lights" → Agent 2
- [ ] Query 3: "another test query" → Agent 3

**Expected Result**: Each query routes to correct specialized agent

#### Test 2.4: Verify Logs Show Routing
Check logs after each test:
```
[custom_components.multi_agent_router] Processing input: 'test query'
[custom_components.multi_agent_router] Router classified as: 'Agent Name'
[custom_components.multi_agent_router] Routing to agent 'Agent Name' (conversation.agent_id)
[custom_components.multi_agent_router] Target agent response: 'response text'
```

**Expected Result**: Logs show complete routing flow

### Phase 3: Edge Cases & Error Handling

#### Test 3.1: Router Returns Unknown Agent
- [ ] Send query that router might not classify correctly
- [ ] Check logs for fallback behavior
- [ ] Verify fallback to first configured agent

**Expected Result**: Graceful fallback to first agent

#### Test 3.2: Router Agent Fails
- [ ] Temporarily disable router agent (if possible)
- [ ] Send test query
- [ ] Check logs for error handling
- [ ] Verify fallback behavior

**Expected Result**: Error logged, request falls back to first agent

#### Test 3.3: Target Agent Fails
- [ ] Send query that routes to specific agent
- [ ] Temporarily disable that agent
- [ ] Check error message

**Expected Result**: Error message returned to user

#### Test 3.4: Empty Query
- [ ] Send empty string: `text: ""`
- [ ] Send whitespace only: `text: "   "`

**Expected Result**: Handled gracefully without crash

#### Test 3.5: Very Long Query
- [ ] Send query with 500+ words
- [ ] Check processing time
- [ ] Verify response

**Expected Result**: Long queries processed successfully

### Phase 4: Configuration Management

#### Test 4.1: Edit Configuration
- [ ] Go to Settings → Devices & Services
- [ ] Find Multi-Agent Router
- [ ] Click "Configure"
- [ ] Change router agent
- [ ] Verify change takes effect

**Expected Result**: Configuration updates without restart

#### Test 4.2: Add Agent After Initial Setup
- [ ] Open configuration
- [ ] Add new specialized agent
- [ ] Test routing to new agent

**Expected Result**: New agent immediately available for routing

#### Test 4.3: Edit Existing Agent
- [ ] Open configuration → Manage Agents
- [ ] Click "Edit Agent"
- [ ] Select agent to edit
- [ ] Change description
- [ ] Test routing with new description

**Expected Result**: Updated description affects routing

#### Test 4.4: Remove Agent
- [ ] Open configuration → Manage Agents
- [ ] Click "Remove Agent"
- [ ] Remove one agent (keeping at least 1)
- [ ] Verify agent is removed

**Expected Result**: Agent removed from configuration

#### Test 4.5: Prevent Removing Last Agent
- [ ] Try to remove all agents
- [ ] Should show error

**Expected Result**: Cannot remove last agent

### Phase 5: Voice Pipeline Integration

#### Test 5.1: Set as Voice Assistant Agent
- [ ] Go to Settings → Voice Assistants
- [ ] Select voice assistant
- [ ] Set conversation agent to "Multi-Agent Router"
- [ ] Save configuration

**Expected Result**: Router available in voice assistant settings

#### Test 5.2: Voice Command Test (if hardware available)
- [ ] Speak test command
- [ ] Verify routing through logs
- [ ] Check response is correct

**Expected Result**: Voice commands route correctly

#### Test 5.3: Custom Intent Setup
- [ ] Copy `examples/custom_sentences.yaml` to `custom_sentences/en/`
- [ ] Copy `examples/intent_script.yaml` to `intents/`
- [ ] Restart Home Assistant
- [ ] Test with conversation service

**Expected Result**: Custom intent routes through Multi-Agent Router

### Phase 6: Performance & Reliability

#### Test 6.1: Response Time
- [ ] Send 10 test queries
- [ ] Measure average response time
- [ ] Compare with direct agent calls

**Expected Result**: Acceptable overhead (< 1 second additional latency)

#### Test 6.2: Concurrent Requests
- [ ] Send multiple requests simultaneously
- [ ] Verify all are handled correctly
- [ ] Check for race conditions

**Expected Result**: All requests processed correctly

#### Test 6.3: Router Prompt Generation
- [ ] Add agent with special characters in description
- [ ] Check logs for generated prompt
- [ ] Verify prompt is well-formed

**Expected Result**: Prompt handles special characters correctly

#### Test 6.4: Memory Usage
- [ ] Monitor Home Assistant memory usage
- [ ] Send 100 test queries
- [ ] Check for memory leaks

**Expected Result**: No memory leaks, stable memory usage

### Phase 7: Integration Testing

#### Test 7.1: Home Assistant Restart
- [ ] Configure router with agents
- [ ] Restart Home Assistant
- [ ] Verify configuration persists
- [ ] Test routing still works

**Expected Result**: Configuration survives restart

#### Test 7.2: Backup & Restore
- [ ] Create Home Assistant backup
- [ ] Remove integration
- [ ] Restore from backup
- [ ] Verify integration restored with configuration

**Expected Result**: Configuration included in backups

#### Test 7.3: Multiple Router Instances (if supported)
- [ ] Try to add second instance of integration
- [ ] Should be prevented (single instance)

**Expected Result**: Only one instance allowed

## Test Results Template

Use this template to record test results:

```
Test Date: ____________________
Home Assistant Version: ____________________
Integration Version: 1.0.0

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| 1.1 | Installation | ⬜ Pass ⬜ Fail | |
| 1.2 | Add Integration via UI | ⬜ Pass ⬜ Fail | |
| ... | ... | ... | |

Issues Found:
1.
2.
3.

Performance Metrics:
- Average routing time: ______ ms
- Memory usage: ______ MB
- Concurrent request handling: ⬜ Pass ⬜ Fail

Overall Status: ⬜ Pass ⬜ Fail
```

## Automated Testing (Future)

For developers contributing to this integration:

```python
# Example test structure
async def test_router_classification():
    """Test that router classifies requests correctly."""
    # Setup
    router = MultiAgentRouter(...)

    # Test
    result = await router.async_process(input)

    # Assert
    assert result.agent_name == "Expected Agent"
```

## Debugging Tips

### Enable Verbose Logging
```yaml
logger:
  default: debug
  logs:
    custom_components.multi_agent_router: debug
    homeassistant.components.conversation: debug
```

### Check Router Classification
Look for this log line:
```
Router classified as: 'Agent Name'
```

### Test Router Agent Directly
```yaml
service: conversation.process
data:
  agent_id: conversation.your_router_agent
  text: |
    You are a routing assistant. Classify user requests and respond with the agent name.

    Available agents:
    - "Agent 1": Description 1
    - "Agent 2": Description 2

    Classify: what is the weather
```

Expected response should be just: "Agent 1" or "Agent 2"

## Common Issues & Solutions

### Issue: Router returns full explanation
**Solution**: Router agent needs to be more concise. Try:
- Using a more instruction-following model
- Adjusting temperature to be lower (more deterministic)
- Simplifying agent descriptions

### Issue: Always routes to same agent
**Solution**:
- Check agent descriptions are distinct
- Verify router agent is processing the prompt correctly
- Test router agent classification directly

### Issue: Integration won't load
**Solution**:
- Check Python syntax: `python3 -m py_compile *.py`
- Review Home Assistant logs for import errors
- Verify all dependencies are available

## Success Criteria

The integration passes testing if:

✅ All Phase 1 tests pass (installation & configuration)
✅ All Phase 2 tests pass (basic routing)
✅ At least 80% of Phase 3 tests pass (edge cases)
✅ All Phase 4 tests pass (configuration management)
✅ Response time < 3 seconds average
✅ No memory leaks or crashes
✅ Configuration persists across restarts
