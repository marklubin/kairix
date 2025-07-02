import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ChatContainer from './Chat'
import { TTSProvider } from './contexts/TTSContext'
import { STTProvider } from './contexts/STTContext'
import { HotkeyProvider } from './contexts/HotkeyContext'
import { HotkeyOverlay } from './components/ui/hotkey-overlay'
import { HotkeyFlashModal } from './components/ui/hotkey-flash'
import { Auth } from './components/Auth'
import { ProtectedRoute } from './components/ProtectedRoute'
import { SensorPanel } from './components/ui/sensor-panel'
import { ContextStatus } from './components/ui/context-status'
import { AdminPanel } from './components/AdminPanel'

function AppContent() {
  return (
    <>
      <ChatContainer />
      <HotkeyOverlay />
      <HotkeyFlashModal />
      
      {/* Context status - hidden on right side */}
      <ContextStatus />
      
      {/* Sensor streaming panel - slide-out toggle on bottom right */}
      <SensorPanel />
    </>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/auth" element={<Auth />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminPanel />
            </ProtectedRoute>
          }
        />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <HotkeyProvider>
                <TTSProvider>
                  <STTProvider>
                    <AppContent />
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