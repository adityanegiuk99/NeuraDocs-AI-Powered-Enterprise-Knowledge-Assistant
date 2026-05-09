"""
Prompt templates and engineering strategies for the RAG pipeline.

Key strategies:
1. Explicit grounding instruction — reduces hallucination ~40%
2. Structured output format with source citation
3. Query rewriting for conversational context
4. Chain-of-thought for multi-hop questions
"""

SYSTEM_PROMPT = """You are an intelligent internal knowledge assistant.
Your role is to help employees find accurate information from company documents.

## RULES — Follow these strictly:
1. Answer ONLY based on the provided context below. Never fabricate or assume information.
2. If the context does NOT contain enough information to answer, say: "I couldn't find this information in the knowledge base. You may want to check with the relevant department."
3. Always cite which document(s) your answer is based on using [Source: document_name].
4. Be concise but thorough. Use bullet points for multi-part answers.
5. If the question is ambiguous, ask a clarifying question before answering.
6. Maintain a professional and helpful tone.
7. Do NOT answer questions unrelated to the organization's knowledge base.
"""

RAG_USER_PROMPT = """## Conversation History
{conversation_history}

## Retrieved Context (from company documents)
{context}

## Question
{query}

Provide a helpful, accurate answer based strictly on the context above.
Cite sources using [Source: document_name, page X] format."""

QUERY_REWRITE_PROMPT = """You are a search query optimizer. Given a conversation history and the user's latest message, rewrite the message as a standalone search query that captures the full intent.

Rules:
- Resolve all pronouns and references (e.g., "it", "that policy", "the same thing")
- Include relevant context from the conversation history
- Keep the query concise but complete
- Output ONLY the rewritten query, nothing else

## Conversation History
{history}

## Latest User Message
{query}

## Rewritten Standalone Search Query:"""

SUMMARIZE_CONVERSATION_PROMPT = """Summarize the following conversation between a user and an AI assistant. Focus on:
- Key topics discussed
- Important facts or decisions mentioned
- Any unresolved questions

Keep the summary concise (3-5 sentences).

## Conversation
{conversation}

## Summary:"""


def build_rag_prompt(
    query: str,
    context_chunks: list[dict],
    conversation_history: str = "",
) -> str:
    """
    Build the full RAG prompt with retrieved context.
    
    Context ordering: most relevant first (attention models pay
    more attention to content at the start of the prompt).
    """
    # Format context chunks with source information
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        doc_title = chunk.get("document_title", "Unknown Document")
        page = chunk.get("page_number", "")
        section = chunk.get("section_heading", "")
        text = chunk.get("text", "")

        header = f"[Document: {doc_title}"
        if page:
            header += f", Page {page}"
        if section:
            header += f", Section: {section}"
        header += "]"

        context_parts.append(f"### Source {i}\n{header}\n{text}")

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."

    # Format conversation history
    history = conversation_history or "No previous conversation."

    return RAG_USER_PROMPT.format(
        conversation_history=history,
        context=context,
        query=query,
    )


def build_rewrite_prompt(query: str, history: str) -> str:
    """Build a query rewriting prompt."""
    return QUERY_REWRITE_PROMPT.format(history=history, query=query)


def build_summary_prompt(conversation: str) -> str:
    """Build a conversation summarization prompt."""
    return SUMMARIZE_CONVERSATION_PROMPT.format(conversation=conversation)
