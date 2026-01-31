# Changelog

All notable changes to the Multi-Agent Router integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-01-31

### Added
- **Configurable Prompt Generator Agent**: You can now select which conversation agent to use for generating router prompts through the UI
  - Previously hardcoded to `conversation.jarvis_prompt_generator`
  - Now configurable during initial setup or via options flow
  - Added `CONF_PROMPT_GENERATOR_AGENT` configuration key
  - Defaults to `conversation.jarvis_prompt_generator` for backward compatibility

- **Configurable Prompt Generator Prompt**: You can now customize the prompt template sent to the prompt generator agent
  - Added `CONF_PROMPT_GENERATOR_PROMPT` configuration key
  - Template uses `{agent_json}` placeholder that gets replaced with agent configuration JSON
  - Includes comprehensive default prompt with best practices for router prompt generation
  - Editable through UI during setup or via options menu

- **New UI Flows**:
  - Added "Configure Prompt Generator" step during initial setup
  - Added "Edit Prompt Generator" option in the configuration options menu
  - Both flows allow selecting the agent and editing the prompt template

- **Default Prompt Template**: Comprehensive sample prompt that demonstrates best practices:
  - Requires ONLY "ROUTE: [Agent Name]" format responses
  - Requests 5-8 concrete examples with actual agent names
  - Emphasizes using real agent names instead of placeholders
  - Instructs the generator to create explicit routing rules
  - Ensures the router never attempts to answer questions directly

### Changed
- `async_build_agent_prompt_with_ai()` now accepts optional `prompt_generator_agent` and `prompt_generator_prompt` parameters
- `regenerate_prompt` service now uses the configured prompt generator settings instead of hardcoded values
- Initial setup flow now includes prompt generator configuration as an optional step
- Configuration entry data now includes prompt generator agent and prompt settings

### Fixed
- Improved flexibility in prompt generation by removing hardcoded prompt generator dependency

## [1.0.0] - 2026-01-28

### Added
- Initial release of Multi-Agent Router integration
- Dynamic router prompt generation based on configured agents
- Config flow for easy setup via UI
- Support for multiple specialized conversation agents
- Intelligent routing using LLM-based classification
- Fallback behavior when routing fails
- Options flow for managing agents after initial setup
- Comprehensive debug logging
- Fuzzy matching for agent name classification
- Automatic reload when configuration changes

### Features
- **Router Agent Selection**: Choose any conversation agent to act as router
- **Specialized Agent Management**: Add, edit, and remove agents via UI
- **Dynamic Prompt Building**: Automatically generates routing instructions
- **Graceful Fallback**: Falls back to first agent on routing failures
- **Voice Pipeline Integration**: Works with Home Assistant voice assistants
- **Real-time Updates**: Configuration changes take effect immediately

### Documentation
- README.md with comprehensive usage guide
- INSTALL.md with step-by-step installation instructions
- TESTING.md with complete testing checklist
- Example configurations for voice pipeline integration
- Troubleshooting guide and tips

### Technical Details
- Implements AbstractConversationAgent interface
- Uses conversation.process service for agent communication
- Supports config entry reload without restart
- Single instance enforcement
- Input validation for agent configuration

## [Unreleased]

### Planned Features
- Advanced matching using ML embeddings
- Router response caching for similar queries
- Agent usage statistics and analytics
- Web UI for prompt preview
- Import/export agent configurations
- Support for agent descriptions with structured examples
- Multi-language support beyond English
- Performance optimizations for large agent lists

### Known Limitations
- Requires two API calls per request (router + specialized agent)
- Router must return agent name in a parseable format
- English language only in initial release
- Single router instance per Home Assistant installation
- Router prompt is prepended to each request (not stored in agent config)

## Migration Guide

### From Manual Routing Scripts
If you were previously using automations or scripts to route conversation requests:

1. Install Multi-Agent Router integration
2. Configure your existing agents as specialized agents
3. Create or designate a router agent
4. Update your voice pipeline to use Multi-Agent Router
5. Remove old routing automations

### Future Version Migrations
Breaking changes and migration steps will be documented here for future releases.

---

## Version History

- **1.0.0** (2026-01-28) - Initial release
