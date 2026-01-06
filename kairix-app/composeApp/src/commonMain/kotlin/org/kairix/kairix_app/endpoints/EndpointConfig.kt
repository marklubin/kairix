package org.kairix.kairix_app.endpoints

/**
 * Represents a server endpoint configuration.
 */
data class EndpointConfig(
    val id: String,
    val label: String,
    val baseUrl: String,
    val voiceUrl: String,
    val eventsUrl: String,
    val agentId: String,
    val isSelected: Boolean,
    val createdAt: String
) {
    /**
     * Returns the WebSocket URL for the chat endpoint.
     */
    val chatUrl: String
        get() = baseUrl.replace("http://", "ws://").replace("https://", "wss://") + "/ws"

    companion object {
        /**
         * Default CARRIZO endpoint configuration.
         */
        fun carrizo(): EndpointConfig = EndpointConfig(
            id = "carrizo-default",
            label = "Carrizo",
            baseUrl = "http://100.86.139.116:8000",
            voiceUrl = "ws://100.86.139.116:8000/voice",
            eventsUrl = "ws://100.86.139.116:8000/events/agent-62f4b273-69c4-41d3-8571-02a0413756fb",
            agentId = "agent-62f4b273-69c4-41d3-8571-02a0413756fb",
            isSelected = false,
            createdAt = "2024-01-01T00:00:00Z"
        )

        /**
         * Default SALINAS endpoint configuration.
         */
        fun salinas(): EndpointConfig = EndpointConfig(
            id = "salinas-default",
            label = "Salinas",
            baseUrl = "http://100.120.96.128:8000",
            voiceUrl = "ws://100.120.96.128:8000/voice",
            eventsUrl = "ws://100.120.96.128:8000/events/agent-56a10649-420a-4639-83f3-575e12964442",
            agentId = "agent-56a10649-420a-4639-83f3-575e12964442",
            isSelected = true,
            createdAt = "2024-01-01T00:00:01Z"
        )
    }
}
