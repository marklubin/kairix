package org.kairix.kairix_app.voice

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Voice(
    val id: String,
    val name: String,
    @SerialName("provider_voice_id") val providerVoiceId: String,
    val provider: String,
    val description: String?,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String?
)

@Serializable
data class AgentVoiceSettings(
    @SerialName("agent_id") val agentId: String,
    val voice: Voice?
)

@Serializable
data class SetAgentVoiceRequest(
    @SerialName("voice_id") val voiceId: String
)

@Serializable
data class SetAgentVoiceResponse(
    @SerialName("agent_id") val agentId: String,
    @SerialName("voice_id") val voiceId: String,
    @SerialName("active_pipelines_updated") val activePipelinesUpdated: Int
)
