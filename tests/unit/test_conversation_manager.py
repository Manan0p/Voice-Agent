from apps.agent.conversation.manager import ConversationManager
from apps.agent.llm.base import Role


def test_conversation_manager_basic_flow() -> None:
    """Verify adding messages, turn counting, and transcript export."""
    cm = ConversationManager(max_turns=10)
    assert cm.turn_count == 0
    assert len(cm.get_messages()) == 0

    cm.add_user_message("Hello!")
    assert cm.turn_count == 1
    assert len(cm.get_messages()) == 1
    assert cm.get_messages()[0].role == Role.USER
    assert cm.get_messages()[0].content == "Hello!"

    cm.add_assistant_message("Hi there! How can I help you?")
    assert len(cm.get_messages()) == 2
    assert cm.get_messages()[1].role == Role.ASSISTANT

    transcript = cm.to_transcript()
    assert len(transcript) == 2
    assert transcript[0]["role"] == "user"
    assert transcript[1]["role"] == "assistant"


def test_conversation_manager_trimming() -> None:
    """Verify that messages beyond max_turns are cleanly trimmed."""
    cm = ConversationManager(max_turns=3)  # max 6 messages total

    for i in range(10):
        cm.add_user_message(f"User message {i}")
        cm.add_assistant_message(f"Assistant response {i}")

    messages = cm.get_messages()
    assert len(messages) <= 6
    # Verify the most recent message is present
    assert messages[-1].content == "Assistant response 9"
    assert messages[-2].content == "User message 9"


def test_conversation_manager_clear() -> None:
    """Verify reset function clears history and resets turn count."""
    cm = ConversationManager()
    cm.add_user_message("Hi")
    cm.add_assistant_message("Hello")
    assert cm.turn_count == 1

    cm.clear()
    assert cm.turn_count == 0
    assert len(cm.get_messages()) == 0
