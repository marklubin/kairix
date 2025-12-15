package org.kairix.kairix_app.audio

expect class AudioStream(
    sampleRateIn: Int,
    sampleRateOut: Int,
) {
    fun startCapture(onAudioChunk: (ByteArray) -> Unit)
    fun stopCapture()
    fun playAudio(data: ByteArray)
    fun stopPlayback()
}