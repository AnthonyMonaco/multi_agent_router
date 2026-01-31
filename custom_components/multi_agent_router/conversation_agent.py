"""Conversation agent for Multi-Agent Router."""
import logging
from typing import Any

from homeassistant.components import conversation
from homeassistant.components.conversation import AbstractConversationAgent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.util import ulid

from .const import (
    CONF_AGENT_DESCRIPTION,
    CONF_AGENT_ID,
    CONF_AGENT_NAME,
)

_LOGGER = logging.getLogger(__name__)


class MultiAgentRouter(AbstractConversationAgent):
    """Multi-agent router conversation agent."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        agent_id: str,
        agent_prompt: str,
        agents: list[dict],
    ) -> None:
        """Initialize router."""
        self.hass = hass
        self.entry = entry
        self.agent_id = agent_id
        self.agent_prompt = agent_prompt
        self.agents = {agent[CONF_AGENT_NAME]: agent for agent in agents}
        self.agent_names = [agent[CONF_AGENT_NAME] for agent in agents]

        # Metrics tracking
        self.metrics = {
            'direct_handling': 0,
            'routed': 0,
            'total_requests': 0,
        }

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return ["en"]

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process conversation input."""
        text = user_input.text.strip()
        language = user_input.language or "en"
        conversation_id = user_input.conversation_id or ulid.ulid_now()

        _LOGGER.info("🎤 MultiAgentRouter received: '%s' (lang=%s, conv_id=%s)", text, language, conversation_id)
        self.metrics['total_requests'] += 1

        # Step 1: Call the unified agent
        agent_response = await self._call_agent(text, language, conversation_id)

        # Step 2: Determine if it's a direct response or routing
        if self._is_routing_response(agent_response):
            # Extract agent name and route
            target_agent_name = self._extract_agent_name(agent_response)
            _LOGGER.info("🎯 Routing decision: '%s' (extracted from response)", target_agent_name)
            target_agent = self._match_agent(target_agent_name)

            if not target_agent:
                _LOGGER.warning(
                    "No matching agent found for '%s', using fallback agent: %s",
                    target_agent_name,
                    self.agent_names[0]
                )
                target_agent = self.agents[self.agent_names[0]]

            self.metrics['routed'] += 1
            result = await self._call_specialized_agent(target_agent, text, language, conversation_id)
            self._log_metrics()
            return result
        else:
            # Direct handling - return the response
            self.metrics['direct_handling'] += 1
            self._log_metrics()
            _LOGGER.warning("⚠️  Router handled request directly (NOT routing) - response: '%s'", agent_response)
            return self._create_response(agent_response, language, conversation_id)

    async def _call_agent(
        self, text: str, language: str, conversation_id: str
    ) -> str | None:
        """Call the unified agent with user text."""
        try:
            _LOGGER.info("📞 Calling router agent: %s", self.agent_id)
            response = await self.hass.services.async_call(
                "conversation",
                "process",
                {
                    "agent_id": self.agent_id,
                    "text": text,
                    "language": language,
                    "conversation_id": conversation_id,
                },
                blocking=True,
                return_response=True,
            )

            # Extract response text
            response_text = self._extract_speech_from_response(response)
            _LOGGER.info("📥 Router agent responded: '%s'", response_text)
            return response_text

        except Exception as e:
            _LOGGER.error("Agent failed: %s", e)
            return None

    def _is_routing_response(self, response: str | None) -> bool:
        """Check if response starts with 'ROUTE:'."""
        if response is None:
            return False
        return response.strip().upper().startswith("ROUTE:")

    def _extract_agent_name(self, response: str) -> str:
        """Extract agent name from 'ROUTE: AgentName' response."""
        # Remove "ROUTE:" prefix and clean up
        agent_name = response.strip()
        if agent_name.upper().startswith("ROUTE:"):
            agent_name = agent_name[6:].strip()  # Remove "ROUTE:" prefix
        return agent_name

    async def _call_specialized_agent(
        self, target_agent: dict[str, Any], text: str, language: str, conversation_id: str
    ) -> conversation.ConversationResult:
        """Call the target specialized agent."""
        _LOGGER.info(
            "Routing to agent '%s' (%s)",
            target_agent[CONF_AGENT_NAME],
            target_agent[CONF_AGENT_ID]
        )
        _LOGGER.info("📞 Calling specialized agent '%s' with input: '%s'", target_agent[CONF_AGENT_ID], text)

        try:
            target_response = await self.hass.services.async_call(
                "conversation",
                "process",
                {
                    "agent_id": target_agent[CONF_AGENT_ID],
                    "text": text,
                    "language": language,
                    "conversation_id": conversation_id,
                },
                blocking=True,
                return_response=True,
            )

            # Extract speech from response
            speech_text = self._extract_speech_from_response(target_response)

            if speech_text is None or speech_text == "":
                _LOGGER.warning("Target agent %s did not return a valid response - returning silent result", target_agent[CONF_AGENT_ID])
                # Return result with no speech
                response_obj = intent.IntentResponse(language=language)
                return conversation.ConversationResult(
                    response=response_obj,
                    conversation_id=conversation_id,
                )

            _LOGGER.info("📤 Specialized agent responded: '%s'", speech_text)

        except Exception as e:
            _LOGGER.error("Target agent %s failed: %s", target_agent[CONF_AGENT_ID], e)
            # Return result with no speech on error
            response_obj = intent.IntentResponse(language=language)
            return conversation.ConversationResult(
                response=response_obj,
                conversation_id=conversation_id,
            )

        # Return response with speech
        response_obj = intent.IntentResponse(language=language)
        response_obj.async_set_speech(speech_text)
        return conversation.ConversationResult(
            response=response_obj,
            conversation_id=conversation_id,
        )

    def _create_response(
        self, speech_text: str | None, language: str, conversation_id: str
    ) -> conversation.ConversationResult:
        """Create a conversation result from speech text."""
        response_obj = intent.IntentResponse(language=language)

        # Only set speech if we have valid text
        if speech_text and speech_text.strip():
            response_obj.async_set_speech(speech_text.strip())

        return conversation.ConversationResult(
            response=response_obj,
            conversation_id=conversation_id,
        )

    def _match_agent(self, classification: str) -> dict[str, Any] | None:
        """Match classification to an agent using fuzzy matching."""
        classification_lower = classification.lower()

        # Try exact match first
        for agent_name in self.agent_names:
            if agent_name.lower() == classification_lower:
                return self.agents[agent_name]

        # Try substring match
        for agent_name in self.agent_names:
            if agent_name.lower() in classification_lower:
                return self.agents[agent_name]

        # Try reverse substring match (classification in agent name)
        for agent_name in self.agent_names:
            if classification_lower in agent_name.lower():
                return self.agents[agent_name]

        # No match found
        return None

    def _extract_speech_from_response(self, response: dict[str, Any]) -> str | None:
        """
        Extract speech text from service response.

        Tries multiple extraction paths to handle different response structures.
        """
        # Log the response type and keys for debugging
        _LOGGER.debug("Response type: %s", type(response))
        _LOGGER.debug("Response top-level keys: %s", list(response.keys()) if isinstance(response, dict) else "Not a dict")

        # If response is a dict, log the structure
        if isinstance(response, dict):
            _LOGGER.debug("Response structure:\n%s", self._format_response_structure(response))

        # Try ConversationResult object response
        if hasattr(response, 'response') and hasattr(response.response, 'speech'):
            speech_obj = response.response.speech
            if hasattr(speech_obj, 'plain') and hasattr(speech_obj.plain, 'speech'):
                speech_text = speech_obj.plain.speech
                if speech_text and speech_text.strip():
                    _LOGGER.debug("Extracted from ConversationResult object")
                    return speech_text.strip()

        # Try direct IntentResponse extraction
        if hasattr(response, 'speech'):
            if isinstance(response.speech, str):
                if response.speech.strip():
                    _LOGGER.debug("Extracted from direct speech attribute")
                    return response.speech.strip()

        # Try the standard nested structure first
        if "response" in response:
            response_data = response["response"]
            if "speech" in response_data:
                speech_data = response_data["speech"]
                if "plain" in speech_data:
                    plain_speech = speech_data["plain"]
                    if "speech" in plain_speech:
                        speech_text = plain_speech["speech"]
                        if speech_text and speech_text.strip():
                            _LOGGER.debug("Extracted from response.speech.plain.speech")
                            return speech_text.strip()

        # Try alternative structure: response.speech directly
        if "response" in response and "speech" in response["response"]:
            speech_text = response["response"]["speech"]
            if isinstance(speech_text, str) and speech_text.strip():
                _LOGGER.debug("Extracted from response.speech")
                return speech_text.strip()

        # Try top-level speech field
        if "speech" in response:
            speech_text = response["speech"]
            if isinstance(speech_text, str) and speech_text.strip():
                _LOGGER.debug("Extracted from top-level speech")
                return speech_text.strip()

        # Try OpenAI conversation agent response structure
        # OpenAI agents may return: {"content": "response text"}
        if "content" in response:
            content = response["content"]
            if isinstance(content, str) and content.strip():
                _LOGGER.debug("Extracted from 'content' field")
                return content.strip()

        # Try nested content field
        if "response" in response and "content" in response["response"]:
            content = response["response"]["content"]
            if isinstance(content, str) and content.strip():
                _LOGGER.debug("Extracted from 'response.content' field")
                return content.strip()

        # Try message field (some agents use this)
        if "message" in response:
            message = response["message"]
            if isinstance(message, str) and message.strip():
                _LOGGER.debug("Extracted from 'message' field")
                return message.strip()

        # Try text field (some agents use this)
        if "text" in response:
            text = response["text"]
            if isinstance(text, str) and text.strip():
                _LOGGER.debug("Extracted from 'text' field")
                return text.strip()

        # Last resort: try to find any string value that looks like a response
        if isinstance(response, dict):
            for key, value in response.items():
                if isinstance(value, str) and len(value) > 10 and not key.startswith('_'):
                    _LOGGER.warning("Using fallback extraction from key '%s'", key)
                    return value.strip()
                # Check nested dicts
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        if isinstance(nested_value, str) and len(nested_value) > 10 and not nested_key.startswith('_'):
                            _LOGGER.warning("Using fallback extraction from nested key '%s.%s'", key, nested_key)
                            return nested_value.strip()

        # If we truly can't extract anything meaningful, return None
        _LOGGER.error("CRITICAL: Could not extract speech from response. Full response dump: %s", response)
        return None

    def _format_response_structure(self, obj, indent=0):
        """Format response structure for logging."""
        if isinstance(obj, dict):
            lines = []
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    lines.append("  " * indent + f"{key}: {type(value).__name__}")
                    lines.append(self._format_response_structure(value, indent + 1))
                else:
                    value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    lines.append("  " * indent + f"{key}: {value_str}")
            return "\n".join(lines)
        elif isinstance(obj, list):
            return "  " * indent + f"[{len(obj)} items]"
        return ""

    def _log_metrics(self):
        """Log routing metrics periodically."""
        if self.metrics['total_requests'] % 20 == 0:
            total = self.metrics['total_requests']
            direct = self.metrics['direct_handling']
            routed = self.metrics['routed']

            _LOGGER.info(
                "Router metrics: Total=%d, Direct=%d, Routed=%d",
                total, direct, routed
            )

            if total > 0:
                direct_rate = (direct / total) * 100
                _LOGGER.info("Direct handling rate: %.1f%%", direct_rate)
