import { useState, useEffect, useRef } from 'react'
import { useCustomChat } from './useCustomChat'
import { useTTS } from './contexts/TTSContext'
import { useSTT } from './contexts/STTContext'

export default function VoiceChat() {
  const chatHandler = useCustomChat()
  const { ttsService, isEnabled: isTTSEnabled } = useTTS()
  const { sttState, sttService } = useSTT()
  const [isRecording, setIsRecording] = useState(false)
  const [currentTranscript, setCurrentTranscript] = useState('')
  const [currentResponse, setCurrentResponse] = useState('')
  const [appState, setAppState] = useState<'idle' | 'recording' | 'processing' | 'speaking'>('idle')
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null)
  const [silenceCountdown, setSilenceCountdown] = useState(0)
  
  // Simple VAD - 2 second silence detection
  const SILENCE_THRESHOLD = 2000 // 2 seconds
  
  // Handle STT state changes
  useEffect(() => {
    if (sttState.status === 'listening' && 'interimTranscript' in sttState && sttState.interimTranscript) {
      setCurrentTranscript(sttState.interimTranscript)
      // Reset silence timer when new speech detected
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current)
        setSilenceCountdown(0)
      }
      
      // Start countdown
      let countdown = SILENCE_THRESHOLD / 1000
      setSilenceCountdown(countdown)
      
      const countdownInterval = setInterval(() => {
        countdown -= 0.1
        if (countdown <= 0) {
          clearInterval(countdownInterval)
        } else {
          setSilenceCountdown(Math.max(0, countdown))
        }
      }, 100)
      
      // Set new silence timer
      silenceTimerRef.current = setTimeout(async () => {
        clearInterval(countdownInterval)
        setSilenceCountdown(0)
        if (isRecording && currentTranscript.trim()) {
          await stopRecording()
        }
      }, SILENCE_THRESHOLD)
    }
  }, [sttState, currentTranscript, isRecording])
  
  // Update app state based on STT/TTS states
  useEffect(() => {
    if (sttState.status === 'listening') {
      setAppState('recording')
    } else if (sttState.status === 'processing') {
      setAppState('processing')
    } else if (chatHandler.isLoading) {
      setAppState('processing')
    }
  }, [sttState.status, chatHandler.isLoading])
  
  // Auto-play TTS responses
  useEffect(() => {
    const lastMessage = chatHandler.messages[chatHandler.messages.length - 1]
    if (lastMessage?.role === 'assistant' && lastMessage.content) {
      setCurrentResponse(lastMessage.content)
      setAppState('speaking')
      // Reset to idle after TTS would complete (rough estimate)
      setTimeout(() => {
        if (appState === 'speaking') {
          setAppState('idle')
        }
      }, lastMessage.content.length * 50) // ~50ms per character
    }
  }, [chatHandler.messages])
  
  const startRecording = async () => {
    try {
      setIsRecording(true)
      setCurrentTranscript('')
      setCurrentResponse('')
      await chatHandler.handleSTTToggle()
    } catch (error) {
      console.error('Failed to start recording:', error)
      setIsRecording(false)
      setAppState('idle')
    }
  }
  
  const stopRecording = async () => {
    try {
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current)
      }
      setSilenceCountdown(0)
      setIsRecording(false)
      await chatHandler.handleSTTToggle()
    } catch (error) {
      console.error('Failed to stop recording:', error)
    }
  }
  
  const handleScreenTap = async () => {
    if (appState === 'recording') {
      await stopRecording()
    } else if (appState === 'idle') {
      await startRecording()
    }
    // Ignore taps during processing or speaking
  }
  
  const getStateColor = () => {
    switch (appState) {
      case 'recording': return 'bg-red-500'
      case 'processing': return 'bg-yellow-500'
      case 'speaking': return 'bg-green-500'
      default: return 'bg-gray-800'
    }
  }
  
  const getStateText = () => {
    switch (appState) {
      case 'recording': return 'Listening...'
      case 'processing': return 'Processing...'
      case 'speaking': return 'Speaking...'
      default: return 'Tap to Start'
    }
  }
  
  return (
    <div 
      className={`fixed inset-0 ${getStateColor()} transition-colors duration-300 flex flex-col`}
      onClick={handleScreenTap}
    >
      {/* Status Bar */}
      <div className="bg-black/20 p-4 text-center">
        <h1 className="text-white text-2xl font-bold">{getStateText()}</h1>
      </div>
      
      {/* Caption Area */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-white text-center max-w-2xl">
          {appState === 'recording' && (
            <>
              <p className="text-4xl mb-4 min-h-[120px]">
                {currentTranscript || '...'}
              </p>
              {silenceCountdown > 0 && (
                <p className="text-xl opacity-70">
                  Auto-submit in {silenceCountdown.toFixed(1)}s
                </p>
              )}
            </>
          )}
          {appState === 'processing' && (
            <div className="text-4xl animate-pulse">Processing...</div>
          )}
          {appState === 'speaking' && (
            <p className="text-4xl animate-fade-in">{currentResponse}</p>
          )}
          {appState === 'idle' && (
            <div className="opacity-50">
              <div className="w-32 h-32 mx-auto mb-8 rounded-full bg-white/20 flex items-center justify-center">
                <svg className="w-20 h-20 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <p className="text-3xl">Tap anywhere to speak</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Visual State Indicator */}
      <div className="h-20 bg-black/20 flex items-center justify-center">
        {appState === 'recording' && (
          <div className="flex space-x-1">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="w-3 h-12 bg-white rounded-full animate-pulse" 
                style={{ animationDelay: `${i * 0.1}s` }} />
            ))}
          </div>
        )}
        {appState === 'processing' && (
          <div className="w-16 h-16 border-4 border-white/30 border-t-white rounded-full animate-spin" />
        )}
        {appState === 'speaking' && (
          <div className="w-20 h-20 bg-white/30 rounded-full animate-ping" />
        )}
      </div>
    </div>
  )
}