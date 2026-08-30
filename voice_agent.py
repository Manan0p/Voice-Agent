"""Convenience script to run the real-time live Voice Agent with microphone and speaker."""

import asyncio
import sys

from apps.agent.voice.runner import LiveVoiceAgentRunner
from packages.shared.config import get_settings
from packages.shared.logging import setup_logging


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    caller_name = "User"
    if len(sys.argv) > 1:
        caller_name = sys.argv[1]

    runner = LiveVoiceAgentRunner(caller_name=caller_name)
    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
