import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
import type { STTState } from '@/services/stt/types';

interface RecordingIndicatorProps {
  sttState: STTState;
}

export function RecordingIndicator({ sttState }: RecordingIndicatorProps) {
  const [volumeLevel, setVolumeLevel] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    if (sttState.status !== 'listening') {
      setIsAnalyzing(false);
      setVolumeLevel(0);
      return;
    }

    let audioContext: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let microphone: MediaStreamAudioSourceNode | null = null;
    let animationId: number | null = null;

    const startAudioAnalysis = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioContext = new AudioContext();
        analyser = audioContext.createAnalyser();
        microphone = audioContext.createMediaStreamSource(stream);
        
        analyser.fftSize = 256;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        microphone.connect(analyser);
        setIsAnalyzing(true);

        const updateVolume = () => {
          if (analyser) {
            analyser.getByteFrequencyData(dataArray);
            
            // Calculate average volume
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
              sum += dataArray[i];
            }
            const average = sum / bufferLength;
            const normalizedVolume = Math.min(100, (average / 128) * 100);
            
            setVolumeLevel(normalizedVolume);
          }
          
          animationId = requestAnimationFrame(updateVolume);
        };
        
        updateVolume();
      } catch (error) {
        console.error('Error accessing microphone for volume analysis:', error);
      }
    };

    startAudioAnalysis();

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
      if (audioContext) {
        audioContext.close();
      }
      setIsAnalyzing(false);
      setVolumeLevel(0);
    };
  }, [sttState.status]);

  if (sttState.status === 'idle') return null;

  return (
    <div className="fixed top-20 left-0 right-0 flex justify-center z-50 pointer-events-none">
      <div className={cn(
        "px-6 py-3 rounded-full shadow-lg backdrop-blur-md pointer-events-auto",
        "flex flex-col items-center gap-2 transition-all duration-300",
        sttState.status === 'listening' && "bg-red-500/90 text-white",
        sttState.status === 'processing' && "bg-blue-500/90 text-white",
        sttState.status === 'transcribed' && "bg-green-500/90 text-white",
        sttState.status === 'error' && "bg-red-600/90 text-white"
      )}>
        <div className="flex items-center gap-3">
          {/* Volume indicator bars */}
          {sttState.status === 'listening' && isAnalyzing && (
            <div className="flex items-center gap-1 h-6">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className={cn(
                    "w-1 bg-white rounded-full transition-all duration-100",
                    volumeLevel > i * 20 ? "opacity-100" : "opacity-30"
                  )}
                  style={{
                    height: volumeLevel > i * 20 
                      ? `${Math.min(24, 8 + (volumeLevel - i * 20) * 0.8)}px` 
                      : '4px'
                  }}
                />
              ))}
            </div>
          )}
          
          {/* Status text */}
          <div className="font-medium text-center">
            {sttState.status === 'listening' && 'Recording... (Press again to stop)'}
            {sttState.status === 'processing' && 'Processing speech...'}
            {sttState.status === 'transcribed' && 'Transcription complete'}
            {sttState.status === 'error' && `Error: ${sttState.error}`}
          </div>
        </div>

        {/* Interim transcript - separate row below */}
        {sttState.status === 'listening' && sttState.interimTranscript && (
          <div className="max-w-md text-sm opacity-80 text-center px-4">
            "{sttState.interimTranscript}"
          </div>
        )}
      </div>
    </div>
  );
}