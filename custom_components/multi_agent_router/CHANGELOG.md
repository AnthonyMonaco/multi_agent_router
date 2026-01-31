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

## [1.2.0] - (Previous Release)

### Notes
- Version 1.2.0 and earlier changes not documented in this changelog
- Refer to git history or release notes for previous changes
