package org.kairix.kairix_app.db

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.IO
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import org.kairix.kairix_app.events.AgentEvent

/**
 * Repository for persisting and retrieving AgentEvents from SQLite.
 * All database operations run on Dispatchers.IO to avoid blocking the UI.
 */
class EventRepository(driverFactory: DriverFactory) {

    private val database = KairixDatabase(driverFactory.createDriver())
    private val queries = database.agentEventQueries
    private val json = Json { ignoreUnknownKeys = true }

    /**
     * Check if an event already exists in the database.
     */
    suspend fun eventExists(id: String): Boolean = withContext(Dispatchers.IO) {
        queries.eventExists(id).executeAsOne() > 0
    }

    /**
     * Insert an event into the database.
     * Uses INSERT OR IGNORE to skip duplicates.
     * Returns true if inserted, false if already existed.
     */
    suspend fun insertEvent(event: AgentEvent): Boolean = withContext(Dispatchers.IO) {
        val exists = queries.eventExists(event.id).executeAsOne() > 0
        if (!exists) {
            queries.insertEvent(
                id = event.id,
                agent_id = event.agentId,
                event_type = event.eventType,
                payload = event.payload.toString(),
                created_at = event.createdAt
            )
        }
        !exists  // Return true if we inserted (didn't exist before)
    }

    /**
     * Load the most recent events from the database.
     * Returns events in chronological order (oldest first) for display.
     */
    suspend fun loadRecentEvents(limit: Int = 20): List<AgentEvent> = withContext(Dispatchers.IO) {
        queries.selectRecentEvents(limit.toLong())
            .executeAsList()
            .reversed()  // Reverse to get chronological order (oldest first)
            .map { entity ->
                AgentEvent(
                    id = entity.id,
                    agentId = entity.agent_id,
                    eventType = entity.event_type,
                    payload = json.decodeFromString<JsonObject>(entity.payload),
                    createdAt = entity.created_at
                )
            }
    }
}