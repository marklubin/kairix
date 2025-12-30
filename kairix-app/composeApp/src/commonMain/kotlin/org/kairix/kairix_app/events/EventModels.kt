package org.kairix.kairix_app.events

import androidx.compose.ui.graphics.Color
import kotlin.math.roundToInt
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.decodeFromJsonElement

/**
 * Raw event from the /events/{agent_id} WebSocket.
 */
@Serializable
data class AgentEvent(
    val id: String,
    @SerialName("agent_id") val agentId: String,
    @SerialName("event_type") val eventType: String,
    val payload: JsonObject,
    @SerialName("created_at") val createdAt: String
)

/**
 * Sealed interface for displayable events.
 * Each implementation encapsulates its own parsing and display configuration.
 */
sealed interface DisplayableEvent {
    /** Unique ID from the original event */
    val id: String

    /** ISO timestamp from the original event */
    val createdAt: String

    /** Display title for the card header */
    val title: String

    /** Title color for this event type */
    val titleColor: Color

    /** Primary content lines to display */
    val contentLines: List<String>

    /** Optional expandable text (null if not applicable) */
    val expandableText: String?

    companion object {
        private val json = Json { ignoreUnknownKeys = true }

        /**
         * Parse an AgentEvent into a DisplayableEvent.
         * Never returns null - unknown types become UnknownEvent, parse errors become ParseErrorEvent.
         */
        fun fromAgentEvent(event: AgentEvent): DisplayableEvent {
            return when (event.eventType) {
                "session_boundary" -> SessionBoundaryEvent.parse(event, json)
                    ?: ParseErrorEvent(event.id, event.createdAt, event.eventType, "Invalid payload")
                "summary_complete" -> SummaryCompleteEvent.parse(event, json)
                    ?: ParseErrorEvent(event.id, event.createdAt, event.eventType, "Invalid payload")
                "insights_complete" -> InsightsCompleteEvent.parse(event, json)
                    ?: ParseErrorEvent(event.id, event.createdAt, event.eventType, "Invalid payload")
                "context_state" -> ContextStateEvent.parse(event, json)
                    ?: ParseErrorEvent(event.id, event.createdAt, event.eventType, "Invalid payload")
                "persona_step_complete", "human_step_complete", "world_step_complete" ->
                    StepCompleteEvent.parse(event, json)
                        ?: ParseErrorEvent(event.id, event.createdAt, event.eventType, "Invalid payload")
                else -> UnknownEvent(event.id, event.createdAt, event.eventType)
            }
        }
    }
}

// =============================================================================
// Event Implementations
// =============================================================================

/**
 * Session boundary - conversation gap identified.
 */
data class SessionBoundaryEvent(
    override val id: String,
    override val createdAt: String,
    val boundaryDetected: Boolean,
    val gapMinutes: Double,
    val messageCount: Int
) : DisplayableEvent {

    override val title: String = "Session Boundary"
    override val titleColor: Color = Color(0xFF7C4DFF) // Purple

    override val contentLines: List<String> = listOf(
        "Detected: ${if (boundaryDetected) "Yes" else "No"}",
        "Gap: ${((gapMinutes * 10).roundToInt() / 10.0)} minutes",
        "Messages: $messageCount"
    )

    override val expandableText: String? = null

    companion object {
        fun parse(event: AgentEvent, json: Json): SessionBoundaryEvent? {
            return try {
                val payload = json.decodeFromJsonElement<SessionBoundaryPayload>(event.payload)
                SessionBoundaryEvent(
                    id = event.id,
                    createdAt = event.createdAt,
                    boundaryDetected = payload.boundaryDetected,
                    gapMinutes = payload.gapMinutes,
                    messageCount = payload.messageCount
                )
            } catch (e: Exception) {
                println("ERROR: Failed to parse SessionBoundaryEvent payload: ${e.message}")
                println("  Event ID: ${event.id}")
                println("  Payload: ${event.payload}")
                null
            }
        }
    }
}

@Serializable
private data class SessionBoundaryPayload(
    @SerialName("boundary_detected") val boundaryDetected: Boolean,
    @SerialName("gap_minutes") val gapMinutes: Double,
    @SerialName("message_count") val messageCount: Int
)

/**
 * Summary complete - session has been summarized.
 */
data class SummaryCompleteEvent(
    override val id: String,
    override val createdAt: String,
    val messageCount: Int,
    val summary: String
) : DisplayableEvent {

    override val title: String = "Summary Complete"
    override val titleColor: Color = Color(0xFF4CAF50) // Green

    override val contentLines: List<String> = listOf(
        "$messageCount messages summarized"
    )

    override val expandableText: String = summary

    companion object {
        fun parse(event: AgentEvent, json: Json): SummaryCompleteEvent? {
            return try {
                val payload = json.decodeFromJsonElement<SummaryCompletePayload>(event.payload)
                SummaryCompleteEvent(
                    id = event.id,
                    createdAt = event.createdAt,
                    messageCount = payload.messageCount,
                    summary = payload.summary
                )
            } catch (e: Exception) {
                println("ERROR: Failed to parse SummaryCompleteEvent payload: ${e.message}")
                println("  Event ID: ${event.id}")
                println("  Payload: ${event.payload}")
                null
            }
        }
    }
}

@Serializable
private data class SummaryCompletePayload(
    @SerialName("message_count") val messageCount: Int,
    val summary: String
)

/**
 * Insights complete - background insights evaluation finished.
 */
