package org.kairix.kairix_app.chat

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Role in the conversation.
 */
enum class ChatRole {
    USER,
    ASSISTANT
}

/**
 * A chat message in the conversation.
 */
data class ChatMessage(
    val id: String,
    val agentId: String,
    val role: ChatRole,
    val content: String,
    val createdAt: String,
    val isStreaming: Boolean = false
)

// WebSocket message types for the /ws endpoint

/**
 * Input message sent from client to server.
 */
@Serializable
data class InputChunk(
    val type: String = "input_chunk",
    val text: String,
    val timestamp: Double
)

/**
 * Response start message from server.
 */
@Serializable
data class ResponseStart(
    val type: String,
    val id: String,
    val timestamp: Double
)

/**
 * Response chunk message from server (streaming token).
 */
@Serializable
data class ResponseChunk(
    val type: String,
    @SerialName("chunk_id") val chunkId: String,
    @SerialName("response_id") val responseId: String,
    val text: String,
    val timestamp: Double
)

/**
 * Response done message from server.
 */
@Serializable
data class ResponseDone(
    val type: String,
    val id: String,
    val timestamp: Double
)

/**
 * Generic WebSocket message for parsing the type field first.
 */
@Serializable
data class WebSocketMessage(
    val type: String
)
