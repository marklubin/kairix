package org.kairix.kairix_app.events

import io.ktor.client.*
import io.ktor.client.plugins.websocket.*
import io.ktor.websocket.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.Json
import org.kairix.kairix_app.db.EventRepository

/**
 * WebSocket client for receiving server events from /events/{agent_id}.
 * Events are persisted to SQLite via EventRepository.
 */
class EventSession(
    private val repository: EventRepository,
    private val maxDisplayEvents: Int = 50,
    private val loadOnStartup: Int = 20
) {
    private var client: HttpClient? = null

    private val json = Json { ignoreUnknownKeys = true }

    private var sessionScope: CoroutineScope? = null
    private var session: WebSocketSession? = null

    private val _events = MutableStateFlow<List<DisplayableEvent>>(emptyList())
    val events: StateFlow<List<DisplayableEvent>> = _events

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected

    // Track displayed event IDs to prevent duplicates in UI
    private val displayedEventIds = mutableSetOf<String>()

    /**
     * Connect to the events WebSocket endpoint.
     */
    suspend fun connect(eventsUrl: String) {
        if (_isConnected.value) return

        // Create fresh client for each connection
        client = HttpClient { install(WebSockets) }
        sessionScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

        try {
            client!!.webSocketSession(eventsUrl).also { ws ->
                session = ws
                _isConnected.value = true
                println("EventSession: Connected to $eventsUrl")

                sessionScope?.launch {
                    receiveLoop(ws)
                }
            }
        } catch (e: Exception) {
            println("EventSession: Connection failed: ${e.message}")
            cleanup()
            throw e
        }
    }

    /**
     * Disconnect from the events WebSocket.
     */
    fun disconnect() {
        println("EventSession: Disconnecting")
        cleanup()
    }

    /**
     * Clean up all resources.
     */
    private fun cleanup() {
        sessionScope?.cancel()
        sessionScope = null
        session = null
        client?.close()
        client = null
        _isConnected.value = false
    }

    /**
     * Clear all events from the display list.
     */
    fun clearEvents() {
        _events.value = emptyList()
        displayedEventIds.clear()
    }

    /**
     * Load persisted events from database on startup.
     * Call this before connecting to WebSocket.
     */
    suspend fun loadPersistedEvents() {
        val storedEvents = repository.loadRecentEvents(loadOnStartup)
        val displayable = storedEvents.map { DisplayableEvent.fromAgentEvent(it) }

        // Track IDs of loaded events to prevent duplicates
        displayedEventIds.clear()
        displayable.forEach { displayedEventIds.add(it.id) }

        // Take only the most recent for display
        _events.value = displayable.takeLast(maxDisplayEvents)
        println("EventSession: Loaded ${displayable.size} events from database")
    }

    /**
     * Receive loop: parse incoming JSON text frames.
     */
    private suspend fun receiveLoop(ws: WebSocketSession) {
        try {
            for (frame in ws.incoming) {
                when (frame) {
                    is Frame.Text -> handleTextFrame(frame.readText())
                    is Frame.Close -> {
                        println("EventSession: Received close frame")
                        break
                    }
                    else -> { /* ignore binary/ping/pong */ }
                }
            }
            // Loop exited normally (server closed connection)
            println("EventSession: Connection closed by server")
        } catch (e: CancellationException) {
            // Normal cancellation during disconnect - don't log as error
            println("EventSession: Receive loop cancelled")
        } catch (e: Exception) {
            println("EventSession: Receive loop error: ${e.message}")
        } finally {
            // Always update connection state when loop exits
            _isConnected.value = false
            session = null
        }
    }

    /**
     * Parse JSON text frame, persist to database, and add to display list.
     */
    private suspend fun handleTextFrame(text: String) {
        try {
            val agentEvent = json.decodeFromString<AgentEvent>(text)

            // Check if we've already displayed this event (prevents duplicates)
            if (displayedEventIds.contains(agentEvent.id)) {
                println("EventSession: Skipping duplicate event ${agentEvent.id}")
                return
            }

            // Persist to database - returns false if already exists
            val isNew = try {
                repository.insertEvent(agentEvent)
            } catch (e: Exception) {
                println("EventSession: Database insert failed: ${e.message}")
                true // Assume new if DB fails, so we still display it
            }

            if (!isNew) {
                println("EventSession: Event ${agentEvent.id} already in database, skipping")
                displayedEventIds.add(agentEvent.id) // Track it so we don't check DB again
                return
            }

            // Parse and add to display list (never returns null)
            val displayable = DisplayableEvent.fromAgentEvent(agentEvent)
            addEvent(displayable)
            println("EventSession: Received ${displayable.title} event")
        } catch (e: Exception) {
            println("EventSession: Failed to parse JSON: ${e.message}")
            println("  Raw text: $text")
        }
    }

    /**
     * Add event to display list, maintaining max size.
     */
    private fun addEvent(event: DisplayableEvent) {
        // Double-check for duplicates (belt and suspenders)
        if (displayedEventIds.contains(event.id)) return

        displayedEventIds.add(event.id)

        val currentList = _events.value.toMutableList()
        currentList.add(event)

        // Trim oldest events if over limit
        while (currentList.size > maxDisplayEvents) {
            val removed = currentList.removeAt(0)
            displayedEventIds.remove(removed.id)
        }

        _events.value = currentList.toList()
    }
}