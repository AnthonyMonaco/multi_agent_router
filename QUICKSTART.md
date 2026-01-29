# Quick Start Guide

Get the Multi-Agent Router running in 5 minutes!

## Prerequisites
- Home Assistant 2024.1+
- At least 2 conversation agents configured

## Installation (2 minutes)

1. **Copy files**
   ```bash
   # The multi_agent_router folder should be in:
   /config/custom_components/multi_agent_router/
   ```

2. **Restart Home Assistant**
   - Settings → System → Restart
   - Wait for restart to complete

3. **Verify installation**
   - Check logs for errors (Settings → System → Logs)
   - Should see: "Successfully loaded multi_agent_router"

## Configuration (3 minutes)

### Step 1: Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search: "Multi-Agent Router"
4. Click to add

### Step 2: Select Router Agent

- **Router Agent**: Select the agent that will classify requests
  - Recommended: OpenAI GPT-3.5 or GPT-4
  - Should be fast and instruction-following

### Step 3: Add Specialized Agents

**Agent 1: Questions**
```
Name: Questions
Agent: conversation.jarvis_think
Description: Questions about weather, time, date, general knowledge, calculations
```

**Agent 2: Commands**
```
Name: Commands
Agent: conversation.jarvis_do
Description: Commands to control lights, switches, locks, thermostats, scenes
```

**Agent 3: Security** (optional)
```
Name: Security
Agent: conversation.security_agent
Description: Questions and commands about alarms, cameras, locks, security status
```

Click **Finish** when done.

## Testing (30 seconds)

### Test via Developer Tools

1. Go to **Developer Tools** → **Services**
2. Select: `conversation.process`
3. Enter:
   ```yaml
   agent_id: conversation.multi_agent_router
   text: "what is the weather"
   ```
4. Click **Call Service**
5. Check response

### Check Logs

1. Go to **Settings** → **System** → **Logs**
2. Filter: "multi_agent_router"
3. Look for:
   ```
   Processing input: 'what is the weather'
   Router classified as: 'Questions'
   Routing to agent 'Questions'
   ```

## Voice Integration (Optional)

### Simple Method
1. Settings → Voice Assistants
2. Select your assistant
3. Conversation agent → **Multi-Agent Router**
4. Save

Done! Voice commands now route through your agents.

## Test Queries

Try these to verify routing:

| Query | Expected Agent |
|-------|---------------|
| "what's the weather" | Questions |
| "turn on living room lights" | Commands |
| "is the alarm armed" | Security |
| "what time is it" | Questions |
| "lock the front door" | Commands |

## Troubleshooting

### Integration doesn't appear
- Check file location: `/config/custom_components/multi_agent_router/`
- Restart Home Assistant again
- Check logs for errors

### Always routes to same agent
- Agent descriptions too similar → Make them more distinct
- Router not following instructions → Try different router model
- Enable debug logging (see below)

### "Error processing request"
- Test each agent individually first
- Check agent IDs are correct
- Review logs for specific error

## Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.multi_agent_router: debug
```

Restart and check logs after each test query.

## Next Steps

- ✅ **Working?** Great! Configure more specialized agents
- ❌ **Issues?** See INSTALL.md or TESTING.md for detailed guides
- 💡 **Want more?** Check README.md for advanced features

## Common Commands

### Restart Home Assistant
```bash
ha core restart
```

### Check logs
```bash
tail -f /config/home-assistant.log | grep multi_agent_router
```

### Test service call (CLI)
```bash
ha service call conversation.process \
  --arguments '{"agent_id": "conversation.multi_agent_router", "text": "test query"}'
```

## Example Agent Configurations

### Home Control Setup
- **Router**: OpenAI GPT-3.5
- **Agent 1**: Questions (knowledge, weather, time)
- **Agent 2**: Commands (lights, switches, locks)
- **Agent 3**: Security (alarms, cameras)

### Advanced Setup
- **Router**: OpenAI GPT-4 (better classification)
- **Agent 1**: General (questions + simple commands)
- **Agent 2**: Home Automation (complex multi-device scenarios)
- **Agent 3**: Entertainment (media, TV, music)
- **Agent 4**: Climate (HVAC, temperature control)

### Minimalist Setup
- **Router**: OpenAI GPT-3.5
- **Agent 1**: Assistant (handles everything)

Yes, even with one agent, the router validates configuration!

## Tips for Success

1. **Keep descriptions specific**
   - Good: "Control lights, switches, locks, thermostats"
   - Bad: "Control devices"

2. **Make descriptions distinct**
   - Avoid overlap between agents
   - Each agent should have clear purpose

3. **Start small**
   - Begin with 2-3 agents
   - Add more as needed

4. **Test incrementally**
   - Test each agent individually first
   - Then test routing
   - Then add voice integration

5. **Monitor logs initially**
   - Enable debug logging during setup
   - Watch routing decisions
   - Adjust descriptions based on results

## That's It!

You're now routing conversation requests to specialized agents. Enjoy your smarter Home Assistant!

For detailed information:
- **Installation**: See INSTALL.md
- **Usage**: See README.md
- **Testing**: See TESTING.md
- **Issues**: See TESTING.md troubleshooting section
