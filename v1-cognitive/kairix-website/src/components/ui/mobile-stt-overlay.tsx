import React, { useState, useEffect } from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';
import type { STTState } from '@/services/stt/types';

interface MobileSTTOverlayProps {
  sttState: STTState;
  onStop: () => void;
}

export function MobileSTTOverlay({ sttState, onStop }: MobileSTTOverlayProps) {
  const [modelLoading, setModelLoading] = useState(true);
  const [waveformData, setWaveformData] = useState<number[]>(new Array(20).fill(0));
  
  useEffect(() => {
    // Simulate model loading for 2 seconds
    const timer = setTimeout(() => setModelLoading(false), 2000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    // Animate waveform when listening
    if (sttState.status === 'listening' && !modelLoading) {
      const interval = setInterval(() => {
        setWaveformData(prev => 
          prev.map(() => Math.random() * 40 + 10)
        );
      }, 100);
      return () => clearInterval(interval);
    }
  }, [sttState.status, modelLoading]);
  
  if (sttState.status !== 'listening' && sttState.status !== 'processing') {
    return null;
  }

  const isProcessing = sttState.status === 'processing';
  const transcript = sttState.status === "listening" ? sttState.interimTranscript || '' : '';

  return (
    <div className="fixed inset-0 z-50 bg-gradient-to-b from-black/90 to-black/95 backdrop-blur-md flex flex-col">
      {/* Header */}
      <div className="p-4 text-center">
        <h2 className="text-white/80 text-lg font-medium">
          {modelLoading ? 'Loading Whisper AI...' : 'Listening...'}
        </h2>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col items-center justify-center px-6">
        {modelLoading ? (
          <div className="flex flex-col items-center gap-4">
            <div className="relative">
              <Loader2 className="w-16 h-16 text-white/60 animate-spin" />
            </div>
            <p className="text-white/60 text-sm">Preparing speech recognition...</p>
          </div>
        ) : (
          <>
            {/* Waveform Visualization */}
            <div className="flex items-center justify-center gap-1 h-20 mb-8">
              {waveformData.map((height, i) => (
                <div
                  key={i}
                  className="w-1 bg-gradient-to-t from-blue-500 to-purple-500 rounded-full transition-all duration-150"
                  style={{ height: `${height}px` }}
                />
              ))}
            </div>

            {/* Transcript Display */}
            <div className="min-h-[120px] max-h-[200px] overflow-y-auto mb-8 w-full">
              {transcript ? (
                <p className="text-white text-xl leading-relaxed text-center px-4">
                  {transcript}
                </p>
              ) : (
                <p className="text-white/40 text-lg text-center">
                  Start speaking...
                </p>
              )}
            </div>
          </>
        )}
      </div>

      {/* Bottom Controls */}
      <div className="p-6 pb-8 flex flex-col items-center gap-4">
        {!modelLoading && (
          <>
            {/* Stop Button */}
            <button
              onTouchEnd={(e) => {
                e.preventDefault();
                onStop();
              }}
              disabled={isProcessing}
              className="relative group"
            >
              <div className="absolute inset-0 bg-red-600 rounded-2xl blur-2xl opacity-40 group-active:opacity-60 transition-opacity" />
              <div className={`relative bg-red-600 active:bg-red-700 disabled:bg-red-800 disabled:opacity-50 text-white rounded-2xl px-8 py-4 transition-all transform active:scale-95 disabled:scale-100 flex items-center gap-3`}>
                {isProcessing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span className="font-medium">Processing...</span>
                  </>
                ) : (
                  <>
                    <Square className="w-5 h-5 fill-current" />
                    <span className="font-medium">Stop Recording</span>
                  </>
                )}
              </div>
            </button>

            {/* Status Text */}
            <p className="text-white/50 text-sm">
              {isProcessing ? 
                'Converting speech to text...' : 
                'Tap stop when you\'re done speaking'
              }
            </p>
          </>
        )}
      </div>

      {/* Powered by Whisper */}
      <div className="absolute bottom-2 right-2 text-white/30 text-xs">
        Powered by Whisper AI
      </div>
    </div>
  );
}