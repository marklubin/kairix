import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { Mic } from 'lucide-react';
import type { STTState } from '@/services/stt/types';

interface STTOverlayProps {
  sttState: STTState;
  onStop: () => void;
}

export function STTOverlay({ sttState, onStop }: STTOverlayProps) {
  const [volumeLevel, setVolumeLevel] = useState(0);

  useEffect(() => {
    if (sttState.status !== 'listening') {
      setVolumeLevel(0);
      return;
    }

    let audioContext: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let microphone: MediaStreamAudioSourceNode | null = null;
    let animationId: number | null = null;
    let stream: MediaStream | null = null;

    const startAudioAnalysis = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioContext = new AudioContext();
        analyser = audioContext.createAnalyser();
        microphone = audioContext.createMediaStreamSource(stream);
        
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.3;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        microphone.connect(analyser);

        const updateVolume = () => {
          if (analyser) {
            analyser.getByteFrequencyData(dataArray);
            
            // Calculate average volume
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
              sum += dataArray[i];
            }
            const average = sum / bufferLength;
            const normalizedVolume = Math.min(100, (average / 50) * 100);
            
            setVolumeLevel(normalizedVolume);
          }
          
          animationId = requestAnimationFrame(updateVolume);
        };
        
        updateVolume();
      } catch (error) {
        console.error('Error accessing microphone:', error);
      }
    };

    startAudioAnalysis();

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      if (audioContext && audioContext.state !== 'closed') {
        audioContext.close();
      }
    };
  }, [sttState.status]);

  if (sttState.status !== 'listening' && sttState.status !== 'processing') {
    return null;
  }

  const pulseScale = 1 + (volumeLevel / 100) * 0.3;

  return (
    <>
      <div data-testid="stt-overlay" className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center">
        <div className="text-center">
          {/* Big red button */}
          <button
            onClick={onStop}
            disabled={sttState.status === 'processing'}
            className={cn(
              "relative w-32 h-32 rounded-full bg-red-500 hover:bg-red-600",
              "flex items-center justify-center transition-all duration-150",
              "shadow-2xl hover:shadow-red-500/50",
              sttState.status === 'processing' && "opacity-50 cursor-not-allowed"
            )}
            style={{
              transform: `scale(${sttState.status === 'listening' ? pulseScale : 1})`,
            }}
          >
            {/* Outer ring animation */}
            {sttState.status === 'listening' && (
              <>
                <div className="absolute inset-0 rounded-full bg-red-400 animate-ping" />
                <div 
                  className="absolute inset-0 rounded-full bg-red-400 opacity-30"
                  style={{
                    transform: `scale(${1 + volumeLevel / 200})`,
                    transition: 'transform 0.1s ease-out'
                  }}
                />
              </>
            )}
            
            {/* Icon */}
            <Mic className="w-12 h-12 text-white relative z-10" />
          </button>

          {/* Status text */}
          <div className="mt-8 space-y-2">
            <p className="text-white text-xl font-medium">
              {sttState.status === 'listening' ? 'Listening...' : 'Processing...'}
            </p>
            <p className="text-white/70 text-sm">
              {sttState.status === 'listening' ? 'Click to stop recording' : 'Please wait...'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Interim transcript on separate layer */}
      {sttState.status === 'listening' && sttState.interimTranscript && (
        <div className="fixed bottom-20 left-1/2 transform -translate-x-1/2 z-[100] pointer-events-none">
          <div className="bg-black/90 backdrop-blur-sm rounded-lg px-6 py-3 max-w-2xl">
            <p className="text-white/80 text-base">
              {sttState.interimTranscript}
            </p>
          </div>
        </div>
      )}
    </>
  );
}