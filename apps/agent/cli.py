import asyncio
import sys

from apps.agent.context.manager import ContextManager
from apps.agent.engine import AgentEngine
from apps.agent.llm.factory import get_llm_provider
from packages.shared.config import get_settings
from packages.shared.logging import setup_logging


async def main() -> None:
    """Run interactive text conversation session with the AI Call Agent."""
    settings = get_settings()
    setup_logging(settings.log_level)

    print("\n" + "=" * 60)
    print("🤖 PERSONAL AI CALL AGENT — TEXT CLI (Phase 1)")
    print(
        f"📡 LLM Provider: {settings.llm_provider.upper()} ({settings.gemini_model if settings.llm_provider == 'gemini' else ''})"
    )
    print("=" * 60)
    print("Commands:")
    print("  'exit' / 'quit' : End the simulated call")
    print("  'context'       : Set caller name/context")
    print("  'reset'         : Clear conversation memory")
    print("  'transcript'    : View raw conversation history")
    print("=" * 60 + "\n")

    context = ContextManager(owner_name="Manan")
    llm = get_llm_provider(settings)
    engine = AgentEngine(llm_provider=llm, context_manager=context)

    # Initial simulated caller prompt
    caller_name = input("Enter caller name (or press Enter for Unknown): ").strip()
    if caller_name:
        context.set_caller(caller_id="+91-9876543210", caller_name=caller_name)
    else:
        context.set_caller(caller_id="+91-9876543210", caller_name=None)

    print(
        f"\n[Call Connected from: {context.caller_context.caller_name or 'Unknown Caller'} ({context.caller_context.caller_id})]\n"
    )

    while True:
        try:
            user_msg = input("\n👤 Caller: ").strip()
            if not user_msg:
                continue

            if user_msg.lower() in ("exit", "quit", "q"):
                print("\n[Call Terminated]")
                break

            if user_msg.lower() == "reset":
                engine.conversation.clear()
                print("\n[Conversation memory cleared]")
                continue

            if user_msg.lower() == "transcript":
                print("\n--- Current Transcript ---")
                for entry in engine.conversation.to_transcript():
                    print(f"{entry['role'].upper()}: {entry['content']}")
                print("--------------------------")
                continue

            if user_msg.lower() == "context":
                name = input("New caller name: ").strip()
                rel = input("Relationship: ").strip()
                context.set_caller(
                    caller_id=context.caller_context.caller_id,
                    caller_name=name or None,
                    relationship=rel or None,
                )
                print(f"[Context updated: {name} ({rel})]")
                continue

            print("🤖 Agent: ", end="", flush=True)
            result = await engine.step(user_msg)
            print(result.response_text)

            if result.tool_calls:
                for tc in result.tool_calls:
                    print(f"   ⚙️ [Tool Call: {tc.name}({tc.arguments})]")

            print(f"   ⏱️ [Turn {result.turn_index} | Latency: {result.total_latency_ms:.0f}ms]")

        except KeyboardInterrupt:
            print("\n[Call Ended]")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
