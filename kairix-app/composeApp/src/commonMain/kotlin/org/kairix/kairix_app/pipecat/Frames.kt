package org.kairix.kairix_app.pipecat

import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.Serializable
import kotlinx.serialization.protobuf.ProtoNumber
import kotlinx.serialization.protobuf.ProtoOneOf

/**
 * Pipecat frame types matching frames.proto
 *
 * Proto definition:
 * ```
 * message Frame {
 *   oneof frame {
 *     TextFrame text = 1;
 *     AudioRawFrame audio = 2;
 *     TranscriptionFrame transcription = 3;
 *     MessageFrame message = 4;
 *   }
 * }
 * ```
 */

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class TextFrame(
    @ProtoNumber(1) val id: ULong = 0u,
    @ProtoNumber(2) val name: String = "",
    @ProtoNumber(3) val text: String = "",
)

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class AudioRawFrame(
    @ProtoNumber(1) val id: ULong = 0u,
    @ProtoNumber(2) val name: String = "",
    @ProtoNumber(3) val audio: ByteArray = ByteArray(0),
    @ProtoNumber(4) val sampleRate: UInt = 0u,
    @ProtoNumber(5) val numChannels: UInt = 0u,
    @ProtoNumber(6) val pts: ULong? = null,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other == null || this::class != other::class) return false
        other as AudioRawFrame
        return id == other.id &&
                name == other.name &&
                audio.contentEquals(other.audio) &&
                sampleRate == other.sampleRate &&
                numChannels == other.numChannels &&
                pts == other.pts
    }

    override fun hashCode(): Int {
        var result = id.hashCode()
        result = 31 * result + name.hashCode()
        result = 31 * result + audio.contentHashCode()
        result = 31 * result + sampleRate.hashCode()
        result = 31 * result + numChannels.hashCode()
        result = 31 * result + (pts?.hashCode() ?: 0)
        return result
    }
}

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class TranscriptionFrame(
    @ProtoNumber(1) val id: ULong = 0u,
    @ProtoNumber(2) val name: String = "",
    @ProtoNumber(3) val text: String = "",
    @ProtoNumber(4) val userId: String = "",
    @ProtoNumber(5) val timestamp: String = "",
)

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class MessageFrame(
    @ProtoNumber(1) val data: String = "",
)

/**
 * Sealed interface for Frame oneof field.
 * Each subtype wraps one of the frame types with its proto field number.
 */
@Serializable
sealed interface FrameType

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class TextFrameHolder(@ProtoNumber(1) val frame: TextFrame) : FrameType

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class AudioFrameHolder(@ProtoNumber(2) val frame: AudioRawFrame) : FrameType

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class TranscriptionFrameHolder(@ProtoNumber(3) val frame: TranscriptionFrame) : FrameType

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class MessageFrameHolder(@ProtoNumber(4) val frame: MessageFrame) : FrameType

/**
 * Top-level Frame wrapper with oneof semantics.
 */
@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class Frame(
    @ProtoOneOf val frame: FrameType? = null,
)
