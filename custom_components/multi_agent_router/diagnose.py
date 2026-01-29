"""Diagnostic script for Multi-Agent Router conversation agent detection."""
import asyncio
import sys
import logging

# Add Home Assistant to path
sys.path.insert(0, '/usr/src/homeassistant')

logging.basicConfig(level=logging.DEBUG)

async def diagnose():
    """Run diagnostics."""
    try:
        # Try to import Home Assistant components
        from homeassistant.core import HomeAssistant
        from homeassistant.components import conversation
        from homeassistant.helpers import selector

        print("✓ Home Assistant imports successful")

        # Create a minimal Home Assistant instance
        hass = HomeAssistant('/config')
        await hass.async_start()

        print("\n=== Checking Conversation Component ===")

        # Check if conversation component is loaded
        if 'conversation' in hass.config.components:
            print("✓ Conversation component is loaded")
        else:
            print("✗ Conversation component is NOT loaded")

        # Try to get conversation agents
        try:
            agents = conversation.async_get_conversation_agents(hass)
            print(f"\nFound {len(agents)} conversation agents:")
            for agent_id, agent_info in agents.items():
                print(f"  - {agent_id}: {agent_info}")
        except Exception as e:
            print(f"✗ Error getting conversation agents: {e}")

        # Check selector
        print("\n=== Checking ConversationAgentSelector ===")
        try:
            from homeassistant.helpers.selector import (
                ConversationAgentSelector,
                ConversationAgentSelectorConfig,
            )
            selector_obj = ConversationAgentSelector(
                ConversationAgentSelectorConfig(language="en")
            )
            print(f"✓ Selector created: {selector_obj}")
            print(f"  Config: {selector_obj.config}")
        except Exception as e:
            print(f"✗ Error creating selector: {e}")

        await hass.async_stop()

    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("\nThis script must be run from within Home Assistant's Python environment")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose())
