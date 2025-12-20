package org.kairix.kairix_app.voice

import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.json.Json

/**
 * REST client for the Voice Management API.
 */
class VoiceApiClient(private val baseUrl: String) {
    private val client = HttpClient {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
            })
        }
    }

    /**
     * List all available voices.
     * GET /voices
     */
    suspend fun listVoices(): List<Voice> {
        return client.get("$baseUrl/voices").body()
    }

    /**
     * Get the current voice setting for an agent.
     * GET /voices/agents/{agent_id}
     */
    suspend fun getAgentVoice(agentId: String): AgentVoiceSettings {
        return client.get("$baseUrl/voices/agents/$agentId").body()
    }

    /**
     * Set the voice for an agent.
     * PUT /voices/agents/{agent_id}
     */
    suspend fun setAgentVoice(agentId: String, voiceId: String): SetAgentVoiceResponse {
        return client.put("$baseUrl/voices/agents/$agentId") {
            contentType(ContentType.Application.Json)
            setBody(SetAgentVoiceRequest(voiceId))
        }.body()
    }
}
