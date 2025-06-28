import * as React from "react"
import { ChevronLeft, Settings, Volume2, Mic, Keyboard } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import type { Endpoint, Model } from "@/types/config"
import { ENDPOINTS } from "@/types/config"
import { useTTS } from "@/contexts/TTSContext"
import { useSTT } from "@/contexts/STTContext"
import { useHotkey } from "@/contexts/HotkeyContext"
import type { TTSVoice } from "@/services/tts/types"
import { getHotkeysByCategory } from "@/services/hotkeys/defaultHotkeys"

interface SidebarProps {
  selectedEndpoint: Endpoint
  handleEndpointChange: (endpoint: Endpoint) => void
  models: Model[]
  selectedModel: string
  handleModelChange: (modelId: string) => void
  loadingModels: boolean
  clearChat: () => void
  isOpen?: boolean
  setIsOpen?: (open: boolean) => void
}

export function Sidebar({
  selectedEndpoint,
  handleEndpointChange,
  models,
  selectedModel,
  handleModelChange,
  loadingModels,
  clearChat,
  isOpen: controlledIsOpen,
  setIsOpen: controlledSetIsOpen
}: SidebarProps) {
  const [internalIsOpen, setInternalIsOpen] = React.useState(false)
  const isOpen = controlledIsOpen ?? internalIsOpen
  const setIsOpen = controlledSetIsOpen ?? setInternalIsOpen
  const { ttsConfig, updateTTSConfig, isEnabled, setIsEnabled, ttsService } = useTTS()
  const { sttConfig, updateSTTConfig } = useSTT()
  const { hotkeyConfig, updateHotkey, resetHotkeys, setShowOverlay } = useHotkey()
  const [voices, setVoices] = React.useState<TTSVoice[]>([])
  const [editingHotkey, setEditingHotkey] = React.useState<string | null>(null)
  const [tempHotkey, setTempHotkey] = React.useState('')

  React.useEffect(() => {
    ttsService.getVoices().then(setVoices);
  }, [ttsService, ttsConfig.provider, ttsConfig.elevenLabsApiKey]);

  return (
    <>
      {/* Toggle Button */}
      <Button
        onClick={() => setIsOpen(true)}
        className={cn(
          "fixed left-0 top-1/2 -translate-y-1/2 z-40 rounded-l-none transition-transform",
          isOpen && "-translate-x-full"
        )}
        size="icon"
        variant="outline"
      >
        <Settings className="h-4 w-4" />
      </Button>

      {/* Sidebar */}
      <div
        className={cn(
          "fixed left-0 top-0 h-full w-80 bg-background border-r shadow-lg z-50 transition-transform duration-300 overflow-y-auto",
          !isOpen && "-translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-background">
          <h2 className="text-lg font-semibold">Settings</h2>
          <Button
            onClick={() => setIsOpen(false)}
            size="icon"
            variant="ghost"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-6">
          {/* Endpoint Selection */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Chat Configuration</h3>
            <div className="space-y-3">
              <div>
                <label htmlFor="sidebar-endpoint" className="text-sm font-medium mb-2 block">
                  Endpoint
                </label>
                <Select
                  id="sidebar-endpoint"
                  value={selectedEndpoint.name}
                  onChange={(e) => {
                    const endpoint = ENDPOINTS.find(ep => ep.name === e.target.value)
                    if (endpoint) handleEndpointChange(endpoint)
                  }}
                  className="w-full"
                >
                  {ENDPOINTS.map((endpoint) => (
                    <option key={endpoint.name} value={endpoint.name}>
                      {endpoint.name}
                    </option>
                  ))}
                </Select>
              </div>
              
              {/* Model Selection */}
              <div>
                <label htmlFor="sidebar-model" className="text-sm font-medium mb-2 block">
                  Model
                </label>
                <Select
                  id="sidebar-model"
                  value={selectedModel}
                  onChange={(e) => handleModelChange(e.target.value)}
                  disabled={loadingModels || models.length === 0}
                  className="w-full"
                >
                  {loadingModels ? (
                    <option>Loading models...</option>
                  ) : models.length === 0 ? (
                    <option>No models available</option>
                  ) : (
                    models.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.id}
                      </option>
                    ))
                  )}
                </Select>
              </div>
            </div>
          </div>

          {/* TTS Configuration */}
          <div className="border-t pt-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Volume2 className="h-4 w-4" />
                Text-to-Speech
              </h3>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={isEnabled}
                  onChange={(e) => setIsEnabled(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">Enabled</span>
              </label>
            </div>

            <div className="space-y-3">
              {/* Provider Selection */}
              <div>
                <label htmlFor="tts-provider" className="text-sm font-medium mb-2 block">
                  Provider
                </label>
                <Select
                  id="tts-provider"
                  value={ttsConfig.provider}
                  onChange={(e) => updateTTSConfig({ provider: e.target.value })}
                  className="w-full"
                  disabled={!isEnabled}
                >
                  <option value="browser">Browser (Built-in)</option>
                  <option value="elevenlabs">ElevenLabs</option>
                </Select>
              </div>

              {/* ElevenLabs API Key (only show when ElevenLabs is selected) */}
              {ttsConfig.provider === 'elevenlabs' && (
                <div>
                  <label htmlFor="elevenlabs-api-key" className="text-sm font-medium mb-2 block">
                    ElevenLabs API Key
                  </label>
                  <input
                    id="elevenlabs-api-key"
                    type="password"
                    value={ttsConfig.elevenLabsApiKey || 'sk_f84893b970e13c43c23063f92abbcbc760698537780b5bfd'}
                    onChange={(e) => updateTTSConfig({ elevenLabsApiKey: e.target.value })}
                    placeholder="Enter your API key"
                    className="w-full px-3 py-2 text-sm border rounded-md"
                    disabled={!isEnabled}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    ⚠️ API keys in browser apps are visible to users. Use with caution.
                  </p>
                </div>
              )}

              {/* Voice Selection */}
              <div>
                <label htmlFor="tts-voice" className="text-sm font-medium mb-2 block">
                  Voice
                </label>
                <Select
                  id="tts-voice"
                  value={ttsConfig.voice || ''}
                  onChange={(e) => updateTTSConfig({ voice: e.target.value })}
                  className="w-full"
                  disabled={!isEnabled}
                >
                  <option value="">Default</option>
                  {voices.map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.name} ({voice.lang})
                    </option>
                  ))}
                </Select>
              </div>

              {/* Rate */}
              <div>
                <label htmlFor="tts-rate" className="text-sm font-medium mb-2 block">
                  Speed: {ttsConfig.rate}x
                </label>
                <input
                  id="tts-rate"
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={ttsConfig.rate}
                  onChange={(e) => updateTTSConfig({ rate: parseFloat(e.target.value) })}
                  className="w-full"
                  disabled={!isEnabled}
                />
              </div>

              {/* Pitch */}
              <div>
                <label htmlFor="tts-pitch" className="text-sm font-medium mb-2 block">
                  Pitch: {ttsConfig.pitch}
                </label>
                <input
                  id="tts-pitch"
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={ttsConfig.pitch}
                  onChange={(e) => updateTTSConfig({ pitch: parseFloat(e.target.value) })}
                  className="w-full"
                  disabled={!isEnabled}
                />
              </div>

              {/* Volume */}
              <div>
                <label htmlFor="tts-volume" className="text-sm font-medium mb-2 block">
                  Volume: {Math.round(ttsConfig.volume! * 100)}%
                </label>
                <input
                  id="tts-volume"
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={ttsConfig.volume}
                  onChange={(e) => updateTTSConfig({ volume: parseFloat(e.target.value) })}
                  className="w-full"
                  disabled={!isEnabled}
                />
              </div>
            </div>
          </div>

          {/* STT Configuration */}
          <div className="border-t pt-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Mic className="h-4 w-4" />
                Speech-to-Text
              </h3>
            </div>

            <div className="space-y-3">
              {/* Provider Selection */}
              <div>
                <label htmlFor="stt-provider" className="text-sm font-medium mb-2 block">
                  Provider
                </label>
                <Select
                  id="stt-provider"
                  value={sttConfig.provider}
                  onChange={(e) => updateSTTConfig({ provider: e.target.value })}
                  className="w-full"
                >
                  <option value="browser">Browser (Built-in)</option>
                  <option value="whisper">Whisper (Experimental)</option>
                </Select>
              </div>

              {/* Language Selection */}
              <div>
                <label htmlFor="stt-language" className="text-sm font-medium mb-2 block">
                  Language
                </label>
                <Select
                  id="stt-language"
                  value={sttConfig.language}
                  onChange={(e) => updateSTTConfig({ language: e.target.value })}
                  className="w-full"
                >
                  <option value="en-US">English (US)</option>
                  <option value="en-GB">English (UK)</option>
                  <option value="es-ES">Spanish</option>
                  <option value="fr-FR">French</option>
                  <option value="de-DE">German</option>
                  <option value="it-IT">Italian</option>
                  <option value="pt-BR">Portuguese (Brazil)</option>
                  <option value="ja-JP">Japanese</option>
                  <option value="ko-KR">Korean</option>
                  <option value="zh-CN">Chinese (Simplified)</option>
                </Select>
              </div>

              {/* Auto-submit */}
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={sttConfig.autoSubmit}
                    onChange={(e) => updateSTTConfig({ autoSubmit: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm">Auto-submit on transcription</span>
                </label>
                <p className="text-xs text-muted-foreground mt-1">
                  Automatically send message when speech is transcribed
                </p>
              </div>

              {/* Interim Results */}
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={sttConfig.interimResults}
                    onChange={(e) => updateSTTConfig({ interimResults: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm">Show interim results</span>
                </label>
                <p className="text-xs text-muted-foreground mt-1">
                  Display partial transcription while speaking
                </p>
              </div>
            </div>
          </div>

          {/* Hotkey Configuration */}
          <div className="border-t pt-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Keyboard className="h-4 w-4" />
                Keyboard Shortcuts
              </h3>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowOverlay(true)}
                >
                  View All
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    if (confirm('Reset all hotkeys to defaults?')) {
                      resetHotkeys();
                    }
                  }}
                >
                  Reset
                </Button>
              </div>
            </div>

            <div className="space-y-4 max-h-60 overflow-y-auto">
              {getHotkeysByCategory().map(category => (
                <div key={category.name}>
                  <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                    {category.name}
                  </h4>
                  <div className="space-y-1">
                    {category.actions.map(action => {
                      const isEditing = editingHotkey === action.id;
                      const currentKeys = hotkeyConfig[action.id] || action.defaultKeys;
                      
                      return (
                        <div
                          key={action.id}
                          className="flex items-center justify-between p-1.5 rounded hover:bg-muted/50 text-sm"
                        >
                          <span className="text-xs truncate flex-1">{action.name}</span>
                          {isEditing ? (
                            <div className="flex items-center gap-1">
                              <input
                                type="text"
                                value={tempHotkey}
                                onChange={(e) => setTempHotkey(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    updateHotkey(action.id, tempHotkey);
                                    setEditingHotkey(null);
                                  } else if (e.key === 'Escape') {
                                    setEditingHotkey(null);
                                  }
                                }}
                                className="w-24 px-1 py-0.5 text-xs border rounded"
                                placeholder="e.g. cmd+k"
                                autoFocus
                              />
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 px-1"
                                onClick={() => {
                                  updateHotkey(action.id, tempHotkey);
                                  setEditingHotkey(null);
                                }}
                              >
                                ✓
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 px-1"
                                onClick={() => setEditingHotkey(null)}
                              >
                                ✕
                              </Button>
                            </div>
                          ) : (
                            <button
                              onClick={() => {
                                setEditingHotkey(action.id);
                                setTempHotkey(currentKeys);
                              }}
                              className="px-2 py-0.5 text-xs font-mono bg-muted rounded hover:bg-muted/70"
                            >
                              {currentKeys.split(',')[0].trim()}
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="pt-4 border-t">
            <Button
              onClick={() => {
                if (confirm('Are you sure you want to clear the chat history?')) {
                  clearChat()
                }
              }}
              variant="outline"
              className="w-full"
            >
              Clear Chat History
            </Button>
          </div>
        </div>
      </div>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}