import ChatContainer from './Chat'
import { TTSProvider } from './contexts/TTSContext'
import { STTProvider } from './contexts/STTContext'
import { HotkeyProvider } from './contexts/HotkeyContext'
import { HotkeyOverlay } from './components/ui/hotkey-overlay'
import { HotkeyFlashModal } from './components/ui/hotkey-flash'

function App() {
  return (
    <HotkeyProvider>
      <TTSProvider>
        <STTProvider>
          <ChatContainer />
          <HotkeyOverlay />
          <HotkeyFlashModal />
        </STTProvider>
      </TTSProvider>
    </HotkeyProvider>
  )
}

export default App