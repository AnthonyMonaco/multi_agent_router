# Example Configurations

This directory contains example configuration files for integrating the Multi-Agent Router with Home Assistant's voice pipeline.

## Files

### custom_sentences.yaml
This file defines a custom intent that captures all user input and routes it through the Multi-Agent Router. Place this file in your Home Assistant `custom_sentences/en/` directory.

### intent_script.yaml
This file defines the intent script that calls the Multi-Agent Router with the user's query. Place this file in your Home Assistant `intents/` directory.

## Setup Instructions

### Method 1: Direct Voice Pipeline (Simplest)

1. Install and configure the Multi-Agent Router integration
2. Go to **Settings** → **Voice Assistants**
3. Select your voice assistant
4. Under "Conversation agent", select "Multi-Agent Router"
5. Done! All voice commands will now be routed through your configured agents

### Method 2: Custom Intent (Advanced)

Use this method if you want more control or want to route only specific commands through the Multi-Agent Router.

1. Install and configure the Multi-Agent Router integration

2. Copy `custom_sentences.yaml` to `custom_sentences/en/multi_agent.yaml` in your Home Assistant config directory

3. Copy `intent_script.yaml` to `intents/multi_agent_route.yaml` in your Home Assistant config directory

4. Ensure your main `configuration.yaml` includes:
   ```yaml
   intent_script: !include_dir_merge_named intents

   conversation:
     intents:
       MultiAgentRoute:
   ```

5. Restart Home Assistant

6. Test with a voice command or by calling the service:
   ```yaml
   service: conversation.process
   data:
     agent_id: conversation.multi_agent_router
     text: "what's the weather"
   ```

## Example Agent Configuration

Here's an example of how you might configure your specialized agents:

### Router Agent
- **Agent**: `conversation.openai_router` (or any LLM-based conversation agent)
- **Purpose**: Classify user requests and return the target agent name

### Specialized Agents

1. **Jarvis Think**
   - **Agent**: `conversation.jarvis_think`
   - **Description**: "Questions about weather, time, date, general knowledge, calculations, definitions, explanations"

2. **Jarvis Do**
   - **Agent**: `conversation.jarvis_do`
   - **Description**: "Commands to control lights, switches, locks, thermostats, fans, covers, scenes, routines, appliances"

3. **Security**
   - **Agent**: `conversation.security_agent`
   - **Description**: "Questions and commands about alarms, security system, cameras, door locks, window sensors, motion sensors, security status"

4. **Gardening**
   - **Agent**: `conversation.garden_agent`
   - **Description**: "Questions and commands about irrigation, sprinklers, plants, soil moisture, outdoor sensors, weather conditions, watering schedules"

## Testing

After setup, test the routing with these example queries:

- "what is the weather today" → Should route to Jarvis Think
- "turn on the living room lights" → Should route to Jarvis Do
- "is the front door locked" → Should route to Security
- "water the garden" → Should route to Gardening

Enable debug logging to see routing decisions:

```yaml
logger:
  default: info
  logs:
    custom_components.multi_agent_router: debug
```

## Troubleshooting

If commands aren't routing correctly:

1. Check that all configured agents are working individually
2. Review agent descriptions for clarity and distinctiveness
3. Check Home Assistant logs for routing decisions
4. Ensure the router agent is responding with just the agent name
