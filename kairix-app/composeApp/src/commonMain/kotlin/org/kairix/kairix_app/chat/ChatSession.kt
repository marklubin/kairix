package org.kairix.kairix_app.chat

import io.ktor.client.*
import io.ktor.client.plugins.websocket.*
import io.ktor.websocket.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.Json
import org.kairix.kairix_app.db.ChatRepository
import kotlin.random.Random

/**
 * Manages WebSocket chat sessions with streaming support.
 */
class ChatSession(private val repository: ChatRepository) {
    private val client = HttpClient {
        install(WebSockets)
    }

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    private var sessionScope: CoroutineScope? = null
    private var session: WebSocketSession? = null
    private var currentAgentId: String? = null

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected

    // Track current streaming response
    private var currentResponseId: String? = null
    private var streamingContent = StringBuilder()

    /**
     * Connect to the chat WebSocket endpoint.
     */
    suspend fun connect(chatUrl: String, agentId: String) {
        if (_isConnected.value) return

        currentAgentId = agentId
        sessionScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

        val urlWithAgent = "$chatUrl?agent_id=$agentId"

        try {
            client.webSocketSession(urlWithAgent).also { ws ->
                session = ws
                _isConnected.value = true

                // Start receive loop
                sessionScope?.launch {
                    receiveLoop(ws)
                }
            }
        } catch (e: Exception) {
            sessionScope?.cancel()
            sessionScope = null
            _isConnected.value = false
            println("ChatSession: Failed to connect: ${e.message}")
        }
    }

    /**
     * Disconnect from the chat WebSocket.
     */
    suspend fun disconnect() {
        sessionScope?.cancel()
        sessionScope = null

        session?.close()
        session = null

        _isConnected.value = false
        currentResponseId = null
        streamingContent.clear()
    }

    /**
     * Load chat history from the database.
     */
    suspend fun loadHistory(agentId: String) {
        currentAgentId = agentId
        val history = repository.loadRecentMessages(agentId, 100)
        _messages.value = history
    }

    /**
     * Send a user message.
     */
    suspend fun sendMessage(text: String) {
        val agentId = currentAgentId ?: return
        val ws = session ?: return

        // Create and add user message
        val userMessage = ChatMessage(
            id = generateId(),
            agentId = agentId,
            role = ChatRole.USER,
            content = text,
            createdAt = currentTimestamp(),
            isStreaming = false
        )

        // Add to UI immediately
        _messages.value = _messages.value + userMessage

        // Persist user message
        repository.insertMessage(userMessage)

        // Send to server
        val inputChunk = InputChunk(
            text = text,
            timestamp = messageCounter.toDouble()
        )

        try {
            ws.send(Frame.Text(json.encodeToString(InputChunk.serializer(), inputChunk)))
        } catch (e: Exception) {
            println("ChatSession: Failed to send message: ${e.message}")
        }
    }

    private var messageCounter = 0L

    private fun generateId(): String = "msg-${Random.nextLong().toString(16)}-${messageCounter++}"

    private fun currentTimestamp(): String = "T${messageCounter}"

    /**
     * Clear all messages for the current agent.
     */
    suspend fun clearHistory() {
        val agentId = currentAgentId ?: return
        repository.clearMessages(agentId)
        _messages.value = emptyList()
    }

    /**
     * Receive loop for WebSocket messages.
     */
    private suspend fun receiveLoop(ws: WebSocketSession) {
        try {
            for (frame in ws.incoming) {
                when (frame) {
                    is Frame.Text -> handleTextFrame(frame.readText())
                    is Frame.Close -> break
                    else -> { /* ignore binary, ping/pong */ }
                }
            }
        } catch (e: CancellationException) {
            // Normal cancellation during disconnect
        } catch (e: Exception) {
            println("ChatSession: Receive error: ${e.message}")
            _isConnected.value = false
        }
    }

    /**
     * Handle incoming text frame from server.
     */
    private suspend fun handleTextFrame(text: String) {
        val agentId = currentAgentId ?: return

        // Parse the type first
        val messageType = try {
            json.decodeFromString(WebSocketMessage.serializer(), text)
        } catch (e: Exception) {
            println("ChatSession: Failed to parse message type: ${e.message}")
            return
        }

        when (messageType.type) {
            "response_start" -> {
                val response = json.decodeFromString(ResponseStart.serializer(), text)
                currentResponseId = response.id
                streamingContent.clear()

                // Create placeholder assistant message
                val assistantMessage = ChatMessage(
                    id = response.id,
                    agentId = agentId,
                    role = ChatRole.ASSISTANT,
                    content = "",
                    createdAt = currentTimestamp(),
                    isStreaming = true
                )
                _messages.value = _messages.value + assistantMessage
            }

            "response_chunk" -> {
                val chunk = json.decodeFromString(ResponseChunk.serializer(), text)
                if (chunk.responseId == currentResponseId) {
                    streamingContent.append(chunk.text)

                    // Update the message in the list
                    _messages.value = _messages.value.map { msg ->
                        if (msg.id == currentResponseId) {
                            msg.copy(content = streamingContent.toString())
                        } else {
                            msg
                        }
                    }
                }
            }

            "response_done" -> {
                val done = json.decodeFromString(ResponseDone.serializer(), text)
                if (done.id == currentResponseId) {
                    // Finalize the message
                    val finalContent = streamingContent.toString()
                    _messages.value = _messages.value.map { msg ->
                        if (msg.id == currentResponseId) {
                            msg.copy(content = finalContent, isStreaming = false)
                        } else {
                            msg
                        }
                    }

                    // Persist the completed assistant message
                    _messages.value.find { it.id == currentResponseId }?.let { msg ->
                        repository.insertMessage(msg)
                    }

                    currentResponseId = null
                    streamingContent.clear()
                }
            }
        }
    }
}
