import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface VolumeIndicatorProps {
  className?: string;
}

export function VolumeIndicator({ className }: VolumeIndicatorProps) {
  const [volumeLevel, setVolumeLevel] = useState(0);

  useEffect(() => {
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
        analyser.smoothingTimeConstant = 0.8;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        microphone.connect(analyser);

        const updateVolume = () => {
          if (analyser) {
            analyser.getByteFrequencyData(dataArray);
            
            // Calculate average volume with emphasis on voice frequencies
            let sum = 0;
            const startBin = Math.floor(80 * bufferLength / (audioContext?.sampleRate || 44100) * 2);
            const endBin = Math.floor(1000 * bufferLength / (audioContext?.sampleRate || 44100) * 2);
            
            for (let i = startBin; i < endBin && i < bufferLength; i++) {
              sum += dataArray[i];
            }
            const average = sum / (endBin - startBin);
            const normalizedVolume = Math.min(100, (average / 100) * 100);
            
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
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      if (audioContext && audioContext.state !== 'closed') {
        audioContext.close();
      }
      setVolumeLevel(0);
    };
  }, []);

  return (
    <div data-testid="volume-indicator" className={cn("flex items-center gap-0.5", className)}>
      {[...Array(4)].map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-0.5 bg-red-500 rounded-full transition-all duration-75",
            volumeLevel > i * 25 ? "opacity-100" : "opacity-30"
          )}
          style={{
            height: volumeLevel > i * 25 
              ? `${Math.min(16, 4 + (volumeLevel - i * 25) * 0.48)}px` 
              : '2px'
          }}
        />
      ))}
    </div>
  );
}