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

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._agent: str | None = None
        self._agents: list[dict] = []
        self._agent_prompt: str | None = None
        self._prompt_generator_agent: str | None = None
        self._prompt_generator_prompt: str | None = None
        self._editing_index: int | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - collect router agent and prompt generator config."""
        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            self._agent = user_input[CONF_AGENT]
            self._prompt_generator_agent = user_input[CONF_PROMPT_GENERATOR_AGENT]
            self._prompt_generator_prompt = user_input[CONF_PROMPT_GENERATOR_PROMPT]
            _LOGGER.debug(f"Agent selected: {self._agent}")
            _LOGGER.debug(f"Prompt generator configured: {self._prompt_generator_agent}")
            # Go directly to agent management
            return await self.async_step_add_agent()

        # Use ConversationAgentSelector for agent selection
        schema = vol.Schema({
            vol.Required(
                CONF_AGENT,
                description={"suggested_value": "homeassistant"}
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_PROMPT_GENERATOR_AGENT,
                description={"suggested_value": DEFAULT_PROMPT_GENERATOR_AGENT}
            ): ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            ),
            vol.Required(
                CONF_PROMPT_GENERATOR_PROMPT,
                description={"suggested_value": DEFAULT_PROMPT_GENERATOR_PROMPT}
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "info": "Configure the router agent and prompt generator. The router classifies requests, and the prompt generator can auto-create routing prompts."
            }
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
                _LOGGER.debug(f"Added agent: {agent_name} -> {user_input[CONF_AGENT_ID]}")
                # Ask if they want to add another
                return await self.async_step_add_another()

        # Use ConversationAgentSelector for agent selection
        schema = vol.Schema({
            vol.Required(CONF_AGENT_NAME): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_AGENT_ID,
                description={"suggested_value": "homeassistant"}
            ): ConversationAgentSelector(
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

    async def async_step_add_another(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask if user wants to add another agent."""
        if user_input is not None:
            if user_input.get("add_another"):
                return await self.async_step_add_agent()
            else:
                # Done! Go to prompt review
                return await self.async_step_finish()

        # Show current agents
        agent_list = "\n".join([
            f"- {agent[CONF_AGENT_NAME]} ({agent[CONF_AGENT_ID]})"
            for agent in self._agents
        ])

        if not self._agents:
            description = "No agents added yet. You need at least one agent."
            default_add_another = True
        else:
            description = f"Currently configured agents:\n{agent_list}\n\nAdd another agent or continue to finish setup?"
            default_add_another = False

        return self.async_show_form(
            step_id="add_another",
            data_schema=vol.Schema({
                vol.Required("add_another", default=default_add_another): bool,
            }),
            description_placeholders={"agents": agent_list, "description": description}
        )


    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finish configuration and set router prompt."""
        if not self._agents:
            return self.async_abort(reason="no_agents")

        if user_input is not None:
            # Save the prompt and create entry
            self._agent_prompt = user_input[CONF_AGENT_PROMPT]

            # Set defaults for prompt generator if not configured
            if not self._prompt_generator_agent:
                self._prompt_generator_agent = DEFAULT_PROMPT_GENERATOR_AGENT
            if not self._prompt_generator_prompt:
                self._prompt_generator_prompt = DEFAULT_PROMPT_GENERATOR_PROMPT

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

        # Generate default prompt based on configured agents
        default_prompt = build_agent_prompt(self._agents)

        # Show prompt field for review/editing
        schema = vol.Schema({
            vol.Required(
                CONF_AGENT_PROMPT,
                description={"suggested_value": default_prompt}
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="finish",
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
        self._agent: str | None = None
        self._agents: list[dict] = []
        self._agent_prompt: str | None = None
        self._prompt_generator_agent: str | None = None
        self._prompt_generator_prompt: str | None = None
        self._editing_index: int | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
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

        return self.async_show_menu(
            step_id="init",
            menu_options={
                "edit_prompt": "Edit Router Prompt",
                "edit_prompt_generator": "Edit Prompt Generator",
                "manage_agents": "Manage Agents",
                "finish": "Save & Exit"
            },
        )

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
