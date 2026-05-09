"""
Conversation memory manager.
Implements short-term sliding window + long-term summarization.

This hybrid approach:
- Keeps last N turns in full detail for immediate context (follow-ups)
- Periodically compresses older turns into a summary to save tokens
- Summaries preserve intent while reducing token count ~80%
"""

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.utils.logging import get_logger

logger = get_logger(__name__)

WINDOW_SIZE = 6  # Number of recent turns to keep in full
SUMMARY_THRESHOLD = 10  # Summarize when message count exceeds this


class ConversationMemory:
    """
    Manages conversation context for the RAG pipeline.
    
    Short-term: Last WINDOW_SIZE messages in full text
    Long-term: Summary of older messages stored in the Conversation model
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_context(self, conversation_id: str) -> str:
        """
        Build conversation context string for the RAG prompt.
        Combines long-term summary + recent messages.
        """
        # Get conversation (includes summary)
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return ""

        parts = []

        # Include long-term summary if available
        if conversation.summary:
            parts.append(f"[Previous context summary]: {conversation.summary}")

        # Get recent messages
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(WINDOW_SIZE)
        )
        recent_messages = list(reversed(result.scalars().all()))

        # Format recent messages
        for msg in recent_messages:
            role = "User" if msg.role == "user" else "Assistant"
            parts.append(f"{role}: {msg.content}")

        return "\n\n".join(parts) if parts else ""

    async def should_summarize(self, conversation_id: str) -> bool:
        """Check if conversation needs summarization."""
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return False

        return conversation.message_count >= SUMMARY_THRESHOLD

    async def get_messages_for_summary(self, conversation_id: str) -> str:
        """Get older messages that should be summarized (beyond the window)."""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        all_messages = result.scalars().all()

        # Messages to summarize = everything except the last WINDOW_SIZE
        if len(all_messages) <= WINDOW_SIZE:
            return ""

        to_summarize = all_messages[:-WINDOW_SIZE]
        parts = []
        for msg in to_summarize:
            role = "User" if msg.role == "user" else "Assistant"
            parts.append(f"{role}: {msg.content}")

        return "\n\n".join(parts)

    async def save_summary(self, conversation_id: str, summary: str):
        """Save a compressed summary to the conversation record."""
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(summary=summary)
        )
        await self.db.flush()
        logger.info("conversation_summarized", conversation_id=conversation_id)

    async def add_messages(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        sources: str = None,
        confidence: float = None,
        latency_ms: float = None,
    ):
        """Add a user/assistant turn to the conversation."""
        # User message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )
        self.db.add(user_msg)

        # Assistant message
        asst_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_message,
            sources=sources,
            confidence=confidence,
            latency_ms=latency_ms,
        )
        self.db.add(asst_msg)

        # Update conversation message count
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.message_count += 2

        await self.db.flush()
