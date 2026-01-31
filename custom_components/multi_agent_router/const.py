"""Constants for Multi-Agent Router."""

DOMAIN = "multi_agent_router"

# Configuration keys
CONF_AGENT = "agent"
CONF_AGENT_PROMPT = "agent_prompt"
CONF_AGENTS = "agents"
CONF_AGENT_NAME = "name"
CONF_AGENT_ID = "agent_id"
CONF_AGENT_DESCRIPTION = "description"

# Agent keywords (new)
CONF_AGENT_KEYWORDS = "agent_keywords"

# Prompt generator configuration
CONF_PROMPT_GENERATOR_AGENT = "prompt_generator_agent"
CONF_PROMPT_GENERATOR_PROMPT = "prompt_generator_prompt"

# Defaults
DEFAULT_AGENT_NAME = "Multi-Agent Router"
DEFAULT_PROMPT_GENERATOR_AGENT = "conversation.jarvis_prompt_generator"

# Default prompt for the prompt generator
DEFAULT_PROMPT_GENERATOR_PROMPT = """Generate a router system prompt for a multi-agent routing system.

The router must classify user requests and respond with ONLY "ROUTE: [Agent Name]" format.

Available agents:
{agent_json}

Requirements:
1. Use ONLY "ROUTE: [exact agent name]" format (e.g., "ROUTE: Jarvis Think")
2. Include 5-8 concrete examples showing routing decisions
3. Examples must use the ACTUAL agent names from the list above
4. Never use placeholders like [AgentName] - always use real names
5. Add explicit routing rules based on agent capabilities
6. Emphasize the router should NEVER answer questions itself
7. Keep prompt concise and deterministic

Generate ONLY the router prompt text, nothing else."""

# Services
SERVICE_REGENERATE_PROMPT = "regenerate_prompt"
