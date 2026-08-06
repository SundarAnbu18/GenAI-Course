def get_history(conversation_id: str) -> BaseChatMessageHistory:
    settings = get_settings()
    if settings.history_dsn:
        from langchain_community.chat_message_histories import SQLChatMessageHistory
        return SQLChatMessageHistory(session_id=conversation_id, connection=settings.history_dsn)
    from langchain_core.chat_history import InMemoryChatMessageHistory
    return _MEMORY.setdefault(conversation_id, InMemoryChatMessageHistory())