package org.kairix.kairix_app.db

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.IO
import kotlinx.coroutines.withContext
import org.kairix.kairix_app.endpoints.EndpointConfig
import org.kairix.kairixapp.db.EndpointConfigEntity

/**
 * Repository for persisting and retrieving endpoint configurations from SQLite.
 * All database operations run on Dispatchers.IO to avoid blocking the UI.
 */
class EndpointRepository(private val database: KairixDatabase) {

    private val queries = database.endpointConfigQueries

    /**
     * Get all endpoint configurations.
     */
    suspend fun getAllEndpoints(): List<EndpointConfig> = withContext(Dispatchers.IO) {
        queries.selectAllEndpoints()
            .executeAsList()
            .map { it.toEndpointConfig() }
    }

    /**
     * Get the currently selected endpoint.
     */
    suspend fun getSelectedEndpoint(): EndpointConfig? = withContext(Dispatchers.IO) {
        queries.selectSelectedEndpoint()
            .executeAsOneOrNull()
            ?.toEndpointConfig()
    }

    /**
     * Get an endpoint by ID.
     */
    suspend fun getEndpointById(id: String): EndpointConfig? = withContext(Dispatchers.IO) {
        queries.selectEndpointById(id)
            .executeAsOneOrNull()
            ?.toEndpointConfig()
    }

    /**
     * Insert a new endpoint configuration.
     */
    suspend fun insertEndpoint(endpoint: EndpointConfig) = withContext(Dispatchers.IO) {
        queries.insertEndpoint(
            id = endpoint.id,
            label = endpoint.label,
            base_url = endpoint.baseUrl,
            voice_url = endpoint.voiceUrl,
            events_url = endpoint.eventsUrl,
            agent_id = endpoint.agentId,
            is_selected = if (endpoint.isSelected) 1L else 0L,
            created_at = endpoint.createdAt
        )
    }

    /**
     * Update an existing endpoint configuration.
     */
    suspend fun updateEndpoint(endpoint: EndpointConfig) = withContext(Dispatchers.IO) {
        queries.updateEndpoint(
            label = endpoint.label,
            base_url = endpoint.baseUrl,
            voice_url = endpoint.voiceUrl,
            events_url = endpoint.eventsUrl,
            agent_id = endpoint.agentId,
            id = endpoint.id
        )
    }

    /**
     * Delete an endpoint configuration.
     */
    suspend fun deleteEndpoint(id: String) = withContext(Dispatchers.IO) {
        queries.deleteEndpoint(id)
    }

    /**
     * Set an endpoint as selected (clears other selections first).
     */
    suspend fun setSelectedEndpoint(id: String) = withContext(Dispatchers.IO) {
        queries.clearSelection()
        queries.setSelected(id)
    }

    /**
     * Check if endpoints table is empty.
     */
    suspend fun isEmpty(): Boolean = withContext(Dispatchers.IO) {
        queries.countEndpoints().executeAsOne() == 0L
    }

    /**
     * Seed default endpoints if the table is empty.
     */
    suspend fun seedDefaultsIfEmpty() = withContext(Dispatchers.IO) {
        if (queries.countEndpoints().executeAsOne() == 0L) {
            // Insert CARRIZO
            val carrizo = EndpointConfig.carrizo()
            queries.insertEndpoint(
                id = carrizo.id,
                label = carrizo.label,
                base_url = carrizo.baseUrl,
                voice_url = carrizo.voiceUrl,
                events_url = carrizo.eventsUrl,
                agent_id = carrizo.agentId,
                is_selected = if (carrizo.isSelected) 1L else 0L,
                created_at = carrizo.createdAt
            )

            // Insert SALINAS (selected by default)
            val salinas = EndpointConfig.salinas()
            queries.insertEndpoint(
                id = salinas.id,
                label = salinas.label,
                base_url = salinas.baseUrl,
                voice_url = salinas.voiceUrl,
                events_url = salinas.eventsUrl,
                agent_id = salinas.agentId,
                is_selected = if (salinas.isSelected) 1L else 0L,
                created_at = salinas.createdAt
            )
        }
    }

    /**
     * Extension to convert database entity to domain model.
     */
    private fun EndpointConfigEntity.toEndpointConfig(): EndpointConfig = EndpointConfig(
        id = id,
        label = label,
        baseUrl = base_url,
        voiceUrl = voice_url,
        eventsUrl = events_url,
        agentId = agent_id,
        isSelected = is_selected == 1L,
        createdAt = created_at
    )
}