data class InsightsCompleteEvent(
    override val id: String,
    override val createdAt: String,
    val triggered: Boolean,
    val response: String?
) : DisplayableEvent {

    override val title: String = "Insights Complete"
    override val titleColor: Color = Color(0xFF2196F3) // Blue

    override val contentLines: List<String> = listOf(
        "Triggered: ${if (triggered) "Yes" else "No"}"
    )

    override val expandableText: String? = response?.takeIf { it.isNotBlank() }

    companion object {
        fun parse(event: AgentEvent, json: Json): InsightsCompleteEvent? {
            return try {
                val payload = json.decodeFromJsonElement<InsightsCompletePayload>(event.payload)
                InsightsCompleteEvent(
                    id = event.id,
                    createdAt = event.createdAt,
                    triggered = payload.triggered,
                    response = payload.response
                )
            } catch (e: Exception) {
                println("ERROR: Failed to parse InsightsCompleteEvent payload: ${e.message}")
                println("  Event ID: ${event.id}")
                println("  Payload: ${event.payload}")
                null
            }
        }
    }
}

@Serializable
private data class InsightsCompletePayload(
    val triggered: Boolean,
    val response: String? = null
)

/**
 * Unknown event type - fallback for unrecognized events.
 */
data class UnknownEvent(
    override val id: String,
    override val createdAt: String,
    val eventType: String
) : DisplayableEvent {

    override val title: String = eventType.uppercase()
    override val titleColor: Color = Color(0xFF9E9E9E) // Gray
    override val contentLines: List<String> = listOf("Unknown event type")
    override val expandableText: String? = null
}

/**
 * Parse error event - when a known event type fails to parse.
 */
data class ParseErrorEvent(
    override val id: String,
    override val createdAt: String,
    val eventType: String,
    val errorMessage: String
) : DisplayableEvent {

    override val title: String = "Parse Error"
    override val titleColor: Color = Color(0xFFE53935) // Red
    override val contentLines: List<String> = listOf(
        "Event type: $eventType",
        "Error: $errorMessage"
    )
    override val expandableText: String? = null
}

// =============================================================================
// Memory Block / Context State
// =============================================================================

/**
 * A single memory block from the agent's context.
 */
@Serializable
data class MemoryBlock(
    val label: String,
    val value: String,
    @SerialName("updated_at") val updatedAt: String? = null
)

/**
 * Context state event - full snapshot of agent's memory blocks.
 * Used to update the Context view with latest block values.
 */
data class ContextStateEvent(
    override val id: String,
    override val createdAt: String,
    val blocks: List<MemoryBlock>
) : DisplayableEvent {

    override val title: String = "Context Updated"
    override val titleColor: Color = Color(0xFFFF9800) // Orange

    override val contentLines: List<String> = listOf(
        "${blocks.size} memory blocks"
    )

    override val expandableText: String? = blocks.joinToString("\n\n") { block ->
        "[${block.label}]\n${block.value.take(100)}${if (block.value.length > 100) "..." else ""}"
    }.takeIf { it.isNotBlank() }

    companion object {
        fun parse(event: AgentEvent, json: Json): ContextStateEvent? {
            return try {
                val payload = json.decodeFromJsonElement<ContextStatePayload>(event.payload)
                ContextStateEvent(
                    id = event.id,
                    createdAt = event.createdAt,
                    blocks = payload.blocks
                )
            } catch (e: Exception) {
                println("ERROR: Failed to parse ContextStateEvent payload: ${e.message}")
                println("  Event ID: ${event.id}")
                println("  Payload: ${event.payload}")
                null
            }
        }
    }
}

@Serializable
private data class ContextStatePayload(
    val blocks: List<MemoryBlock>
)

// =============================================================================
// Step Complete Events (persona, human, world block updates)
// =============================================================================

/**
 * Step complete event - memory block update after session summarization.
 * Handles persona_step_complete, human_step_complete, and world_step_complete events.
 */
data class StepCompleteEvent(
    override val id: String,
    override val createdAt: String,
    val blockLabel: String,
    val updated: Boolean,
    val newValue: String?,
    val searchedKp3: Boolean
) : DisplayableEvent {

    override val title: String = "${blockLabel.replaceFirstChar { it.uppercase() }} Step"

    override val titleColor: Color = when (blockLabel) {
        "persona" -> Color(0xFFC2185B) // Dark Pink
        "human" -> Color(0xFF1976D2)   // Blue
        "world" -> Color(0xFF388E3C)   // Green
        else -> Color.Gray
    }

    override val contentLines: List<String> = buildList {
        add(if (updated) "Block updated" else "No changes needed")
        if (searchedKp3) add("Searched KP3")
    }

    override val expandableText: String? = newValue?.takeIf { updated }

    companion object {
        fun parse(event: AgentEvent, json: Json): StepCompleteEvent? {
            return try {
                val payload = json.decodeFromJsonElement<StepCompletePayload>(event.payload)
                StepCompleteEvent(
                    id = event.id,
                    createdAt = event.createdAt,
                    blockLabel = payload.blockLabel,
                    updated = payload.updated,
                    newValue = payload.newValue,
                    searchedKp3 = payload.searchedKp3
                )
            } catch (e: Exception) {
                println("ERROR: Failed to parse StepCompleteEvent payload: ${e.message}")
                println("  Event ID: ${event.id}")
                println("  Payload: ${event.payload}")
                null
            }
        }
    }
}

@Serializable
private data class StepCompletePayload(
    val updated: Boolean,
    @SerialName("block_label") val blockLabel: String,
    @SerialName("new_value") val newValue: String? = null,
    @SerialName("passage_id") val passageId: String? = null,
    @SerialName("searched_kp3") val searchedKp3: Boolean = false
)