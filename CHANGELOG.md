# Changelog

All notable changes to the Multi-Agent Router integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
