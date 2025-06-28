import { cn } from "@/lib/utils"
import type { TTSState } from "@/services/tts/types"
import type { STTState } from "@/services/stt/types"

interface ActivityStatusBarProps {
  ttsState: TTSState
  sttState: STTState
}

const getTTSStatusInfo = (state: TTSState): { color: string; text: string; bgClass: string } => {
  switch (state.status) {
    case 'waiting':
      return { color: 'grey', text: 'Waiting', bgClass: 'bg-gray-500' };
    case 'buffering':
      return { color: 'cyan', text: 'Buffering', bgClass: 'bg-cyan-500' };
    case 'rendering':
      return { color: 'yellow', text: 'Rendering', bgClass: 'bg-yellow-500' };
    case 'playing':
      return { color: 'green', text: 'Playing', bgClass: 'bg-green-500' };
    case 'error':
      return { color: 'red', text: 'Error', bgClass: 'bg-red-500' };
    default:
      return { color: 'grey', text: 'Unknown', bgClass: 'bg-gray-500' };
  }
};

const getSTTStatusInfo = (state: STTState): { color: string; text: string; bgClass: string } => {
  switch (state.status) {
    case 'idle':
      return { color: 'grey', text: 'Idle', bgClass: 'bg-gray-500' };
    case 'listening':
      return { color: 'red', text: 'Listening', bgClass: 'bg-red-500' };
    case 'processing':
      return { color: 'yellow', text: 'Processing', bgClass: 'bg-yellow-500' };
    case 'transcribed':
      return { color: 'green', text: 'Transcribed', bgClass: 'bg-green-500' };
    case 'error':
      return { color: 'red', text: 'Error', bgClass: 'bg-red-500' };
    default:
      return { color: 'grey', text: 'Unknown', bgClass: 'bg-gray-500' };
  }
};

export function ActivityStatusBar({ ttsState, sttState }: ActivityStatusBarProps) {
  const ttsInfo = getTTSStatusInfo(ttsState);
  const sttInfo = getSTTStatusInfo(sttState);

  return (
    <div className="w-full bg-background border-b px-4 py-2">
      <div className="flex items-center gap-6">
        {/* TTS Status */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">TTS:</span>
          <div className="flex items-center gap-2">
            <div className={cn(
              "w-2 h-2 rounded-full",
              ttsState.status === 'playing' && "animate-pulse",
              ttsInfo.bgClass
            )} />
            <span className={cn(
              "text-xs font-medium uppercase",
              ttsState.status === 'error' ? 'text-red-600' : 'text-foreground'
            )}>
              {ttsInfo.text}
            </span>
          </div>
        </div>

        {/* STT Status */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">STT:</span>
          <div className="flex items-center gap-2">
            <div className={cn(
              "w-2 h-2 rounded-full",
              sttState.status === 'listening' && "animate-pulse",
              sttInfo.bgClass
            )} />
            <span className={cn(
              "text-xs font-medium uppercase",
              sttState.status === 'error' ? 'text-red-600' : 'text-foreground'
            )}>
              {sttInfo.text}
            </span>
          </div>
        </div>
        
        {/* Show additional info for certain states */}
        {ttsState.status === 'error' && (
          <span className="text-xs text-red-600 truncate max-w-md">
            TTS: {ttsState.error}
          </span>
        )}
        
        {sttState.status === 'error' && (
          <span className="text-xs text-red-600 truncate max-w-md">
            STT: {sttState.error}
          </span>
        )}
      </div>
    </div>
  )
}