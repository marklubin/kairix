import { Chat } from "@/components/ui/chat"
import { Sidebar } from "@/components/ui/sidebar"
import { ActivityStatusBar } from "@/components/ui/activity-status-bar"
import { STTOverlay } from "@/components/ui/stt-overlay"
import { useCustomChat } from "./useCustomChat"
import { useTTS } from "./contexts/TTSContext"
import { useSTT } from "./contexts/STTContext"
import { useHotkey } from "./contexts/HotkeyContext"
import { useRef, useState } from "react"

function ChatContainer() {
  const chatHandler = useCustomChat()
  const { ttsState, setIsEnabled: setTTSEnabled, isEnabled: isTTSEnabled } = useTTS()
  const { sttState } = useSTT()
  const { registerAction } = useHotkey()
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const messagesRef = useRef<HTMLDivElement>(null)

  // Register all hotkey actions
  registerAction('focusInput', () => {
    inputRef.current?.focus();
  });

  registerAction('focusMessages', () => {
    messagesRef.current?.focus();
  });

  registerAction('scrollToBottom', () => {
    const messagesContainer = messagesRef.current?.querySelector('.overflow-y-auto');
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  });

  registerAction('scrollToTop', () => {
    const messagesContainer = messagesRef.current?.querySelector('.overflow-y-auto');
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

  registerAction('newChat', () => {
    if (confirm('Are you sure you want to clear the chat history?')) {
      chatHandler.clearChat();
    }
  });

  registerAction('toggleSidebar', () => {
    setIsSidebarOpen(prev => !prev);
  });

  registerAction('toggleTTS', () => {
    setTTSEnabled(!isTTSEnabled);
  }, [isTTSEnabled]);

  registerAction('nextModel', () => {
    const currentIndex = chatHandler.models.findIndex(m => m.id === chatHandler.selectedModel);
    if (currentIndex < chatHandler.models.length - 1) {
      chatHandler.handleModelChange(chatHandler.models[currentIndex + 1].id);
    }
  });

  registerAction('previousModel', () => {
    const currentIndex = chatHandler.models.findIndex(m => m.id === chatHandler.selectedModel);
    if (currentIndex > 0) {
      chatHandler.handleModelChange(chatHandler.models[currentIndex - 1].id);
    }
  });

  return (
    <div className="h-screen w-full relative flex flex-col">
      <ActivityStatusBar ttsState={ttsState} sttState={sttState} />
      <STTOverlay sttState={sttState} onStop={chatHandler.handleSTTToggle} />
      <div className="flex-1 relative">
        <Sidebar
          selectedEndpoint={chatHandler.selectedEndpoint}
          handleEndpointChange={chatHandler.handleEndpointChange}
          models={chatHandler.models}
          selectedModel={chatHandler.selectedModel}
          handleModelChange={chatHandler.handleModelChange}
          loadingModels={chatHandler.loadingModels}
          clearChat={chatHandler.clearChat}
          isOpen={isSidebarOpen}
          setIsOpen={setIsSidebarOpen}
        />
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
  )
}

export default ChatContainer