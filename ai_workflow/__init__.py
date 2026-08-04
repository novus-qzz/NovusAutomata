"""NovusAutomata - AI-powered Git workflow automation.

Provides a modular CLI toolkit that automates code review, issue triage,
auto-fixing, changelog generation, and more via AI providers.
"""

from ai_workflow.config import Config, load_config

__all__ = ["Config", "load_config"]
__version__ = "0.2.0"
