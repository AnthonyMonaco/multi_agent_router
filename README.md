# Multi-Agent Router for Home Assistant

A Home Assistant custom integration that intelligently routes conversation requests to specialized AI agents based on their purpose.

## Features

- **Dynamic Routing**: Automatically routes user requests to the appropriate specialized agent
- **Flexible Configuration**: Add, edit, and remove specialized agents through the UI
- **Automatic Prompt Generation**: Dynamically builds routing instructions based on your agent configuration
- **Fallback Handling**: Gracefully handles routing failures
- **Voice Pipeline Integration**: Works seamlessly with Home Assistant's voice assistant pipeline

## How It Works

1. You configure a **router agent** (e.g., an OpenAI conversation agent) that classifies user requests
2. You configure multiple **specialized agents**, each with a name and description of what they handle
3. When a user makes a request:
   - The Multi-Agent Router asks the router agent to classify the request
   - Based on the classification, it routes to the appropriate specialized agent
   - The specialized agent's response is returned to the user

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add the repository URL and select "Integration" as the category
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Copy the `multi_agent_router` folder to your `custom_components` directory
2. Restart Home Assistant

## Configuration

### Step 1: Set Up Conversation Agents

Before configuring the Multi-Agent Router, you need to set up your conversation agents. For example:

- **Router Agent**: An OpenAI conversation agent for classification
- **Specialized Agents**:
  - "Questions Agent": Handles general knowledge queries
  - "Commands Agent": Handles device control commands
  - "Security Agent": Handles security-related requests

### Step 2: Add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Multi-Agent Router"
4. Select your **router agent** (the agent that will classify requests)

### Step 3: Configure Specialized Agents

1. Choose **Add Agent** to add your first specialized agent
2. Fill in:
   - **Agent Name**: A descriptive name (e.g., "Questions")
   - **Conversation Agent**: Select the agent entity
   - **Description**: What this agent handles (e.g., "Questions about weather, time, general knowledge")
3. Repeat for each specialized agent
4. Click **Finish** when done

### Example Configuration

**Router Agent**: `conversation.openai_router`

**Specialized Agents**:
1. Name: "Jarvis Think"
   - Agent: `conversation.jarvis_think`
   - Description: "Questions about weather, time, general knowledge, calculations"

2. Name: "Jarvis Do"
   - Agent: `conversation.jarvis_do`
   - Description: "Commands to control lights, locks, thermostats, appliances, scenes"

3. Name: "Security"
   - Agent: `conversation.security_agent`
   - Description: "Questions and commands about alarms, cameras, door locks, security status"

4. Name: "Gardening"
   - Agent: `conversation.garden_agent`
   - Description: "Questions and commands about irrigation, plants, outdoor sensors, weather"

## Voice Pipeline Setup

To use the Multi-Agent Router with voice commands:

### Option 1: Set as Default Agent (Simplest)

1. Go to **Settings** → **Voice Assistants**
2. Select your voice assistant
3. Under "Conversation agent", select "Multi-Agent Router"

### Option 2: Custom Intent (More Flexible)

If you want to keep your existing assistant but route specific commands through the router:

1. Create a custom sentence file in `custom_sentences/en/multi_agent.yaml`:

```yaml
language: "en"
intents:
  MultiAgentRoute:
    data:
      - sentences:
          - "{query}"
lists:
  query:
    wildcard: true
```

2. Create an intent script in `intents/multi_agent_route.yaml`:

```yaml
MultiAgentRoute:
  action:
    - service: conversation.process
      data:
        agent_id: conversation.multi_agent_router
        text: "{{ query }}"
      response_variable: router_response
  speech:
    text: "{{ router_response.response.speech.plain.speech }}"
```

## Managing Agents

### Editing Configuration

1. Go to **Settings** → **Devices & Services**
2. Find "Multi-Agent Router" and click **Configure**
3. You can:
   - Change the router agent
   - Add new specialized agents
   - Edit existing agents
   - Remove agents

### Updating Agent Descriptions

The router's classification is based on agent descriptions. Make them:
- **Specific**: Include examples of what the agent handles
- **Distinct**: Avoid overlapping descriptions between agents
- **Comprehensive**: List all major capabilities

Good description:
```
"Questions about weather, time, date, general knowledge, calculations, definitions"
```

Poor description:
```
"Handles questions"  # Too vague
```

## Troubleshooting

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.multi_agent_router: debug
```

Check `home-assistant.log` for routing decisions.

### Common Issues

**Issue**: Router always picks the same agent

**Solution**:
- Check agent descriptions are distinct
- Verify router agent has access to the routing prompt
- Enable debug logging to see classification results

**Issue**: "An error occurred while processing your request"

**Solution**:
- Verify all configured agents exist and are working
- Check Home Assistant logs for error details
- Test each specialized agent individually

**Issue**: Router responds with full explanation instead of just agent name

**Solution**:
- The router agent might need a more restrictive system prompt
- Try adjusting the router agent's temperature/settings to be more deterministic

## How the Router Prompt Works

The integration automatically generates a prompt for your router agent based on your configuration. For example:

```
You are a routing assistant. Classify user requests and respond with the agent name.

Available agents:
- "Jarvis Think": Questions about weather, time, general knowledge
- "Jarvis Do": Commands to control lights, locks, thermostats, appliances
- "Security": Questions and commands about alarms, cameras, locks
- "Gardening": Questions and commands about irrigation, plants, outdoor

Examples:
"what's the weather" → Jarvis Think
"turn on the lights" → Jarvis Do
"is the alarm armed" → Security
"water the garden" → Gardening

Respond with EXACTLY the agent name only.
```

This prompt is prepended to each classification request.

## Advanced Usage

### Multiple Routers

You can create multiple instances of this integration with different router and specialized agent configurations for different use cases.

### Cascading Routers

You can use one Multi-Agent Router as a specialized agent in another router for hierarchical routing.

### Agent Specialization Tips

Consider organizing agents by:
- **Function**: Questions vs. Commands vs. Status
- **Domain**: Home Control vs. Entertainment vs. Security
- **Capability**: Simple queries vs. Complex reasoning
- **Context**: Indoor vs. Outdoor, Upstairs vs. Downstairs

## Performance Considerations

- Each request requires two API calls (router + specialized agent)
- Router classification should be fast (use a quick model if possible)
- Agent descriptions are included in every router request

## License

This project is licensed under the MIT License.

## Support

For issues, feature requests, or questions, please open an issue on GitHub.

## Credits

Created for Home Assistant community by Anthony Monaco.
