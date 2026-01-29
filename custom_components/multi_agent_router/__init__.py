"""Multi-Agent Router integration for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_AGENTS,
    CONF_AGENT,
    CONF_AGENT_PROMPT,
    DOMAIN,
)
from .conversation_agent import MultiAgentRouter

_LOGGER = logging.getLogger(__name__)


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
                if subentry.get("subentry_type") == "conversation":
                    # Match by title (case-insensitive, with underscores converted to spaces)
                    subentry_title = subentry.get("title", "")
                    normalized_title = subentry_title.lower().replace(" ", "_")
                    if normalized_title == agent_name_part:
                        # Found the matching subentry - update its prompt
                        _LOGGER.debug(
                            "Found matching subentry '%s' (id: %s) for agent %s",
                            subentry_title,
                            subentry.get("subentry_id"),
                            agent_id
                        )
                        return await async_update_subentry_prompt(
                            hass, config_entry, subentry, prompt
                        )

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
    subentry: dict,
    prompt: str
) -> bool:
    """Update a subentry's prompt in the OpenAI Conversation config entry.

    Returns True if successful, False otherwise.
    """
    try:
        # Create a copy of the subentry data with updated prompt
        updated_subentry_data = dict(subentry.get("data", {}))
        updated_subentry_data["prompt"] = prompt

        # Create updated subentry
        updated_subentry = dict(subentry)
        updated_subentry["data"] = updated_subentry_data

        # Find and replace the subentry in the list
        updated_subentries = []
        for existing_subentry in config_entry.subentries:
            if existing_subentry.get("subentry_id") == subentry.get("subentry_id"):
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
            subentry.get("title"),
            subentry.get("subentry_id")
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
    agent_prompt = entry.data[CONF_AGENT_PROMPT]

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
