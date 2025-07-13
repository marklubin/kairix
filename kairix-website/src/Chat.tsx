import { Chat } from "@/components/ui/chat"
import { Settings } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useCustomChat } from "./useCustomChat"
import { useTTS } from "./contexts/TTSContext"
import { useSTT } from "./contexts/STTContext"
import { useHotkey } from "./contexts/HotkeyContext"
import { useRef, useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { STTOverlay } from "@/components/ui/stt-overlay"

function ChatContainer() {
  const chatHandler = useCustomChat()
  const { ttsState, setIsEnabled: setTTSEnabled, isEnabled: isTTSEnabled, ttsConfig, updateTTSConfig, ttsService } = useTTS()
  const { sttState, sttConfig, updateSTTConfig } = useSTT()
  const { registerAction } = useHotkey()
  const [showSettings, setShowSettings] = useState(false)
  const [voices, setVoices] = useState<Array<{id: string, name: string}>>([])
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const messagesRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    const messagesContainer = messagesRef.current?.querySelector('.messages-container');
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }, [chatHandler.messages]);

  // Load voices when provider changes
  useEffect(() => {
    const loadVoices = async () => {
      try {
        console.log('Loading voices for provider:', ttsConfig.provider);
        const availableVoices = await ttsService.getVoices();
        console.log('Available voices:', availableVoices);
        setVoices(availableVoices.map(v => ({ id: v.id, name: v.name })));
      } catch (error) {
        console.error('Failed to load voices:', error);
        setVoices([]);
      }
    };

    if (isTTSEnabled) {
      loadVoices();
    }
  }, [ttsConfig.provider, isTTSEnabled, ttsService]);

  // Register all hotkey actions
  registerAction('focusInput', () => {
    inputRef.current?.focus();
  });

  registerAction('focusMessages', () => {
    messagesRef.current?.focus();
  });

  registerAction('scrollToBottom', () => {
    const messagesContainer = messagesRef.current?.querySelector('.messages-container');
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  });

  registerAction('scrollToTop', () => {
    const messagesContainer = messagesRef.current?.querySelector('.messages-container');
    if (messagesContainer) {
      messagesContainer.scrollTop = 0;
    }
  });

  registerAction('sendMessage', () => {
    if (chatHandler.input.trim()) {
      chatHandler.handleSubmit();
    }
  });

  registerAction('stopGeneration', () => {
    if (chatHandler.isLoading) {
      chatHandler.stop();
    }
  });

  registerAction('clearInput', () => {
    chatHandler.setInput('');
  });

  registerAction('toggleSTT', () => {
    chatHandler.handleSTTToggle();
  });

  // Add Ctrl+V handler for STT toggle
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'space') {
        e.preventDefault();
        chatHandler.handleSTTToggle();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [chatHandler.handleSTTToggle]);

  registerAction('newChat', () => {
    if (confirm('Are you sure you want to clear the chat history?')) {
      chatHandler.clearChat();
    }
  });

  registerAction('toggleSidebar', () => {
    setShowSettings(prev => !prev);
  });

  registerAction('toggleTTS', () => {
    setTTSEnabled(!isTTSEnabled);
  }, [isTTSEnabled]);


  // TTS Status indicator
  const getTTSIndicator = () => {
    switch (ttsState.status) {
      case 'playing':
        return <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />;
      case 'buffering':
      case 'rendering':
        return <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />;
      case 'error':
        return <div className="w-2 h-2 rounded-full bg-red-500" />;
      default:
        return <div className="w-2 h-2 rounded-full bg-gray-400" />;
    }
  };

  // STT Status indicator
  const getSTTIndicator = () => {
    switch (sttState.status) {
      case 'listening':
        return <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />;
      case 'processing':
        return <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />;
      case 'transcribed':
        return <div className="w-2 h-2 rounded-full bg-green-500" />;
      case 'error':
        return <div className="w-2 h-2 rounded-full bg-red-500" />;
      default:
        return <div className="w-2 h-2 rounded-full bg-gray-400" />;
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-background">
      {/* iPhone 13 sized container */}
      <div className="w-[390px] h-screen bg-background border-x shadow-xl relative flex flex-col">
        {/* Header with status indicators and settings */}
        <div className="flex items-center justify-between p-3 border-b bg-background">
          <div className="flex items-center gap-4">
            {/* TTS indicator */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">TTS</span>
              {getTTSIndicator()}
            </div>
            
            {/* STT indicator */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">STT</span>
              {getSTTIndicator()}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Settings toggle */}
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setShowSettings(!showSettings)}
              className="h-8 w-8"
              aria-label="Settings"
            >
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Main content area */}
        <div className="flex-1 relative overflow-hidden">
          {/* Settings Panel (slides in from right) */}
          <div
            className={cn(
              "absolute top-0 right-0 h-full w-full bg-background border-l shadow-lg z-10 transition-transform duration-300",
              showSettings ? "translate-x-0" : "translate-x-full"
            )}
          >
            <div className="p-4 space-y-4 overflow-y-auto h-full">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Settings</h3>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setShowSettings(false)}
                  className="h-8 w-8"
                >
                  ×
                </Button>
              </div>

              {/* TTS Settings */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">TTS</label>
                  <input
                    type="checkbox"
                    checked={isTTSEnabled}
                    onChange={(e) => setTTSEnabled(e.target.checked)}
                    className="rounded"
                  />
                </div>
                
                {isTTSEnabled && (
                  <div className="pl-4 space-y-3">
                    {/* Provider Selection */}
                    <div>
                      <label className="text-xs block mb-1">Provider</label>
                      <select
                        value={ttsConfig.provider}
                        onChange={(e) => updateTTSConfig({ provider: e.target.value })}
                        className="w-full px-2 py-1 text-xs border rounded bg-background"
                      >
                        <option value="browser">Browser TTS</option>
                        <option value="elevenlabs">ElevenLabs</option>
                        <option value="macos">macOS</option>
                      </select>
                    </div>


                    {/* Voice Selection */}
                    <div>
                      <label className="text-xs block mb-1">Voice</label>
                      <select
                        value={ttsConfig.voice || ''}
                        onChange={(e) => updateTTSConfig({ voice: e.target.value })}
                        className="w-full px-2 py-1 text-xs border rounded bg-background"
                      >
                        <option value="">Default Voice</option>
                        {voices.map(voice => (
                          <option key={voice.id} value={voice.id}>
                            {voice.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-xs">Rate: {ttsConfig.rate}x</label>
                      <input
                        type="range"
                        min="0.5"
                        max="2"
                        step="0.1"
                        value={ttsConfig.rate}
                        onChange={(e) => updateTTSConfig({ rate: parseFloat(e.target.value) })}
                        className="w-full h-1"
                      />
                    </div>
                    <div>
                      <label className="text-xs">Volume: {Math.round(ttsConfig.volume! * 100)}%</label>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={ttsConfig.volume}
                        onChange={(e) => updateTTSConfig({ volume: parseFloat(e.target.value) })}
                        className="w-full h-1"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* STT Settings */}
              <div className="space-y-2">
                <label className="text-sm font-medium">STT (Whisper AI)</label>
                <div className="pl-4 space-y-2">
                  <p className="text-xs text-muted-foreground">
                    Voice input uses Whisper AI running locally in your browser.
                    Text accumulates as you speak - click send when done.
                  </p>
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={sttConfig.interimResults}
                      onChange={(e) => updateSTTConfig({ interimResults: e.target.checked })}
                      className="rounded"
                    />
                    Show real-time transcription
                  </label>
                </div>
              </div>

              {/* Clear Chat */}
              <Button
                onClick={() => {
                  if (confirm('Clear chat history?')) {
                    chatHandler.clearChat()
                  }
                }}
                variant="outline"
                className="w-full"
                size="sm"
              >
                Clear Chat
              </Button>
            </div>
          </div>

          {/* Chat component */}
          <div ref={messagesRef} className="h-full">
            <Chat
              messages={chatHandler.messages}
              input={chatHandler.input}
              handleInputChange={chatHandler.handleInputChange}
              handleSubmit={chatHandler.handleSubmit}
              isGenerating={chatHandler.isLoading}
              stop={chatHandler.stop}
              sttState={sttState}
              onSTTToggle={chatHandler.handleSTTToggle}
              inputRef={inputRef}
            />
          </div>
        </div>
      </div>
      
      {/* STT Overlay */}
      <STTOverlay 
        sttState={sttState} 
        onStop={chatHandler.handleSTTToggle}
      />
    </div>
  )
}

export default ChatContainer