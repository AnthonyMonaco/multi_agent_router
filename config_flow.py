"""Config flow for Multi-Agent Router integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    ConversationAgentSelector,
    ConversationAgentSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_AGENTS,
    CONF_AGENT,
    CONF_AGENT_DESCRIPTION,
    CONF_AGENT_ID,
    CONF_AGENT_KEYWORDS,
    CONF_AGENT_NAME,
    CONF_AGENT_PROMPT,
    CONF_PROMPT_GENERATOR_AGENT,
    CONF_PROMPT_GENERATOR_PROMPT,
    DEFAULT_PROMPT_GENERATOR_AGENT,
    DEFAULT_PROMPT_GENERATOR_PROMPT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def build_agent_prompt(agents: list[dict]) -> str:
    """Build agent prompt using static fallback with real agent names.

    This is the synchronous fallback version used when AI generation is not available.
    For AI-powered prompt generation, see async_build_agent_prompt_with_ai() in __init__.py
    """
    agent_list = []
    for agent in agents:
        agent_info = f'- "{agent[CONF_AGENT_NAME]}": {agent[CONF_AGENT_DESCRIPTION]}'

        # Add keywords if present
        keywords = agent.get(CONF_AGENT_KEYWORDS, "").strip()
        if keywords:
            agent_info += f" (Keywords: {keywords})"

        agent_list.append(agent_info)

    agent_list_text = "\n".join(agent_list)

    # Generate examples using actual agent names from the configuration
    # This ensures no placeholder confusion like [AgentName]
    examples = []
    if len(agents) >= 2:
        # Assume first agent is for thinking/questions, second for execution
        examples = [
            f'"turn on kitchen lights" → ROUTE: {agents[1][CONF_AGENT_NAME]}',
            f'"what\'s the weather in Arvada" → ROUTE: {agents[0][CONF_AGENT_NAME]}',
            f'"tell me about my energy usage" → ROUTE: {agents[0][CONF_AGENT_NAME]}',
            f'"are the doors locked" → ROUTE: {agents[0][CONF_AGENT_NAME]}',
            f'"lock the front door" → ROUTE: {agents[1][CONF_AGENT_NAME]}',
        ]
    elif len(agents) == 1:
        # Only one agent, route everything to it
        examples = [
            f'"turn on kitchen lights" → ROUTE: {agents[0][CONF_AGENT_NAME]}',
            f'"what\'s the weather in Arvada" → ROUTE: {agents[0][CONF_AGENT_NAME]}',
            f'"tell me about my energy usage" → ROUTE: {agents[0][CONF_AGENT_NAME]}',
        ]
    else:
        # No agents configured, use generic placeholder
        examples = [
            '"turn on kitchen lights" → ROUTE: [Agent]',
            '"what\'s the weather" → ROUTE: [Agent]',
        ]

    examples_text = "\n".join(examples)

    return f"""You are a routing assistant. Classify requests and respond with ONLY "ROUTE: [AgentName]"

Available agents:
{agent_list_text}

Routing Rules:
1. ANY question (who, what, when, where, why, how) → Route to thinking/analysis agent
2. ANY request for information or status → Route to thinking/analysis agent
3. Device control commands → Route to execution agent

Examples:
{examples_text}

