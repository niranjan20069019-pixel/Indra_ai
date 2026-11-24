from __future__ import annotations

import pytest
from app.agent.context import ConversationContext, ContextManager
from app.llm.base import Message, Role


def test_conversation_context():
    ctx = ConversationContext(session_id="test")
    ctx.add_user_message("Hello")
    ctx.add_assistant_message("Hi!")
    assert len(ctx.messages) == 2
    assert ctx.messages[0].role == Role.USER
    assert ctx.messages[1].role == Role.ASSISTANT


def test_context_manager():
    cm = ContextManager()
    ctx = cm.get_or_create("s1")
    assert cm.get("s1") is ctx
    assert cm.get("s2") is None


def test_get_messages_for_llm():
    ctx = ConversationContext(session_id="test")
    ctx.add_system_message("You are INDRA")
    ctx.add_user_message("Hello")
    ctx.add_assistant_message("Hi!")
    msgs = ctx.get_messages_for_llm()
    assert len(msgs) == 3
    assert msgs[0].role == Role.SYSTEM


def test_clear():
    ctx = ConversationContext(session_id="test")
    ctx.add_user_message("Hello")
    ctx.clear()
    assert len(ctx.messages) == 0
