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
    CONF_PROMPT_GENERATOR_AGENT,
    CONF_PROMPT_GENERATOR_PROMPT,
    DEFAULT_PROMPT_GENERATOR_AGENT,
    DEFAULT_PROMPT_GENERATOR_PROMPT,
    DOMAIN,
)
from .conversation_agent import MultiAgentRouter

_LOGGER = logging.getLogger(__name__)


async def async_build_agent_prompt_with_ai(
    hass: HomeAssistant,
    agents: list[dict],
    prompt_generator_agent: str = None,
    prompt_generator_prompt: str = None
) -> str:
    """Build router prompt using configured Prompt Generator AI.

    Falls back to static prompt if AI generation fails.

    Args:
        hass: HomeAssistant instance
        agents: List of agent configurations
        prompt_generator_agent: Agent ID to use for generating prompts
        prompt_generator_prompt: Template prompt for the generator agent
    """
    from .config_flow import build_agent_prompt  # Import fallback

    # Use defaults if not provided
    if not prompt_generator_agent:
        prompt_generator_agent = DEFAULT_PROMPT_GENERATOR_AGENT
    if not prompt_generator_prompt:
        prompt_generator_prompt = DEFAULT_PROMPT_GENERATOR_PROMPT

    # Prepare agent data as JSON for Prompt Generator
    agent_data = []
    for agent in agents:
        agent_data.append({
            "name": agent[CONF_AGENT_NAME],
            "description": agent[CONF_AGENT_DESCRIPTION],
            "keywords": agent.get(CONF_AGENT_KEYWORDS, "")
        })

    agent_json = json.dumps(agent_data, indent=2)

    # Create request for Prompt Generator by replacing {agent_json} placeholder
    prompt_request = prompt_generator_prompt.replace("{agent_json}", agent_json)

    try:
        _LOGGER.info("Calling Prompt Generator AI (%s) to create router prompt...", prompt_generator_agent)

        # Call the Prompt Generator AI
        response = await hass.services.async_call(
            "conversation",
            "process",
            {
                "agent_id": prompt_generator_agent,
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


def normalize_agent_name(name: str) -> str:
    """Normalize agent name for comparison.

    Converts between formats like 'conversation.jarvis_router' and 'Jarvis Router'.
    """
    # Remove 'conversation.' prefix if present
    if name.startswith("conversation."):
        name = name[13:]  # len("conversation.") = 13

    # Convert underscores and hyphens to spaces, then normalize case
    return name.lower().replace("_", " ").replace("-", " ").strip()


async def async_update_agent_prompt(
    hass: HomeAssistant,
    agent_id: str,
    prompt: str
) -> bool:
    """Update the agent's system prompt, supporting both entities and subentries.

    Returns True if successful, False otherwise.
    """
    try:
        # Get the entity registry to find the agent entity
        entity_registry = er.async_get(hass)

        # Find the conversation agent entity
        entity_entry = entity_registry.async_get(agent_id)

        if entity_entry:
            # Entity found - use existing entity-based logic
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

            _LOGGER.debug(
                "Updating prompt for agent %s (config entry %s, title: '%s')",
                agent_id,
                config_entry_id,
                config_entry.title
            )

            # Update the prompt in the config entry options
            # OpenAI Conversation stores the prompt in options
            new_options = dict(config_entry.options)
            new_options["prompt"] = prompt

            hass.config_entries.async_update_entry(
                config_entry,
                options=new_options
            )

            _LOGGER.info(
                "Successfully updated agent %s system prompt in config entry %s",
                agent_id,
                config_entry_id
            )
            return True

        else:
            # Entity not found - try to find as subentry
            _LOGGER.debug(
                "Agent %s not found as entity, checking OpenAI subentries...",
                agent_id
            )

            # Normalize the agent name for matching
            normalized_agent_name = normalize_agent_name(agent_id)
            _LOGGER.debug("Normalized agent name for matching: '%s' (from agent_id: '%s')", normalized_agent_name, agent_id)

            # Search through all OpenAI conversation config entries
            for entry in hass.config_entries.async_entries("openai_conversation"):
                _LOGGER.debug("Checking OpenAI config entry: %s (title: '%s')", entry.entry_id, entry.title)
                # Check each subentry
                for subentry_obj in entry.subentries:
                    # Get subentry title and normalize it
                    subentry_title = getattr(subentry_obj, "title", "")
                    normalized_subentry_title = normalize_agent_name(subentry_title)
                    _LOGGER.debug("  Checking subentry '%s' -> normalized: '%s' (match: %s)",
                                 subentry_title, normalized_subentry_title,
                                 normalized_agent_name == normalized_subentry_title)

                    if normalized_agent_name == normalized_subentry_title:
                        _LOGGER.info(
                            "Found agent %s as subentry '%s' (subentry_id: %s) in OpenAI config entry %s",
                            agent_id,
                            subentry_title,
                            getattr(subentry_obj, "subentry_id", "unknown"),
                            entry.entry_id
                        )

                        # Convert subentry object to dict for async_update_subentry_prompt
                        subentry_dict = {
                            "subentry_id": getattr(subentry_obj, "subentry_id", None),
                            "title": subentry_title,
                            "data": getattr(subentry_obj, "data", {}),
                        }

                        # Update the subentry prompt
                        return await async_update_subentry_prompt(
                            hass, entry, subentry_obj, subentry_dict, prompt
                        )

            # Not found as entity or subentry
            _LOGGER.warning(
                "Could not find agent %s as entity or subentry in OpenAI conversation",
                agent_id
            )
            return False

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
    prompt_generator_agent = entry.data.get(
        CONF_PROMPT_GENERATOR_AGENT,
        DEFAULT_PROMPT_GENERATOR_AGENT
    )
    prompt_generator_prompt = entry.data.get(
        CONF_PROMPT_GENERATOR_PROMPT,
        DEFAULT_PROMPT_GENERATOR_PROMPT
    )

    # Try to get existing prompt, or generate with AI
    stored_prompt = entry.data.get(CONF_AGENT_PROMPT)
    if stored_prompt:
        agent_prompt = stored_prompt
        _LOGGER.info("Using stored router prompt")
    else:
        # Generate new prompt using AI
        _LOGGER.info("No stored prompt found, generating with AI...")
        agent_prompt = await async_build_agent_prompt_with_ai(
            hass,
            agents,
            prompt_generator_agent,
            prompt_generator_prompt
        )

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
    _LOGGER.info("🔄 Attempting to auto-update router agent prompt for: %s", agent_id)
    update_success = await async_update_agent_prompt(
        hass,
        agent_id,
        agent_prompt
    )

    if not update_success:
        _LOGGER.warning(
            "❌ Could not automatically update agent system prompt. "
            "Please manually set the system prompt for %s to:\n%s",
            agent_id,
            agent_prompt
        )
    else:
        _LOGGER.info("✅ Successfully auto-updated router agent prompt for: %s", agent_id)

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
        prompt_gen_agent = entry.data.get(
            CONF_PROMPT_GENERATOR_AGENT,
            DEFAULT_PROMPT_GENERATOR_AGENT
        )
        prompt_gen_prompt = entry.data.get(
            CONF_PROMPT_GENERATOR_PROMPT,
            DEFAULT_PROMPT_GENERATOR_PROMPT
        )

        new_prompt = await async_build_agent_prompt_with_ai(
            hass,
            agents,
            prompt_gen_agent,
            prompt_gen_prompt
        )

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