CRITICAL: Respond with ONLY "ROUTE: [AgentName]" - nothing else. Never try to answer questions yourself."""


class MultiAgentRouterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Multi-Agent Router."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize config flow."""
        self._agent: str | None = None
        self._agents: list[dict] = []
        self._agent_prompt: str | None = None
        self._prompt_generator_agent: str | None = None
        self._prompt_generator_prompt: str | None = None
        self._editing_index: int | None = None

    async def _get_agent_prompt(self, agent_id: str) -> str | None:
        """Fetch the current prompt from a conversation agent's config.

        Args:
            agent_id: The conversation agent entity ID (e.g., "conversation.jarvis_openai")

        Returns:
            The agent's current prompt, or None if not found
        """
        from homeassistant.helpers import entity_registry as er

        # 1. Try entity registry lookup
        entity_registry = er.async_get(self.hass)
        entity = entity_registry.async_get(agent_id)

        if entity and entity.config_entry_id:
            entry = self.hass.config_entries.async_get_entry(entity.config_entry_id)
            if entry and "prompt" in entry.options:
                return entry.options["prompt"]

        # 2. Fallback: Search OpenAI conversation subentries
        from . import normalize_agent_name
        normalized_agent_name = normalize_agent_name(agent_id)

        for entry in self.hass.config_entries.async_entries("openai_conversation"):
            # Check options for prompt
            if "prompt" in entry.options:
                # Match by normalized title
                entry_name = normalize_agent_name(entry.title)
                if entry_name == normalized_agent_name:
                    return entry.options["prompt"]

            # Check subentries
            for subentry_obj in entry.subentries:
                subentry_title = getattr(subentry_obj, "title", "")
                normalized_subentry_title = normalize_agent_name(subentry_title)
                if normalized_agent_name == normalized_subentry_title:
                    subentry_data = getattr(subentry_obj, "data", {})
                    if "prompt" in subentry_data:
                        return subentry_data["prompt"]

        # 3. Return None if not found (user will need to set manually)
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the main menu step."""
        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # Initialize instance variables if not set
        if self._agents is None:
            self._agents = []

        # Show main menu
        return self.async_show_menu(
            step_id="user",
            menu_options={
                "prompt_ai": "Configure Prompt AI",
                "router_ai": "Configure Router AI",
                "custom_ai": "Manage Custom AIs",
                "finish": "Finish Setup"
            },
        )

    async def async_step_prompt_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure Prompt AI (the agent that generates routing prompts)."""
        if user_input is not None:
            # Save configuration
            self._prompt_generator_agent = user_input[CONF_PROMPT_GENERATOR_AGENT]
            self._prompt_generator_prompt = user_input[CONF_PROMPT_GENERATOR_PROMPT]
            _LOGGER.debug(f"Prompt generator configured: {self._prompt_generator_agent}")
            # Return to main menu
            return await self.async_step_user()

        # Pre-fill with current values or defaults
        suggested_agent = self._prompt_generator_agent or DEFAULT_PROMPT_GENERATOR_AGENT
        suggested_prompt = self._prompt_generator_prompt or DEFAULT_PROMPT_GENERATOR_PROMPT

        # If we have an agent selected, try to fetch its current prompt
        if self._prompt_generator_agent and not self._prompt_generator_prompt:
            fetched_prompt = await self._get_agent_prompt(self._prompt_generator_agent)
            if fetched_prompt:
                suggested_prompt = fetched_prompt

        schema = vol.Schema({
            vol.Required(
                CONF_PROMPT_GENERATOR_AGENT,
                description={"suggested_value": suggested_agent}
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_PROMPT_GENERATOR_PROMPT,
                description={"suggested_value": suggested_prompt}
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="prompt_ai",
            data_schema=schema,
        )

    async def async_step_router_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure Router AI (the agent that routes requests)."""
        if user_input is not None:
            # Save configuration
            self._agent = user_input[CONF_AGENT]
            self._agent_prompt = user_input[CONF_AGENT_PROMPT]
            _LOGGER.debug(f"Router agent configured: {self._agent}")
            # Return to main menu
            return await self.async_step_user()

        # Pre-fill with current values or generate prompt
        suggested_agent = self._agent or "homeassistant"
        suggested_prompt = self._agent_prompt

        # If no prompt exists, try to generate one
        if not suggested_prompt:
            if self._agents:
                # Try to generate with AI if we have agents configured
                if self._prompt_generator_agent and self._prompt_generator_prompt:
                    from . import async_build_agent_prompt_with_ai
                    try:
                        suggested_prompt = await async_build_agent_prompt_with_ai(
                            self.hass,
                            self._agents,
                            self._prompt_generator_agent,
                            self._prompt_generator_prompt
                        )
                    except Exception as e:
                        _LOGGER.warning(f"Failed to generate prompt with AI: {e}")
                        suggested_prompt = build_agent_prompt(self._agents)
                else:
                    # Use static fallback
                    suggested_prompt = build_agent_prompt(self._agents)
            else:
                # No agents yet, provide empty prompt
                suggested_prompt = ""

        # If we have a router agent selected, try to fetch its current prompt
        if self._agent and not self._agent_prompt:
            fetched_prompt = await self._get_agent_prompt(self._agent)
            if fetched_prompt:
                suggested_prompt = fetched_prompt

        schema = vol.Schema({
            vol.Required(
                CONF_AGENT,
                description={"suggested_value": suggested_agent}
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_AGENT_PROMPT,
                description={"suggested_value": suggested_prompt}
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="router_ai",
            data_schema=schema,
        )

    async def async_step_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Custom AI management menu."""
        # Build agent list for display
        agent_list = "None configured yet."
        if self._agents:
            agent_list = "\n".join([
                f"- {agent[CONF_AGENT_NAME]} ({agent[CONF_AGENT_ID]})"
                for agent in self._agents
            ])

        return self.async_show_menu(
            step_id="custom_ai",
            menu_options={
                "add_agent": "Add New Custom AI",
                "edit_agent": "Edit Existing Custom AI" if self._agents else None,
                "remove_agent": "Remove Custom AI" if self._agents else None,
                "user": "Back to Main Menu"
            },
            description_placeholders={"agents_list": agent_list}
        )

    async def async_step_select_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which custom AI to edit."""
        if user_input is not None:
            self._editing_index = int(user_input["agent_index"])
            return await self.async_step_add_agent()

        # Create selection options
        agent_choices = [
            {"label": agent[CONF_AGENT_NAME], "value": str(i)}
            for i, agent in enumerate(self._agents)
        ]

        schema = vol.Schema({
            vol.Required("agent_index"): SelectSelector(
                SelectSelectorConfig(
                    options=agent_choices,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="select_custom_ai",
            data_schema=schema,
        )

    async def async_step_add_agent(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a specialized agent."""
        errors = {}
        is_editing = self._editing_index is not None

        if user_input is not None:
            # Validate agent name is unique (except when editing current agent)
            agent_name = user_input[CONF_AGENT_NAME]
            if any(
                i != self._editing_index and agent[CONF_AGENT_NAME] == agent_name
                for i, agent in enumerate(self._agents)
            ):
                errors["base"] = "duplicate_name"
            else:
                # Create agent dict
                agent_dict = {
                    CONF_AGENT_NAME: agent_name,
                    CONF_AGENT_ID: user_input[CONF_AGENT_ID],
                    CONF_AGENT_DESCRIPTION: user_input[CONF_AGENT_DESCRIPTION],
                    CONF_AGENT_KEYWORDS: user_input.get(CONF_AGENT_KEYWORDS, ""),
                    CONF_AGENT_PROMPT: user_input.get(CONF_AGENT_PROMPT, ""),
                }

                if is_editing:
                    # Update existing agent
                    self._agents[self._editing_index] = agent_dict
                    _LOGGER.debug(f"Updated agent: {agent_name} -> {user_input[CONF_AGENT_ID]}")
                    self._editing_index = None
                    # Return to custom AI menu
                    return await self.async_step_custom_ai()
                else:
                    # Add new agent
                    self._agents.append(agent_dict)
                    _LOGGER.debug(f"Added agent: {agent_name} -> {user_input[CONF_AGENT_ID]}")
                    # Return to custom AI menu
                    return await self.async_step_custom_ai()

        # Prepare form schema
        if is_editing:
            # Pre-fill with current agent data
            current_agent = self._agents[self._editing_index]
            suggested_name = current_agent[CONF_AGENT_NAME]
            suggested_agent_id = current_agent[CONF_AGENT_ID]
            suggested_description = current_agent[CONF_AGENT_DESCRIPTION]
            suggested_keywords = current_agent.get(CONF_AGENT_KEYWORDS, "")
            suggested_prompt = current_agent.get(CONF_AGENT_PROMPT, "")
        else:
            # Empty form for new agent
            suggested_name = ""
            suggested_agent_id = "homeassistant"
            suggested_description = ""
            suggested_keywords = ""
            suggested_prompt = ""

        # Try to fetch prompt from selected agent if not already set
        if suggested_agent_id and not suggested_prompt:
            fetched_prompt = await self._get_agent_prompt(suggested_agent_id)
            if fetched_prompt:
                suggested_prompt = fetched_prompt

        # Build schema
        schema = vol.Schema({
            vol.Required(
                CONF_AGENT_NAME,
                description={"suggested_value": suggested_name} if suggested_name else None
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_AGENT_ID,
                description={"suggested_value": suggested_agent_id}
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Optional(
                CONF_AGENT_PROMPT,
                description={"suggested_value": suggested_prompt} if suggested_prompt else None
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
            vol.Required(
                CONF_AGENT_DESCRIPTION,
                description={"suggested_value": suggested_description} if suggested_description else None
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
            vol.Optional(
                CONF_AGENT_KEYWORDS,
                default=suggested_keywords
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
        })

        return self.async_show_form(
            step_id="add_agent",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_agent(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Redirect to select_custom_ai for editing."""
        return await self.async_step_select_custom_ai(user_input)

    async def async_step_remove_agent(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove an agent."""
        if user_input is not None:
            # Remove agent
            agent_index = int(user_input["agent_index"])
            removed_agent = self._agents.pop(agent_index)
            _LOGGER.debug(f"Removed agent: {removed_agent[CONF_AGENT_NAME]}")
            # Return to custom AI menu
            return await self.async_step_custom_ai()

        # Create selection options
        agent_choices = [
            {"label": agent[CONF_AGENT_NAME], "value": str(i)}
            for i, agent in enumerate(self._agents)
        ]

        schema = vol.Schema({
            vol.Required("agent_index"): SelectSelector(
                SelectSelectorConfig(
                    options=agent_choices,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="remove_agent",
            data_schema=schema,
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finish configuration with validation."""
        errors = {}

        # Validation checks
        if not self._prompt_generator_agent:
            errors["base"] = "missing_prompt_ai"
        if not self._agent:
            errors["base"] = "missing_router_ai"
        if not self._agents:
            errors["base"] = "no_custom_agents"

        # If validation fails, return to main menu with error
        if errors:
            return self.async_show_menu(
                step_id="user",
                menu_options={
                    "prompt_ai": "Configure Prompt AI",
                    "router_ai": "Configure Router AI",
                    "custom_ai": "Manage Custom AIs",
                    "finish": "Finish Setup"
                },
            )

        # All validation passed - create entry
        # Set defaults if needed
        if not self._prompt_generator_prompt:
            self._prompt_generator_prompt = DEFAULT_PROMPT_GENERATOR_PROMPT

        # Ensure router prompt exists
        if not self._agent_prompt:
            # Generate it
            if self._agents:
                from . import async_build_agent_prompt_with_ai
                try:
                    self._agent_prompt = await async_build_agent_prompt_with_ai(
                        self.hass,
                        self._agents,
                        self._prompt_generator_agent,
                        self._prompt_generator_prompt
                    )
                except Exception as e:
                    _LOGGER.warning(f"Failed to generate prompt with AI: {e}")
                    self._agent_prompt = build_agent_prompt(self._agents)

        return self.async_create_entry(
            title="Multi-Agent Router",
            data={
                CONF_AGENT: self._agent,
                CONF_AGENTS: self._agents,
                CONF_AGENT_PROMPT: self._agent_prompt,
                CONF_PROMPT_GENERATOR_AGENT: self._prompt_generator_agent,
                CONF_PROMPT_GENERATOR_PROMPT: self._prompt_generator_prompt,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return MultiAgentRouterOptionsFlow(config_entry)


class MultiAgentRouterOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Multi-Agent Router."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._agent: str | None = None
        self._agents: list[dict] = []
        self._agent_prompt: str | None = None
        self._prompt_generator_agent: str | None = None
        self._prompt_generator_prompt: str | None = None
        self._editing_index: int | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options - load config and show main menu."""
        # Initialize with current config
        self._agent = self.config_entry.data[CONF_AGENT]
        self._agents = list(self.config_entry.data[CONF_AGENTS])
        self._agent_prompt = self.config_entry.data.get(
            CONF_AGENT_PROMPT,
            build_agent_prompt(self._agents)  # Fallback for old configs
        )
        self._prompt_generator_agent = self.config_entry.data.get(
            CONF_PROMPT_GENERATOR_AGENT,
            DEFAULT_PROMPT_GENERATOR_AGENT
        )
        self._prompt_generator_prompt = self.config_entry.data.get(
            CONF_PROMPT_GENERATOR_PROMPT,
            DEFAULT_PROMPT_GENERATOR_PROMPT
        )

        # Show same menu as setup
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "prompt_ai": "Edit Prompt AI",
                "router_ai": "Edit Router AI",
                "custom_ai": "Manage Custom AIs",
                "finish": "Save Changes"
            },
        )

    async def _get_agent_prompt(self, agent_id: str) -> str | None:
        """Fetch the current prompt from a conversation agent's config.

        Args:
            agent_id: The conversation agent entity ID

        Returns:
            The agent's current prompt, or None if not found
        """
        from homeassistant.helpers import entity_registry as er
        from . import normalize_agent_name

        # 1. Try entity registry lookup
        entity_registry = er.async_get(self.hass)
        entity = entity_registry.async_get(agent_id)

        if entity and entity.config_entry_id:
            entry = self.hass.config_entries.async_get_entry(entity.config_entry_id)
            if entry and "prompt" in entry.options:
                return entry.options["prompt"]

        # 2. Fallback: Search OpenAI conversation subentries
        normalized_agent_name = normalize_agent_name(agent_id)

        for entry in self.hass.config_entries.async_entries("openai_conversation"):
            # Check options for prompt
            if "prompt" in entry.options:
                # Match by normalized title
                entry_name = normalize_agent_name(entry.title)
                if entry_name == normalized_agent_name:
                    return entry.options["prompt"]

            # Check subentries
            for subentry_obj in entry.subentries:
                subentry_title = getattr(subentry_obj, "title", "")
                normalized_subentry_title = normalize_agent_name(subentry_title)
                if normalized_agent_name == normalized_subentry_title:
                    subentry_data = getattr(subentry_obj, "data", {})
                    if "prompt" in subentry_data:
                        return subentry_data["prompt"]

        # 3. Return None if not found
        return None

    async def async_step_prompt_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure Prompt AI (reuse config flow logic)."""
        if user_input is not None:
            self._prompt_generator_agent = user_input[CONF_PROMPT_GENERATOR_AGENT]
            self._prompt_generator_prompt = user_input[CONF_PROMPT_GENERATOR_PROMPT]
            return await self.async_step_init()

        suggested_agent = self._prompt_generator_agent or DEFAULT_PROMPT_GENERATOR_AGENT
        suggested_prompt = self._prompt_generator_prompt or DEFAULT_PROMPT_GENERATOR_PROMPT

        if self._prompt_generator_agent and not self._prompt_generator_prompt:
            fetched_prompt = await self._get_agent_prompt(self._prompt_generator_agent)
            if fetched_prompt:
                suggested_prompt = fetched_prompt

        schema = vol.Schema({
            vol.Required(
                CONF_PROMPT_GENERATOR_AGENT,
                description={"suggested_value": suggested_agent}
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_PROMPT_GENERATOR_PROMPT,
                description={"suggested_value": suggested_prompt}
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="prompt_ai",
            data_schema=schema,
        )

    async def async_step_router_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure Router AI (reuse config flow logic)."""
        if user_input is not None:
            self._agent = user_input[CONF_AGENT]
            self._agent_prompt = user_input[CONF_AGENT_PROMPT]
            return await self.async_step_init()

        suggested_agent = self._agent or "homeassistant"
        suggested_prompt = self._agent_prompt

        if not suggested_prompt and self._agents:
            if self._prompt_generator_agent and self._prompt_generator_prompt:
                from . import async_build_agent_prompt_with_ai
                try:
                    suggested_prompt = await async_build_agent_prompt_with_ai(
                        self.hass,
                        self._agents,
                        self._prompt_generator_agent,
                        self._prompt_generator_prompt
                    )
                except Exception as e:
                    _LOGGER.warning(f"Failed to generate prompt with AI: {e}")
                    suggested_prompt = build_agent_prompt(self._agents)
            else:
                suggested_prompt = build_agent_prompt(self._agents)

        if self._agent and not self._agent_prompt:
            fetched_prompt = await self._get_agent_prompt(self._agent)
            if fetched_prompt:
                suggested_prompt = fetched_prompt

        schema = vol.Schema({
            vol.Required(
                CONF_AGENT,
                description={"suggested_value": suggested_agent}
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_AGENT_PROMPT,
                description={"suggested_value": suggested_prompt}
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="router_ai",
            data_schema=schema,
        )

    async def async_step_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Custom AI management menu (reuse config flow logic)."""
        agent_list = "None configured yet."
        if self._agents:
            agent_list = "\n".join([
                f"- {agent[CONF_AGENT_NAME]} ({agent[CONF_AGENT_ID]})"
                for agent in self._agents
            ])

        return self.async_show_menu(
            step_id="custom_ai",
            menu_options={
                "add_agent": "Add New Custom AI",
                "edit_agent": "Edit Existing Custom AI" if self._agents else None,
                "remove_agent": "Remove Custom AI" if self._agents else None,
                "init": "Back to Main Menu"
            },
            description_placeholders={"agents_list": agent_list}
        )

    async def async_step_select_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which custom AI to edit (reuse config flow logic)."""
        if user_input is not None:
            self._editing_index = int(user_input["agent_index"])
            return await self.async_step_add_agent()

        agent_choices = [
            {"label": agent[CONF_AGENT_NAME], "value": str(i)}
            for i, agent in enumerate(self._agents)
        ]

        schema = vol.Schema({
            vol.Required("agent_index"): SelectSelector(
                SelectSelectorConfig(
                    options=agent_choices,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="select_custom_ai",
            data_schema=schema,
        )

    async def async_step_add_agent(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit a specialized agent (reuse config flow logic)."""
        errors = {}
        is_editing = self._editing_index is not None

        if user_input is not None:
            agent_name = user_input[CONF_AGENT_NAME]
            if any(
                i != self._editing_index and agent[CONF_AGENT_NAME] == agent_name
                for i, agent in enumerate(self._agents)
            ):
                errors["base"] = "duplicate_name"
            else:
                agent_dict = {
                    CONF_AGENT_NAME: agent_name,
                    CONF_AGENT_ID: user_input[CONF_AGENT_ID],
                    CONF_AGENT_DESCRIPTION: user_input[CONF_AGENT_DESCRIPTION],
                    CONF_AGENT_KEYWORDS: user_input.get(CONF_AGENT_KEYWORDS, ""),
                    CONF_AGENT_PROMPT: user_input.get(CONF_AGENT_PROMPT, ""),
                }

                if is_editing:
                    self._agents[self._editing_index] = agent_dict
                    self._editing_index = None
                else:
                    self._agents.append(agent_dict)

                return await self.async_step_custom_ai()

        # Prepare form
        if is_editing:
            current_agent = self._agents[self._editing_index]
            suggested_name = current_agent[CONF_AGENT_NAME]
            suggested_agent_id = current_agent[CONF_AGENT_ID]
            suggested_description = current_agent[CONF_AGENT_DESCRIPTION]
            suggested_keywords = current_agent.get(CONF_AGENT_KEYWORDS, "")
            suggested_prompt = current_agent.get(CONF_AGENT_PROMPT, "")
        else:
            suggested_name = ""
            suggested_agent_id = "homeassistant"
            suggested_description = ""
            suggested_keywords = ""
            suggested_prompt = ""

        if suggested_agent_id and not suggested_prompt:
            fetched_prompt = await self._get_agent_prompt(suggested_agent_id)
            if fetched_prompt:
                suggested_prompt = fetched_prompt

        schema = vol.Schema({
            vol.Required(
                CONF_AGENT_NAME,
                description={"suggested_value": suggested_name} if suggested_name else None
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_AGENT_ID,
                description={"suggested_value": suggested_agent_id}
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Optional(
                CONF_AGENT_PROMPT,
                description={"suggested_value": suggested_prompt} if suggested_prompt else None
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
            vol.Required(
                CONF_AGENT_DESCRIPTION,
                description={"suggested_value": suggested_description} if suggested_description else None
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
            vol.Optional(
                CONF_AGENT_KEYWORDS,
                default=suggested_keywords
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
        })

        return self.async_show_form(
            step_id="add_agent",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_agent(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Redirect to select_custom_ai for editing."""
        return await self.async_step_select_custom_ai(user_input)

    async def async_step_remove_agent(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove an agent (reuse config flow logic)."""
        if user_input is not None:
            agent_index = int(user_input["agent_index"])
            removed_agent = self._agents.pop(agent_index)
            _LOGGER.debug(f"Removed agent: {removed_agent[CONF_AGENT_NAME]}")
            return await self.async_step_custom_ai()

        agent_choices = [
            {"label": agent[CONF_AGENT_NAME], "value": str(i)}
            for i, agent in enumerate(self._agents)
        ]

        schema = vol.Schema({
            vol.Required("agent_index"): SelectSelector(
                SelectSelectorConfig(
                    options=agent_choices,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="remove_agent",
            data_schema=schema,
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finish options flow and save all changes."""
        errors = {}

        # Validation
        if not self._prompt_generator_agent:
            errors["base"] = "missing_prompt_ai"
        if not self._agent:
            errors["base"] = "missing_router_ai"
        if not self._agents:
            errors["base"] = "no_custom_agents"

        if errors:
            return await self.async_step_init()

        # Ensure prompts exist
        if not self._prompt_generator_prompt:
            self._prompt_generator_prompt = DEFAULT_PROMPT_GENERATOR_PROMPT

        if not self._agent_prompt and self._agents:
            from . import async_build_agent_prompt_with_ai
            try:
                self._agent_prompt = await async_build_agent_prompt_with_ai(
                    self.hass,
                    self._agents,
                    self._prompt_generator_agent,
                    self._prompt_generator_prompt
                )
            except Exception as e:
                _LOGGER.warning(f"Failed to generate prompt with AI: {e}")
                self._agent_prompt = build_agent_prompt(self._agents)

        # Update config entry
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                CONF_AGENT: self._agent,
                CONF_AGENTS: self._agents,
                CONF_AGENT_PROMPT: self._agent_prompt,
                CONF_PROMPT_GENERATOR_AGENT: self._prompt_generator_agent,
                CONF_PROMPT_GENERATOR_PROMPT: self._prompt_generator_prompt,
            },
        )

        return self.async_create_entry(title="", data={})

    async def async_step_edit_prompt(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the agent prompt."""
        if user_input is not None:
            # Save the updated prompt (don't update entry yet)
            self._agent_prompt = user_input[CONF_AGENT_PROMPT]
            return await self.async_step_init()

        # Show current prompt for editing
        schema = vol.Schema({
            vol.Required(
                CONF_AGENT_PROMPT,
                default=self._agent_prompt
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="edit_prompt",
            data_schema=schema,
        )

    async def async_step_edit_prompt_generator(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the prompt generator configuration."""
        if user_input is not None:
            # Save the updated prompt generator configuration (don't update entry yet)
            self._prompt_generator_agent = user_input[CONF_PROMPT_GENERATOR_AGENT]
            self._prompt_generator_prompt = user_input[CONF_PROMPT_GENERATOR_PROMPT]
            return await self.async_step_init()

        # Show current prompt generator config for editing
        schema = vol.Schema({
            vol.Required(
                CONF_PROMPT_GENERATOR_AGENT,
                default=self._prompt_generator_agent
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_PROMPT_GENERATOR_PROMPT,
                default=self._prompt_generator_prompt
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="edit_prompt_generator",
            data_schema=schema,
            description_placeholders={
                "info": "Configure which agent generates router prompts and the prompt it uses. The {agent_json} placeholder will be replaced with your agent list."
            }
        )

    async def async_step_manage_agents(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage specialized agents."""
        # Build agent list for display
        agent_list = "None"
        if self._agents:
            agent_list = "\n".join([
                f"- {agent[CONF_AGENT_NAME]} ({agent[CONF_AGENT_ID]})"
                for agent in self._agents
            ])
            description = f"Currently configured agents:\n{agent_list}"
        else:
            description = "No agents configured yet."

        return self.async_show_menu(
            step_id="manage_agents",
            menu_options={
                "add_agent": "Add Agent",
                "edit_agent": "Edit Agent",
                "remove_agent": "Remove Agent",
                "finish": "Back to Options"
            },
            description_placeholders={"agents_list": agent_list}
        )

    async def async_step_add_agent(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a specialized agent."""
        errors = {}

        if user_input is not None:
            # Validate agent name is unique
            agent_name = user_input[CONF_AGENT_NAME]
            if any(agent[CONF_AGENT_NAME] == agent_name for agent in self._agents):
                errors["base"] = "duplicate_name"
            else:
                # Add agent to list
                self._agents.append({
                    CONF_AGENT_NAME: agent_name,
                    CONF_AGENT_ID: user_input[CONF_AGENT_ID],
                    CONF_AGENT_DESCRIPTION: user_input[CONF_AGENT_DESCRIPTION],
                    CONF_AGENT_KEYWORDS: user_input.get(CONF_AGENT_KEYWORDS, ""),
                })

                # Regenerate prompt with new agent
                self._agent_prompt = build_agent_prompt(self._agents)

                return await self.async_step_manage_agents()

        # Use ConversationAgentSelector for agent selection
        schema = vol.Schema({
            vol.Required(CONF_AGENT_NAME): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(CONF_AGENT_ID): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(CONF_AGENT_DESCRIPTION): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
            vol.Optional(CONF_AGENT_KEYWORDS, default=""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
        })

        return self.async_show_form(
            step_id="add_agent",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_agent(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select agent to edit."""
        if user_input is not None:
            self._editing_index = int(user_input["agent_index"])
            return await self.async_step_edit_agent_form()

        # Create selection options
        agent_choices = [
            {"label": agent[CONF_AGENT_NAME], "value": str(i)}
            for i, agent in enumerate(self._agents)
        ]

        schema = vol.Schema({
            vol.Required("agent_index"): SelectSelector(
                SelectSelectorConfig(
                    options=agent_choices,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="edit_agent",
            data_schema=schema,
        )

    async def async_step_edit_agent_form(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit agent form."""
        errors = {}

        if user_input is not None:
            # Validate agent name is unique (except for current agent)
            agent_name = user_input[CONF_AGENT_NAME]
            if any(
                i != self._editing_index and agent[CONF_AGENT_NAME] == agent_name
                for i, agent in enumerate(self._agents)
            ):
                errors["base"] = "duplicate_name"
            else:
                # Update agent
                self._agents[self._editing_index] = {
                    CONF_AGENT_NAME: agent_name,
                    CONF_AGENT_ID: user_input[CONF_AGENT_ID],
                    CONF_AGENT_DESCRIPTION: user_input[CONF_AGENT_DESCRIPTION],
                    CONF_AGENT_KEYWORDS: user_input.get(CONF_AGENT_KEYWORDS, ""),
                }

                # Regenerate prompt with updated agent
                self._agent_prompt = build_agent_prompt(self._agents)

                self._editing_index = None
                return await self.async_step_manage_agents()

        # Get current agent data
        current_agent = self._agents[self._editing_index]

        # Use ConversationAgentSelector for agent selection
        schema = vol.Schema({
            vol.Required(
                CONF_AGENT_NAME,
                default=current_agent[CONF_AGENT_NAME]
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_AGENT_ID,
                default=current_agent[CONF_AGENT_ID]
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_AGENT_DESCRIPTION,
                default=current_agent[CONF_AGENT_DESCRIPTION]
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
            vol.Optional(
                CONF_AGENT_KEYWORDS,
                default=current_agent.get(CONF_AGENT_KEYWORDS, "")
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
        })

        return self.async_show_form(
            step_id="edit_agent_form",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_remove_agent(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove an agent."""
        if user_input is not None:
            # Remove agent
            agent_index = int(user_input["agent_index"])
            self._agents.pop(agent_index)

            if not self._agents:
                return self.async_abort(reason="no_agents")

            # Regenerate prompt without removed agent
            self._agent_prompt = build_agent_prompt(self._agents)

            # Don't update entry here - will be saved when finishing
            return await self.async_step_manage_agents()

        # Create selection options
        agent_choices = [
            {"label": agent[CONF_AGENT_NAME], "value": str(i)}
            for i, agent in enumerate(self._agents)
        ]

        schema = vol.Schema({
            vol.Required("agent_index"): SelectSelector(
                SelectSelectorConfig(
                    options=agent_choices,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="remove_agent",
            data_schema=schema,
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finish options flow and save all changes."""
        # Update config entry with all accumulated changes
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                CONF_AGENT: self._agent,
                CONF_AGENTS: self._agents,
                CONF_AGENT_PROMPT: self._agent_prompt,
                CONF_PROMPT_GENERATOR_AGENT: self._prompt_generator_agent,
                CONF_PROMPT_GENERATOR_PROMPT: self._prompt_generator_prompt,
            },
        )

        # Complete options flow
        return self.async_create_entry(title="", data={})
