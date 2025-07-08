import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ChatContainer from './Chat'
import { TTSProvider } from './contexts/TTSContext'
import { STTProvider } from './contexts/STTContext'
import { HotkeyProvider } from './contexts/HotkeyContext'
import { HotkeyOverlay } from './components/ui/hotkey-overlay'
import { HotkeyFlashModal } from './components/ui/hotkey-flash'

function App() {
  return (
    <Router>
      <Routes>
        <Route
          path="/*"
          element={
            <HotkeyProvider>
              <TTSProvider>
                <STTProvider>
                  <ChatContainer />
                  <HotkeyOverlay />
                  <HotkeyFlashModal />
                </STTProvider>
              </TTSProvider>
            </HotkeyProvider>
          }
        />
      </Routes>
    </Router>
  )
}

export default App