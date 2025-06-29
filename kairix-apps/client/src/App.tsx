import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ChatContainer from './Chat'
import { TTSProvider } from './contexts/TTSContext'
import { STTProvider } from './contexts/STTContext'
import { HotkeyProvider } from './contexts/HotkeyContext'
import { HotkeyOverlay } from './components/ui/hotkey-overlay'
import { HotkeyFlashModal } from './components/ui/hotkey-flash'
import { Auth } from './components/Auth'
import { ProtectedRoute } from './components/ProtectedRoute'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/auth" element={<Auth />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <HotkeyProvider>
                <TTSProvider>
                  <STTProvider>
                    <ChatContainer />
                    <HotkeyOverlay />
                    <HotkeyFlashModal />
                  </STTProvider>
                </TTSProvider>
              </HotkeyProvider>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  )
}

export default App