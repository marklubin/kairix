package org.kairix.kairix_app.pipecat

import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.decodeFromByteArray
import kotlinx.serialization.encodeToByteArray
import kotlinx.serialization.protobuf.ProtoBuf

/**
 * Codec for encoding/decoding Pipecat protobuf frames.
 */
@OptIn(ExperimentalSerializationApi::class)
object PipecatCodec {

    private val protoBuf = ProtoBuf {
        encodeDefaults = false
    }

    /**
     * Encode an audio frame for sending to the server.
     */
    fun encodeAudioFrame(
        audio: ByteArray,
        sampleRate: Int,
        numChannels: Int = 1,
    ): ByteArray {
        val audioFrame = AudioRawFrame(
            audio = audio,
            sampleRate = sampleRate.toUInt(),
            numChannels = numChannels.toUInt(),
        )
        val frame = Frame(frame = AudioFrameHolder(audioFrame))
        return protoBuf.encodeToByteArray(frame)
    }

    /**
     * Decode a frame received from the server.
     * Returns the frame type for the caller to handle.
     */
    fun decodeFrame(bytes: ByteArray): FrameType? {
        val frame = protoBuf.decodeFromByteArray<Frame>(bytes)
        return frame.frame
    }

    /**
     * Convenience method to extract audio data from a received frame.
     * Returns null if the frame is not an audio frame.
     */
    fun extractAudio(frameType: FrameType): AudioData? {
        return when (frameType) {
            is AudioFrameHolder -> AudioData(
                audio = frameType.frame.audio,
                sampleRate = frameType.frame.sampleRate.toInt(),
                numChannels = frameType.frame.numChannels.toInt(),
            )
            else -> null
        }
    }

    /**
     * Convenience method to extract text from a received frame.
     * Returns null if the frame is not a text or transcription frame.
     */
    fun extractText(frameType: FrameType): String? {
        return when (frameType) {
            is TextFrameHolder -> frameType.frame.text
            is TranscriptionFrameHolder -> frameType.frame.text
            is MessageFrameHolder -> frameType.frame.data
            else -> null
        }
    }
}

/**
 * Simple data class for extracted audio data.
 */
data class AudioData(
    val audio: ByteArray,
    val sampleRate: Int,
    val numChannels: Int,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other == null || this::class != other::class) return false
        other as AudioData
        return audio.contentEquals(other.audio) &&
                sampleRate == other.sampleRate &&
                numChannels == other.numChannels
    }

    override fun hashCode(): Int {
        var result = audio.contentHashCode()
        result = 31 * result + sampleRate
        result = 31 * result + numChannels
        return result
    }
}
