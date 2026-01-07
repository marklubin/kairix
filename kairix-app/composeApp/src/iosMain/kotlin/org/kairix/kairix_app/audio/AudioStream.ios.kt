package org.kairix.kairix_app.audio

import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.get
import kotlinx.cinterop.set
import platform.AVFAudio.*
import platform.Foundation.NSNotificationCenter
import platform.Foundation.NSOperationQueue
import platform.darwin.NSObjectProtocol

@OptIn(ExperimentalForeignApi::class)
actual class AudioStream actual constructor(
    private val sampleRateIn: Int,
    private val sampleRateOut: Int,
) {
    private val audioEngine = AVAudioEngine()
    private val playerNode = AVAudioPlayerNode()
    private var isCapturing = false
    private var isPlaying = false
    private var hwSampleRate: Int = 48000  // Will be set from actual hardware
    private var configChangeObserver: NSObjectProtocol? = null

    // Format for playback (what server sends us)
    private val playbackFormat = AVAudioFormat(
        standardFormatWithSampleRate = sampleRateOut.toDouble(),
        channels = 1u
    )

    actual fun startCapture(onAudioChunk: (ByteArray) -> Unit) {
        if (isCapturing) return

        // 1. Configure audio session
        val session = AVAudioSession.sharedInstance()
        session.setCategory(
            AVAudioSessionCategoryPlayAndRecord,
            mode = AVAudioSessionModeVoiceChat,
            options = AVAudioSessionCategoryOptionDefaultToSpeaker or
                    AVAudioSessionCategoryOptionAllowBluetooth,
            error = null
        )
        session.setActive(true, error = null)

        // 2. Set up player node for playback FIRST (before voice processing)
        audioEngine.attachNode(playerNode)
        audioEngine.connect(playerNode, audioEngine.mainMixerNode, playbackFormat)

        // 3. Get input node
        val inputNode = audioEngine.inputNode
        val outputNode = audioEngine.outputNode

        // 4. Enable voice processing on BOTH nodes for echo cancellation
        // This must be done AFTER nodes are connected but BEFORE engine starts
        inputNode.setVoiceProcessingEnabled(true, error = null)
        outputNode.setVoiceProcessingEnabled(true, error = null)

        // 5. Get hardware format AFTER enabling voice processing (format may change)
        val hwFormat = inputNode.outputFormatForBus(0u)
        hwSampleRate = hwFormat.sampleRate.toInt()

        // 6. Install tap at hardware format
        inputNode.installTapOnBus(
            bus = 0u,
            bufferSize = 4096u,
            format = hwFormat
        ) { buffer, _ ->
            buffer?.let {
                val bytes = pcmBufferToBytesResampled(it, hwSampleRate, sampleRateIn)
                if (bytes.isNotEmpty()) {
                    onAudioChunk(bytes)
                }
            }
        }

        // 7. Observe configuration changes - engine stops itself after voice processing enabled
        configChangeObserver = NSNotificationCenter.defaultCenter.addObserverForName(
            name = AVAudioEngineConfigurationChangeNotification,
            `object` = audioEngine,
            queue = NSOperationQueue.mainQueue
        ) { _ ->
            // Engine stopped due to config change, restart it
            if (!audioEngine.isRunning()) {
                audioEngine.prepare()
                audioEngine.startAndReturnError(null)
            }
        }

        // 8. Start the engine
        audioEngine.prepare()
        audioEngine.startAndReturnError(null)

        // 9. If engine stopped (due to voice processing config change), start again
        if (!audioEngine.isRunning()) {
            audioEngine.prepare()
            audioEngine.startAndReturnError(null)
        }

        isCapturing = true
    }

    actual fun stopCapture() {
        if (!isCapturing) return

        // Remove config change observer
        configChangeObserver?.let {
            NSNotificationCenter.defaultCenter.removeObserver(it)
            configChangeObserver = null
        }

        audioEngine.inputNode.removeTapOnBus(0u)
        audioEngine.stop()
        isCapturing = false

        AVAudioSession.sharedInstance().setActive(false, error = null)
    }

    actual fun playAudio(data: ByteArray) {
        if (!isCapturing) return  // Engine must be running

        val buffer = bytesToPcmBuffer(data) ?: return

        if (!isPlaying) {
            playerNode.play()
            isPlaying = true
        }

        playerNode.scheduleBuffer(buffer, completionHandler = null)
    }

    actual fun stopPlayback() {
        if (isPlaying) {
            playerNode.stop()
            isPlaying = false
        }
    }

    /**
     * Convert AVAudioPCMBuffer (float32) to ByteArray (int16 PCM) with resampling.
     * Resamples from hardware rate (e.g., 48kHz) to target rate (e.g., 16kHz).
     * Uses linear interpolation for reasonable quality.
     */
    private fun pcmBufferToBytesResampled(
        buffer: AVAudioPCMBuffer,
        fromRate: Int,
        toRate: Int
    ): ByteArray {
        val floatData = buffer.floatChannelData ?: return ByteArray(0)
        val inputFrameCount = buffer.frameLength.toInt()

        if (inputFrameCount == 0) return ByteArray(0)

        val channelData = floatData[0] ?: return ByteArray(0)

        // Calculate resampling ratio and output size
        val ratio = fromRate.toDouble() / toRate  // e.g., 48000/16000 = 3.0
        val outputFrameCount = (inputFrameCount / ratio).toInt()

        val bytes = ByteArray(outputFrameCount * 2)

        for (i in 0 until outputFrameCount) {
            // Linear interpolation for better quality than simple decimation
            val srcPos = i * ratio
            val srcIdx = srcPos.toInt()
            val frac = (srcPos - srcIdx).toFloat()

            val sample1 = channelData[srcIdx]
            val sample2 = if (srcIdx + 1 < inputFrameCount) channelData[srcIdx + 1] else sample1
            val interpolated = sample1 + (sample2 - sample1) * frac

            // Convert to int16
            val intSample = (interpolated * 32767f)
                .toInt()
                .coerceIn(-32768, 32767)
                .toShort()

            // Little-endian
            bytes[i * 2] = (intSample.toInt() and 0xFF).toByte()
            bytes[i * 2 + 1] = (intSample.toInt() shr 8 and 0xFF).toByte()
        }

        return bytes
    }

    /**
     * Convert ByteArray (int16 PCM) to AVAudioPCMBuffer (float32).
     * Reverse of pcmBufferToBytes for playback.
     * Uses playbackFormat configured at construction time.
     */
    private fun bytesToPcmBuffer(data: ByteArray): AVAudioPCMBuffer? {
        if (data.isEmpty()) return null

        val frameCount = data.size / 2  // 2 bytes per sample

        val buffer = AVAudioPCMBuffer(playbackFormat, frameCapacity = frameCount.toUInt())

        buffer.frameLength = frameCount.toUInt()

        val floatData = buffer.floatChannelData ?: return null
        val channelData = floatData[0] ?: return null

        // Convert int16 little-endian to float32
        for (i in 0 until frameCount) {
            val low = data[i * 2].toInt() and 0xFF
            val high = data[i * 2 + 1].toInt()
            val intSample = (high shl 8) or low
            // Convert to float in range -1.0 to 1.0
            channelData[i] = intSample.toFloat() / 32768f
        }

        return buffer
    }
}
