package org.kairix.kairix_app.voice

import io.ktor.client.*
import io.ktor.client.plugins.websocket.*
import io.ktor.websocket.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.kairix.kairix_app.ConnectionState
import org.kairix.kairix_app.audio.AudioStream
import org.kairix.kairix_app.pipecat.AudioFrameHolder
import org.kairix.kairix_app.pipecat.PipecatCodec
import org.kairix.kairix_app.pipecat.TextFrameHolder
import org.kairix.kairix_app.pipecat.TranscriptionFrameHolder

/**
 * Orchestrates voice streaming: WebSocket + AudioStream + PipecatCodec
 */
class VoiceSession(
    private val sampleRateIn: Int = 16000,
    private val sampleRateOut: Int = 22050,
) {
    private val client = HttpClient {
        install(WebSockets)
    }

    // Session-scoped coroutine scope - cancelled on disconnect
    private var sessionScope: CoroutineScope? = null

    private var session: WebSocketSession? = null
    private var audioStream: AudioStream? = null
    private var receiveJob: Job? = null

    private val _state = MutableStateFlow(ConnectionState.DISCONNECTED)
    val state: StateFlow<ConnectionState> = _state

    private val _transcription = MutableStateFlow("")
    val transcription: StateFlow<String> = _transcription

    /**
     * Connect to voice server and start streaming.
     */
    suspend fun connect(serverUrl: String) {
        if (_state.value != ConnectionState.DISCONNECTED) return

        _state.value = ConnectionState.CONNECTING

        // Create session-scoped coroutine context
        sessionScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

        try {
            client.webSocketSession(serverUrl).also { ws ->
                session = ws

                // Create audio stream
                audioStream = AudioStream(sampleRateIn, sampleRateOut).apply {
                    startCapture { audioBytes ->
                        // Called from platform audio thread with PCM chunks
                        val encoded = PipecatCodec.encodeAudioFrame(audioBytes, sampleRateIn)
                        // Send on session scope - cancelled when session ends
                        sessionScope?.launch {
                            try {
                                ws.send(Frame.Binary(true, encoded))
                            } catch (e: Exception) {
                                // Connection closed, ignore
                            }
                        }
                    }
                }

                // Start receive loop on session scope
                receiveJob = sessionScope?.launch {
                    receiveLoop(ws)
                }

                _state.value = ConnectionState.CONNECTED
            }
        } catch (e: Exception) {
            sessionScope?.cancel()
            sessionScope = null
            _state.value = ConnectionState.ERROR
            throw e
        }
    }

    /**
     * Disconnect from voice server.
     */
    suspend fun disconnect() {
        // Cancel all session coroutines (receive loop + pending sends)
        sessionScope?.cancel()
        sessionScope = null
        receiveJob = null

        audioStream?.stopCapture()
        audioStream?.stopPlayback()
        audioStream = null

        session?.close()
        session = null

        _state.value = ConnectionState.DISCONNECTED
    }

    /**
     * Receive loop: decode incoming frames, route to audio or text.
     */
    private suspend fun receiveLoop(ws: WebSocketSession) {
        try {
            for (frame in ws.incoming) {
                when (frame) {
                    is Frame.Binary -> handleBinaryFrame(frame.readBytes())
                    is Frame.Text -> { /* ignore text frames for now */ }
                    is Frame.Close -> break
                    else -> { /* ping/pong handled by Ktor */ }
                }
            }
        } catch (e: CancellationException) {
            // Normal cancellation during disconnect
        } catch (e: Exception) {
            _state.value = ConnectionState.ERROR
        }
    }

    /**
     * Handle incoming binary frame from server.
     */
    private fun handleBinaryFrame(bytes: ByteArray) {
        val frameType = PipecatCodec.decodeFrame(bytes) ?: return

        when (frameType) {
            is AudioFrameHolder -> {
                val audioData = PipecatCodec.extractAudio(frameType)
                audioData?.let { audioStream?.playAudio(it.audio) }
            }
            is TextFrameHolder -> {
                _transcription.value = frameType.frame.text
            }
            is TranscriptionFrameHolder -> {
                _transcription.value = frameType.frame.text
            }
            else -> { /* ignore other frame types */ }
        }
    }
}
