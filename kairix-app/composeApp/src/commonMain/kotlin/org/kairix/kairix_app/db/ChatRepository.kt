package org.kairix.kairix_app.db

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.IO
import kotlinx.coroutines.withContext
import org.kairix.kairix_app.chat.ChatMessage
import org.kairix.kairix_app.chat.ChatRole
import org.kairix.kairixapp.db.ChatMessageEntity

/**
 * Repository for persisting and retrieving chat messages from SQLite.
 * All database operations run on Dispatchers.IO to avoid blocking the UI.
 */
class ChatRepository(private val database: KairixDatabase) {

    private val queries = database.chatMessageQueries

    /**
     * Insert a new chat message.
     */
    suspend fun insertMessage(message: ChatMessage) = withContext(Dispatchers.IO) {
        queries.insertMessage(
            id = message.id,
            agent_id = message.agentId,
            role = message.role.name,
            content = message.content,
            created_at = message.createdAt
        )
    }

    /**
     * Update message content (used when streaming completes).
     */
    suspend fun updateMessageContent(id: String, content: String) = withContext(Dispatchers.IO) {
        queries.updateMessageContent(content = content, id = id)
    }

    /**
     * Load all messages for an agent in chronological order.
     */
    suspend fun loadMessages(agentId: String): List<ChatMessage> = withContext(Dispatchers.IO) {
        queries.selectMessagesByAgent(agentId)
            .executeAsList()
            .map { it.toChatMessage() }
    }

    /**
     * Load recent messages for an agent (newest first, then reversed for display).
     */
    suspend fun loadRecentMessages(agentId: String, limit: Int = 50): List<ChatMessage> =
        withContext(Dispatchers.IO) {
            queries.selectRecentMessagesByAgent(agentId, limit.toLong())
                .executeAsList()
                .reversed()
                .map { it.toChatMessage() }
        }

    /**
     * Delete all messages for an agent.
     */
    suspend fun clearMessages(agentId: String) = withContext(Dispatchers.IO) {
        queries.deleteMessagesByAgent(agentId)
    }

    /**
     * Delete a specific message.
     */
    suspend fun deleteMessage(id: String) = withContext(Dispatchers.IO) {
        queries.deleteMessage(id)
    }

    /**
     * Extension to convert database entity to domain model.
     */
    private fun ChatMessageEntity.toChatMessage(): ChatMessage = ChatMessage(
        id = id,
        agentId = agent_id,
        role = ChatRole.valueOf(role),
        content = content,
        createdAt = created_at,
        isStreaming = false
    )
}
