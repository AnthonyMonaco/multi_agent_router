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

    VERSION = 3

    def __init__(self) -> None:
        """Initialize config flow."""
        self._router_agent: str | None = None
        self._agents: list[dict] = []
        self._generated_router_prompt: str | None = None
        self._prompt_generator_agent: str | None = None
        self._prompt_generator_prompt: str | None = None
        self._editing_custom_ai_index: int | None = None

    def _get_configuration_status(self) -> str:
        """Get current configuration status for display."""
        status_parts = []

        # Prompt AI status
        if self._prompt_generator_agent:
            status_parts.append("✓ Prompt AI configured")
        else:
            status_parts.append("✗ Prompt AI not configured")

        # Router AI status
        if self._router_agent:
            status_parts.append("✓ Router AI configured")
        else:
            status_parts.append("✗ Router AI not configured")

        # Custom AIs status
        if self._agents:
            agent_names = ", ".join([agent[CONF_AGENT_NAME] for agent in self._agents])
            status_parts.append(f"✓ Custom AIs ({len(self._agents)}): {agent_names}")
        else:
            status_parts.append("✗ No Custom AIs configured")

        return "\n".join(status_parts)

    def _can_submit(self) -> bool:
        """Check if all required configuration is complete."""
        return (
            self._prompt_generator_agent is not None
            and self._router_agent is not None
            and len(self._agents) > 0
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - summary page with menu options."""
        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # Build menu options dynamically
        menu_options = ["edit_prompt_ai", "edit_router_ai", "manage_custom_ais"]

        # Only show Submit if all required fields are configured
        if self._can_submit():
            menu_options.append("submit")

        return self.async_show_menu(
            step_id="user",
            menu_options=menu_options,
            description_placeholders={
                "status": self._get_configuration_status()
            }
        )


    async def _get_agent_prompt(self, agent_id: str) -> str:
        """Helper to fetch current prompt from an agent."""
        try:
            from homeassistant.helpers import entity_registry as er

            entity_registry = er.async_get(self.hass)
            entity_entry = entity_registry.async_get(agent_id)

            if entity_entry and entity_entry.config_entry_id:
                config_entry = self.hass.config_entries.async_get_entry(
                    entity_entry.config_entry_id
                )
                if config_entry and config_entry.domain in [
                    "openai_conversation",
                    "extended_openai_conversation",
                ]:
                    return config_entry.options.get("prompt", "")
        except Exception as e:
            _LOGGER.debug("Could not fetch agent prompt: %s", e)

        return ""

    async def async_step_edit_prompt_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit Prompt AI configuration."""
        if user_input is not None:
            self._prompt_generator_agent = user_input[CONF_PROMPT_GENERATOR_AGENT]
            self._prompt_generator_prompt = user_input[CONF_PROMPT_GENERATOR_PROMPT]
            return await self.async_step_user()

        # Pre-fill with current values or defaults
        current_agent = self._prompt_generator_agent or DEFAULT_PROMPT_GENERATOR_AGENT
        current_prompt = self._prompt_generator_prompt

        # If no prompt set, try to fetch from agent
        if not current_prompt:
            fetched_prompt = await self._get_agent_prompt(current_agent)
            current_prompt = fetched_prompt or DEFAULT_PROMPT_GENERATOR_PROMPT

        schema = vol.Schema({
            vol.Required(
                CONF_PROMPT_GENERATOR_AGENT,
                default=current_agent
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_PROMPT_GENERATOR_PROMPT,
                default=current_prompt
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="edit_prompt_ai",
            data_schema=schema,
        )

    async def async_step_edit_router_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit Router AI configuration (agent only, no prompt)."""
        if user_input is not None:
            self._router_agent = user_input[CONF_AGENT]
            return await self.async_step_user()

        # Pre-fill with current value or default
        current_agent = self._router_agent or "homeassistant"

        schema = vol.Schema({
            vol.Required(
                CONF_AGENT,
                default=current_agent
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
        })

        return self.async_show_form(
            step_id="edit_router_ai",
            data_schema=schema,
        )

    async def async_step_manage_custom_ais(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Custom AIs menu."""
        # Build agent list for display
        if self._agents:
            agent_list = "\n".join([
                f"- {agent[CONF_AGENT_NAME]} ({agent[CONF_AGENT_ID]})"
                for agent in self._agents
            ])
        else:
            agent_list = "No Custom AIs configured yet."

        # Build menu options dynamically
        menu_options = ["add_custom_ai"]
        if self._agents:
            menu_options.extend(["edit_custom_ai", "delete_custom_ai"])
        menu_options.append("back_to_summary")

        return self.async_show_menu(
            step_id="manage_custom_ais",
            menu_options=menu_options,
            description_placeholders={"agents_list": agent_list}
        )

    async def async_step_add_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new Custom AI."""
        return await self.async_step_edit_custom_ai_form(user_input, is_add=True)

    async def async_step_select_edit_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select Custom AI to edit."""
        if user_input is not None:
            self._editing_custom_ai_index = int(user_input["agent_index"])
            return await self.async_step_edit_custom_ai_form(None, is_add=False)

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
            step_id="select_edit_custom_ai",
            data_schema=schema,
        )

    async def async_step_edit_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Redirect to select screen for editing."""
        return await self.async_step_select_edit_custom_ai(user_input)

    async def async_step_edit_custom_ai_form(
        self, user_input: dict[str, Any] | None = None, is_add: bool = True
    ) -> FlowResult:
        """Unified form for adding/editing Custom AI."""
        errors = {}

        if user_input is not None:
            # Validate agent name is unique (except when editing self)
            agent_name = user_input[CONF_AGENT_NAME]
            is_duplicate = any(
                i != self._editing_custom_ai_index and agent[CONF_AGENT_NAME] == agent_name
                for i, agent in enumerate(self._agents)
            )

            if is_duplicate:
                errors["base"] = "duplicate_name"
            else:
                # Build agent data
                agent_data = {
                    CONF_AGENT_NAME: agent_name,
                    CONF_AGENT_ID: user_input[CONF_AGENT_ID],
                    CONF_AGENT_DESCRIPTION: user_input[CONF_AGENT_DESCRIPTION],
                    CONF_AGENT_KEYWORDS: user_input.get(CONF_AGENT_KEYWORDS, ""),
                    CONF_AGENT_PROMPT: user_input.get(CONF_AGENT_PROMPT, ""),
                }

                if is_add:
                    # Add new agent
                    self._agents.append(agent_data)
                    _LOGGER.debug(f"Added custom AI: {agent_name}")
                else:
                    # Update existing agent
                    self._agents[self._editing_custom_ai_index] = agent_data
                    _LOGGER.debug(f"Updated custom AI: {agent_name}")
                    self._editing_custom_ai_index = None

                return await self.async_step_manage_custom_ais()

        # Prepare form fields
        if is_add:
            # Defaults for new agent
            default_name = ""
            default_agent_id = "homeassistant"
            default_description = ""
            default_keywords = ""
            default_prompt = ""
        else:
            # Pre-fill for editing
            current_agent = self._agents[self._editing_custom_ai_index]
            default_name = current_agent[CONF_AGENT_NAME]
            default_agent_id = current_agent[CONF_AGENT_ID]
            default_description = current_agent[CONF_AGENT_DESCRIPTION]
            default_keywords = current_agent.get(CONF_AGENT_KEYWORDS, "")
            default_prompt = current_agent.get(CONF_AGENT_PROMPT, "")

            # Auto-fetch prompt if not set
            if not default_prompt:
                default_prompt = await self._get_agent_prompt(default_agent_id)

        schema = vol.Schema({
            vol.Required(CONF_AGENT_NAME, default=default_name): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(CONF_AGENT_ID, default=default_agent_id): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(CONF_AGENT_DESCRIPTION, default=default_description): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
            vol.Optional(CONF_AGENT_KEYWORDS, default=default_keywords): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_AGENT_PROMPT, default=default_prompt): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        step_id = "add_custom_ai" if is_add else "edit_custom_ai_form"

        return self.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_select_delete_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select Custom AI to delete."""
        if user_input is not None:
            # Delete the selected agent
            agent_index = int(user_input["agent_index"])
            deleted_agent = self._agents.pop(agent_index)
            _LOGGER.debug(f"Deleted custom AI: {deleted_agent[CONF_AGENT_NAME]}")
            return await self.async_step_manage_custom_ais()

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
            step_id="select_delete_custom_ai",
            data_schema=schema,
        )

    async def async_step_delete_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Redirect to select screen for deletion."""
        return await self.async_step_select_delete_custom_ai(user_input)

    async def async_step_back_to_summary(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Return to summary page."""
        return await self.async_step_user()

    async def async_step_submit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Submit configuration and generate router prompt."""
        # Validate all required fields
        if not self._prompt_generator_agent:
            return self.async_abort(reason="missing_prompt_ai")
        if not self._router_agent:
            return self.async_abort(reason="missing_router_ai")
        if not self._agents:
            return self.async_abort(reason="no_custom_agents")

        # Generate router prompt using Prompt AI
        try:
            from . import async_build_agent_prompt_with_ai

            _LOGGER.info("Generating router prompt with Prompt AI...")
            self._generated_router_prompt = await async_build_agent_prompt_with_ai(
                self.hass,
                self._agents,
                self._prompt_generator_agent,
                self._prompt_generator_prompt,
            )
        except Exception as e:
            _LOGGER.warning("AI generation failed, using static fallback: %s", e)
            self._generated_router_prompt = build_agent_prompt(self._agents)

        # Go to review prompt page
        return await self.async_step_review_prompt()

    async def async_step_review_prompt(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Review and edit AI-generated router prompt before submission."""
        if user_input is not None:
            # Save the final prompt and create entry
            final_prompt = user_input[CONF_AGENT_PROMPT]

            if not final_prompt or not final_prompt.strip():
                # Should not happen due to Required field, but defensive check
                return self.async_show_form(
                    step_id="review_prompt",
                    data_schema=vol.Schema({
                        vol.Required(
                            CONF_AGENT_PROMPT,
                            default=self._generated_router_prompt
                        ): TextSelector(
                            TextSelectorConfig(
                                type=TextSelectorType.TEXT,
                                multiline=True,
                            )
                        ),
                    }),
                    errors={"base": "empty_prompt"}
                )

            return self.async_create_entry(
                title="Multi-Agent Router",
                data={
                    CONF_AGENT: self._router_agent,
                    CONF_AGENTS: self._agents,
                    CONF_AGENT_PROMPT: final_prompt,
                    CONF_PROMPT_GENERATOR_AGENT: self._prompt_generator_agent,
                    CONF_PROMPT_GENERATOR_PROMPT: self._prompt_generator_prompt,
                },
            )

        # Show AI-generated prompt for review
        schema = vol.Schema({
            vol.Required(
                CONF_AGENT_PROMPT,
                default=self._generated_router_prompt
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="review_prompt",
            data_schema=schema,
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
        self._router_agent: str | None = None
        self._agents: list[dict] = []
        self._generated_router_prompt: str | None = None
        self._prompt_generator_agent: str | None = None
        self._prompt_generator_prompt: str | None = None
        self._editing_custom_ai_index: int | None = None

    def _get_configuration_status(self) -> str:
        """Get current configuration status for display."""
        status_parts = []

        # Prompt AI status
        if self._prompt_generator_agent:
            status_parts.append(f"✓ Prompt AI: {self._prompt_generator_agent}")
        else:
            status_parts.append("✗ Prompt AI not configured")

        # Router AI status
        if self._router_agent:
            status_parts.append(f"✓ Router AI: {self._router_agent}")
        else:
            status_parts.append("✗ Router AI not configured")

        # Custom AIs status
        if self._agents:
            agent_names = ", ".join([agent[CONF_AGENT_NAME] for agent in self._agents])
            status_parts.append(f"✓ Custom AIs ({len(self._agents)}): {agent_names}")
        else:
            status_parts.append("✗ No Custom AIs configured")

        return "\n".join(status_parts)

    def _can_submit(self) -> bool:
        """Check if all required configuration is complete."""
        return (
            self._prompt_generator_agent is not None
            and self._router_agent is not None
            and len(self._agents) > 0
        )

    async def _get_agent_prompt(self, agent_id: str) -> str:
        """Helper to fetch current prompt from an agent."""
        try:
            from homeassistant.helpers import entity_registry as er

            entity_registry = er.async_get(self.hass)
            entity_entry = entity_registry.async_get(agent_id)

            if entity_entry and entity_entry.config_entry_id:
                config_entry = self.hass.config_entries.async_get_entry(
                    entity_entry.config_entry_id
                )
                if config_entry and config_entry.domain in [
                    "openai_conversation",
                    "extended_openai_conversation",
                ]:
                    return config_entry.options.get("prompt", "")
        except Exception as e:
            _LOGGER.debug("Could not fetch agent prompt: %s", e)

        return ""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options - summary page with menu."""
        # Initialize with current config
        self._router_agent = self.config_entry.data[CONF_AGENT]
        self._agents = list(self.config_entry.data[CONF_AGENTS])
        self._generated_router_prompt = self.config_entry.data.get(
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

        # Build menu options dynamically
        menu_options = ["edit_prompt_ai", "edit_router_ai", "manage_custom_ais"]

        # Only show Submit if all required fields are configured
        if self._can_submit():
            menu_options.append("submit")

        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options,
            description_placeholders={
                "status": self._get_configuration_status()
            }
        )

    async def async_step_edit_prompt_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit Prompt AI configuration."""
        if user_input is not None:
            self._prompt_generator_agent = user_input[CONF_PROMPT_GENERATOR_AGENT]
            self._prompt_generator_prompt = user_input[CONF_PROMPT_GENERATOR_PROMPT]
            return await self.async_step_init()

        # Pre-fill with current values
        current_prompt = self._prompt_generator_prompt

        # If no prompt set, try to fetch from agent
        if not current_prompt:
            current_prompt = await self._get_agent_prompt(self._prompt_generator_agent)

        schema = vol.Schema({
            vol.Required(
                CONF_PROMPT_GENERATOR_AGENT,
                default=self._prompt_generator_agent
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_PROMPT_GENERATOR_PROMPT,
                default=current_prompt
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="edit_prompt_ai",
            data_schema=schema,
        )

    async def async_step_edit_router_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit Router AI configuration (agent only, no prompt)."""
        if user_input is not None:
            self._router_agent = user_input[CONF_AGENT]
            return await self.async_step_init()

        schema = vol.Schema({
            vol.Required(
                CONF_AGENT,
                default=self._router_agent
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
        })

        return self.async_show_form(
            step_id="edit_router_ai",
            data_schema=schema,
        )

    async def async_step_manage_custom_ais(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Custom AIs menu."""
        # Build agent list for display
        if self._agents:
            agent_list = "\n".join([
                f"- {agent[CONF_AGENT_NAME]} ({agent[CONF_AGENT_ID]})"
                for agent in self._agents
            ])
        else:
            agent_list = "No Custom AIs configured yet."

        # Build menu options dynamically
        menu_options = ["add_custom_ai"]
        if self._agents:
            menu_options.extend(["edit_custom_ai", "delete_custom_ai"])
        menu_options.append("back_to_summary")

        return self.async_show_menu(
            step_id="manage_custom_ais",
            menu_options=menu_options,
            description_placeholders={"agents_list": agent_list}
        )

    async def async_step_add_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new Custom AI."""
        return await self.async_step_edit_custom_ai_form(user_input, is_add=True)

    async def async_step_select_edit_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select Custom AI to edit."""
        if user_input is not None:
            self._editing_custom_ai_index = int(user_input["agent_index"])
            return await self.async_step_edit_custom_ai_form(None, is_add=False)

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
            step_id="select_edit_custom_ai",
            data_schema=schema,
        )

    async def async_step_edit_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Redirect to select screen for editing."""
        return await self.async_step_select_edit_custom_ai(user_input)

    async def async_step_edit_custom_ai_form(
        self, user_input: dict[str, Any] | None = None, is_add: bool = True
    ) -> FlowResult:
        """Unified form for adding/editing Custom AI."""
        errors = {}

        if user_input is not None:
            # Validate agent name is unique (except when editing self)
            agent_name = user_input[CONF_AGENT_NAME]
            is_duplicate = any(
                i != self._editing_custom_ai_index and agent[CONF_AGENT_NAME] == agent_name
                for i, agent in enumerate(self._agents)
            )

            if is_duplicate:
                errors["base"] = "duplicate_name"
            else:
                # Build agent data
                agent_data = {
                    CONF_AGENT_NAME: agent_name,
                    CONF_AGENT_ID: user_input[CONF_AGENT_ID],
                    CONF_AGENT_DESCRIPTION: user_input[CONF_AGENT_DESCRIPTION],
                    CONF_AGENT_KEYWORDS: user_input.get(CONF_AGENT_KEYWORDS, ""),
                    CONF_AGENT_PROMPT: user_input.get(CONF_AGENT_PROMPT, ""),
                }

                if is_add:
                    # Add new agent
                    self._agents.append(agent_data)
                    _LOGGER.debug(f"Added custom AI: {agent_name}")
                else:
                    # Update existing agent
                    self._agents[self._editing_custom_ai_index] = agent_data
                    _LOGGER.debug(f"Updated custom AI: {agent_name}")
                    self._editing_custom_ai_index = None

                return await self.async_step_manage_custom_ais()

        # Prepare form fields
        if is_add:
            # Defaults for new agent
            default_name = ""
            default_agent_id = "homeassistant"
            default_description = ""
            default_keywords = ""
            default_prompt = ""
        else:
            # Pre-fill for editing
            current_agent = self._agents[self._editing_custom_ai_index]
            default_name = current_agent[CONF_AGENT_NAME]
            default_agent_id = current_agent[CONF_AGENT_ID]
            default_description = current_agent[CONF_AGENT_DESCRIPTION]
            default_keywords = current_agent.get(CONF_AGENT_KEYWORDS, "")
            default_prompt = current_agent.get(CONF_AGENT_PROMPT, "")

            # Auto-fetch prompt if not set
            if not default_prompt:
                default_prompt = await self._get_agent_prompt(default_agent_id)

        schema = vol.Schema({
            vol.Required(CONF_AGENT_NAME, default=default_name): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(CONF_AGENT_ID, default=default_agent_id): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(CONF_AGENT_DESCRIPTION, default=default_description): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
            vol.Optional(CONF_AGENT_KEYWORDS, default=default_keywords): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_AGENT_PROMPT, default=default_prompt): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        step_id = "add_custom_ai" if is_add else "edit_custom_ai_form"

        return self.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_select_delete_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select Custom AI to delete."""
        if user_input is not None:
            # Delete the selected agent
            agent_index = int(user_input["agent_index"])
            deleted_agent = self._agents.pop(agent_index)
            _LOGGER.debug(f"Deleted custom AI: {deleted_agent[CONF_AGENT_NAME]}")
            return await self.async_step_manage_custom_ais()

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
            step_id="select_delete_custom_ai",
            data_schema=schema,
        )

    async def async_step_delete_custom_ai(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Redirect to select screen for deletion."""
        return await self.async_step_select_delete_custom_ai(user_input)

    async def async_step_back_to_summary(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Return to summary page."""
        return await self.async_step_init()

    async def async_step_submit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Submit configuration and generate router prompt."""
        # Validate all required fields
        if not self._prompt_generator_agent:
            return self.async_abort(reason="missing_prompt_ai")
        if not self._router_agent:
            return self.async_abort(reason="missing_router_ai")
        if not self._agents:
            return self.async_abort(reason="no_custom_agents")

        # Generate router prompt using Prompt AI
        try:
            from . import async_build_agent_prompt_with_ai

            _LOGGER.info("Regenerating router prompt with Prompt AI...")
            self._generated_router_prompt = await async_build_agent_prompt_with_ai(
                self.hass,
                self._agents,
                self._prompt_generator_agent,
                self._prompt_generator_prompt,
            )
        except Exception as e:
            _LOGGER.warning("AI generation failed, using static fallback: %s", e)
            self._generated_router_prompt = build_agent_prompt(self._agents)

        # Go to review prompt page
        return await self.async_step_review_prompt()

    async def async_step_review_prompt(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Review and edit AI-generated router prompt before submission."""
        if user_input is not None:
            # Save the final prompt and update entry
            final_prompt = user_input[CONF_AGENT_PROMPT]

            if not final_prompt or not final_prompt.strip():
                # Should not happen due to Required field, but defensive check
                return self.async_show_form(
                    step_id="review_prompt",
                    data_schema=vol.Schema({
                        vol.Required(
                            CONF_AGENT_PROMPT,
                            default=self._generated_router_prompt
                        ): TextSelector(
                            TextSelectorConfig(
                                type=TextSelectorType.TEXT,
                                multiline=True,
                            )
                        ),
                    }),
                    errors={"base": "empty_prompt"}
                )

            # Update config entry with all accumulated changes
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    CONF_AGENT: self._router_agent,
                    CONF_AGENTS: self._agents,
                    CONF_AGENT_PROMPT: final_prompt,
                    CONF_PROMPT_GENERATOR_AGENT: self._prompt_generator_agent,
                    CONF_PROMPT_GENERATOR_PROMPT: self._prompt_generator_prompt,
                },
            )

            # Complete options flow
            return self.async_create_entry(title="", data={})

        # Show AI-generated prompt for review
        schema = vol.Schema({
            vol.Required(
                CONF_AGENT_PROMPT,
                default=self._generated_router_prompt
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="review_prompt",
            data_schema=schema,
        )
