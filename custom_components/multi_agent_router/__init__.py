"""Multi-Agent Router integration for Home Assistant."""
import json
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_AGENTS,
    CONF_AGENT,
    CONF_AGENT_PROMPT,
    CONF_AGENT_NAME,
    CONF_AGENT_DESCRIPTION,
    CONF_AGENT_KEYWORDS,
    DOMAIN,
)
from .conversation_agent import MultiAgentRouter

_LOGGER = logging.getLogger(__name__)


async def async_build_agent_prompt_with_ai(
    hass: HomeAssistant,
    agents: list[dict]
) -> str:
    """Build router prompt using Jarvis Prompt Generator AI.

    Falls back to static prompt if AI generation fails.
    """
    from .config_flow import build_agent_prompt  # Import fallback

    # Prepare agent data as JSON for Prompt Generator
    agent_data = []
    for agent in agents:
        agent_data.append({
            "name": agent[CONF_AGENT_NAME],
            "description": agent[CONF_AGENT_DESCRIPTION],
            "keywords": agent.get(CONF_AGENT_KEYWORDS, "")
        })

    agent_json = json.dumps(agent_data, indent=2)

    # Create request for Prompt Generator
    prompt_request = f"""Generate a router system prompt for a multi-agent routing system.

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

    try:
        _LOGGER.info("Calling Jarvis Prompt Generator AI to create router prompt...")

        # Call the Prompt Generator AI
        response = await hass.services.async_call(
            "conversation",
            "process",
            {
                "agent_id": "conversation.jarvis_prompt_generator",
                "text": prompt_request,
            },
            blocking=True,
            return_response=True,
        )

        # Extract generated prompt from response
        if hasattr(response, 'response') and hasattr(response.response, 'speech'):
            speech_obj = response.response.speech
            if hasattr(speech_obj, 'plain') and hasattr(speech_obj.plain, 'speech'):
                generated_prompt = speech_obj.plain.speech
                if generated_prompt and generated_prompt.strip():
                    _LOGGER.info("✓ Successfully generated router prompt using AI (%d chars)",
                                len(generated_prompt))
                    return generated_prompt.strip()

        _LOGGER.warning("AI response had no speech content, using fallback")

    except Exception as e:
        _LOGGER.warning("Failed to generate prompt with AI: %s. Using fallback.", e)

    # Fallback to static prompt
    _LOGGER.info("Using static fallback prompt")
    return build_agent_prompt(agents)


async def async_update_agent_prompt(
    hass: HomeAssistant,
    agent_id: str,
    prompt: str
) -> bool:
    """Update the agent's system prompt in its config entry.

    Returns True if successful, False otherwise.
    """
    try:
        # Get the entity registry to find the agent entity
        entity_registry = er.async_get(hass)

        # Find the conversation agent entity
        entity_entry = entity_registry.async_get(agent_id)
        if not entity_entry:
            _LOGGER.warning(
                "Could not find agent entity %s in entity registry",
                agent_id
            )
            return False

        # Get the config entry for this entity
        config_entry_id = entity_entry.config_entry_id
        if not config_entry_id:
            _LOGGER.warning(
                "Agent entity %s has no associated config entry",
                agent_id
            )
            return False

        # Get the config entry
        config_entry = hass.config_entries.async_get_entry(config_entry_id)
        if not config_entry:
            _LOGGER.warning(
                "Could not find config entry %s for agent",
                config_entry_id
            )
            return False

        # Check if this is an OpenAI Conversation integration
        if config_entry.domain not in ["openai_conversation", "extended_openai_conversation"]:
            _LOGGER.warning(
                "Agent %s is from domain %s, not OpenAI Conversation. "
                "Automatic prompt update is only supported for OpenAI-based agents.",
                agent_id,
                config_entry.domain
            )
            return False

        # Check if this is a subentry agent (format: conversation.{name})
        if agent_id.startswith("conversation."):
            # Extract the agent name from the agent_id
            agent_name_part = agent_id.replace("conversation.", "")

            # Search for matching subentry
            for subentry in config_entry.subentries:
                try:
                    # ConfigEntrySubEntry is an object with attributes, not a dict
                    # Access attributes safely using getattr()
                    subentry_type = getattr(subentry, "subentry_type", None)

                    if subentry_type == "conversation":
                        # Match by title (case-insensitive, with underscores converted to spaces)
                        subentry_title = getattr(subentry, "title", "")
                        normalized_title = subentry_title.lower().replace(" ", "_")

                        if normalized_title == agent_name_part:
                            # Found the matching subentry - convert to dict for downstream functions
                            subentry_id = getattr(subentry, "subentry_id", None)
                            subentry_data = getattr(subentry, "data", {})

                            subentry_dict = {
                                "subentry_type": subentry_type,
                                "title": subentry_title,
                                "subentry_id": subentry_id,
                                "data": subentry_data
                            }

                            _LOGGER.debug(
                                "Found matching subentry '%s' (id: %s) for agent %s",
                                subentry_title,
                                subentry_id,
                                agent_id
                            )
                            return await async_update_subentry_prompt(
                                hass, config_entry, subentry, subentry_dict, prompt
                            )

                except (AttributeError, TypeError) as e:
                    _LOGGER.debug(
                        "Skipping invalid subentry during iteration: %s",
                        str(e)
                    )
                    continue

            _LOGGER.warning(
                "Could not find subentry for agent %s in config entry %s (has %d subentries)",
                agent_id,
                config_entry_id,
                len(config_entry.subentries)
            )
            # Fall through to try updating parent entry as fallback

        # Update the prompt in the config entry options (parent entry or fallback)
        # OpenAI Conversation stores the prompt in options
        new_options = dict(config_entry.options)
        new_options["prompt"] = prompt

        hass.config_entries.async_update_entry(
            config_entry,
            options=new_options
        )

        _LOGGER.info(
            "Successfully updated agent %s system prompt (parent entry)",
            agent_id
        )
        return True

    except Exception as e:
        _LOGGER.error(
            "Failed to update agent %s system prompt: %s",
            agent_id,
            str(e),
            exc_info=True
        )
        return False


async def async_update_subentry_prompt(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    subentry_obj,
    subentry_dict: dict,
    prompt: str
) -> bool:
    """Update a subentry's prompt in the OpenAI Conversation config entry.

    Args:
        hass: HomeAssistant instance
        config_entry: The parent config entry
        subentry_obj: The actual ConfigEntrySubEntry object from config_entry.subentries
        subentry_dict: Dictionary representation of the subentry for easy access
        prompt: The new prompt to set

    Returns True if successful, False otherwise.
    """
    try:
        # Create a copy of the subentry data with updated prompt
        updated_subentry_data = dict(subentry_dict.get("data", {}))
        updated_subentry_data["prompt"] = prompt

        # Create updated subentry dict
        updated_subentry = dict(subentry_dict)
        updated_subentry["data"] = updated_subentry_data

        # Find and replace the subentry in the list
        updated_subentries = []
        subentry_id_to_match = subentry_dict.get("subentry_id")

        for existing_subentry in config_entry.subentries:
            # Access the subentry_id attribute from the object
            existing_id = getattr(existing_subentry, "subentry_id", None)

            if existing_id == subentry_id_to_match:
                updated_subentries.append(updated_subentry)
            else:
                updated_subentries.append(existing_subentry)

        # Update the config entry with new subentries
        hass.config_entries.async_update_entry(
            config_entry,
            subentries=updated_subentries
        )

        _LOGGER.info(
            "Successfully updated subentry prompt for '%s' (subentry_id: %s)",
            subentry_dict.get("title"),
            subentry_dict.get("subentry_id")
        )
        return True

    except Exception as e:
        _LOGGER.error(
            "Failed to update subentry prompt: %s",
            str(e),
            exc_info=True
        )
        return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Multi-Agent Router from a config entry."""
    # Store config
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry

    # Extract configuration
    agent_id = entry.data[CONF_AGENT]
    agents = entry.data[CONF_AGENTS]

    # Try to get existing prompt, or generate with AI
    stored_prompt = entry.data.get(CONF_AGENT_PROMPT)
    if stored_prompt:
        agent_prompt = stored_prompt
        _LOGGER.info("Using stored router prompt")
    else:
        # Generate new prompt using AI
        _LOGGER.info("No stored prompt found, generating with AI...")
        agent_prompt = await async_build_agent_prompt_with_ai(hass, agents)

        # Update config entry with generated prompt
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_AGENT_PROMPT: agent_prompt}
        )

    _LOGGER.info(
        "Setting up Multi-Agent Router with agent: %s, %d specialized agents",
        agent_id,
        len(agents)
    )
    _LOGGER.debug("Agent ID: %s", agent_id)
    _LOGGER.debug("Agent prompt (first 200 chars):\n%s...", agent_prompt[:200])

    # Attempt to auto-update the agent's system prompt
    update_success = await async_update_agent_prompt(
        hass,
        agent_id,
        agent_prompt
    )

    if not update_success:
        _LOGGER.warning(
            "Could not automatically update agent system prompt. "
            "Please manually set the system prompt for %s to:\n%s",
            agent_id,
            agent_prompt
        )

    # Create and register conversation agent
    from homeassistant.components import conversation

    agent = MultiAgentRouter(
        hass=hass,
        entry=entry,
        agent_id=agent_id,
        agent_prompt=agent_prompt,
        agents=agents,
    )

    conversation.async_set_agent(hass, entry, agent)

    # Register prompt regeneration service
    async def handle_regenerate_prompt(call):
        """Regenerate router prompt using AI."""
        _LOGGER.info("Regenerating router prompt via service call...")

        agents = entry.data[CONF_AGENTS]
        new_prompt = await async_build_agent_prompt_with_ai(hass, agents)

        # Update config entry
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_AGENT_PROMPT: new_prompt}
        )

        _LOGGER.info("✓ Router prompt regenerated, reloading integration...")

        # Reload integration to apply new prompt
        await hass.config_entries.async_reload(entry.entry_id)

    # Register service (only once)
    if not hass.services.has_service(DOMAIN, "regenerate_prompt"):
        hass.services.async_register(
            DOMAIN,
            "regenerate_prompt",
            handle_regenerate_prompt
        )
        _LOGGER.info("Registered multi_agent_router.regenerate_prompt service")

    # Set up update listener for config changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    from homeassistant.components import conversation

    conversation.async_unset_agent(hass, entry)
    hass.data[DOMAIN].pop(entry.entry_id, None)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
