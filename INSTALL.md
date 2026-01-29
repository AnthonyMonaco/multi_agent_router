# Installation Guide

## Quick Start

### Prerequisites

- Home Assistant 2024.1 or newer
- At least one conversation agent configured (e.g., OpenAI, Claude, Ollama)
- Multiple conversation agents for specialization (recommended)

### Installation Steps

1. **Copy the integration**
   ```bash
   cd /config/custom_components
   # The multi_agent_router directory should be here
   ```

2. **Restart Home Assistant**
   - Go to **Settings** → **System** → **Restart**
   - Or use the command: `ha core restart`

3. **Add the integration**
   - Go to **Settings** → **Devices & Services**
   - Click **+ Add Integration**
   - Search for "Multi-Agent Router"
   - Follow the configuration steps

### Configuration Walkthrough

#### Step 1: Select Router Agent

The router agent is responsible for classifying user requests. Choose an LLM-based conversation agent that can understand instructions and return concise responses.

**Recommended**: OpenAI GPT-3.5 or GPT-4, Claude, or similar

**Not recommended**: Home Assistant's built-in intent matcher (it's not designed for this purpose)

#### Step 2: Add Specialized Agents

For each specialized agent:

1. Click **Add Agent**
2. Fill in:
   - **Name**: A short, clear name (e.g., "Questions", "Commands", "Security")
   - **Agent**: Select the conversation agent entity
   - **Description**: Be specific about what this agent handles

**Tips for descriptions**:
- Include examples of queries/commands
- Be specific: "control lights, switches, locks" instead of "control devices"
- Avoid overlap between agent descriptions
- Use natural language

**Example**:
```
Name: Questions
Agent: conversation.jarvis_think
Description: Questions about weather, time, date, general knowledge,
             calculations, definitions, how things work
```

3. Repeat for each specialized agent
4. You need at least one specialized agent
5. Click **Finish** when done

### Verification

Test that the integration is working:

1. **Enable debug logging** (optional but recommended):

   Add to `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.multi_agent_router: debug
   ```

   Restart Home Assistant

2. **Test via Developer Tools**:

   - Go to **Developer Tools** → **Services**
   - Select `conversation.process`
   - Fill in:
     ```yaml
     agent_id: conversation.multi_agent_router
     text: "what's the weather"
     ```
   - Click **Call Service**

3. **Check logs**:

   - Go to **Settings** → **System** → **Logs**
   - Or check `/config/home-assistant.log`
   - Look for entries like:
     ```
     [custom_components.multi_agent_router] Processing input: 'what's the weather'
     [custom_components.multi_agent_router] Router classified as: 'Questions'
     [custom_components.multi_agent_router] Routing to agent 'Questions' (conversation.jarvis_think)
     ```

### Voice Pipeline Setup (Optional)

To use with voice commands:

**Option 1: Set as Default Agent**

1. Go to **Settings** → **Voice Assistants**
2. Select your voice assistant
3. Under "Conversation agent", select "Multi-Agent Router"

**Option 2: Custom Intent**

See `examples/README.md` for detailed instructions on setting up custom intents.

## Troubleshooting

### Integration doesn't appear in Add Integration

- Ensure the `multi_agent_router` directory is in `custom_components/`
- Restart Home Assistant
- Check logs for errors during startup

### "Configuration failed"

- Verify all conversation agents exist and are working
- Test each agent individually via Developer Tools
- Check Home Assistant logs for specific error messages

### Router always picks the wrong agent

- Review agent descriptions for clarity and uniqueness
- Enable debug logging to see classification results
- Try rephrasing agent descriptions
- Ensure router agent is capable of following instructions

### "An error occurred while processing your request"

- Check that all configured agents are accessible
- Test each specialized agent individually
- Review Home Assistant logs for detailed error messages
- Verify network connectivity if using cloud-based agents

## Updating Configuration

To modify your configuration:

1. Go to **Settings** → **Devices & Services**
2. Find "Multi-Agent Router"
3. Click **Configure**
4. Make your changes:
   - Change router agent
   - Add/edit/remove specialized agents
5. Changes take effect immediately (no restart needed)

## Uninstallation

1. Remove the integration:
   - Go to **Settings** → **Devices & Services**
   - Find "Multi-Agent Router"
   - Click the three dots → **Delete**

2. (Optional) Remove the files:
   ```bash
   rm -rf /config/custom_components/multi_agent_router
   ```

3. Restart Home Assistant

## Next Steps

- Read `README.md` for detailed usage information
- Check `examples/` for voice pipeline integration examples
- Enable debug logging to understand routing decisions
- Experiment with different agent descriptions for optimal routing
