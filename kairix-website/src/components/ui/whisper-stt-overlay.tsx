import React, { useState, useEffect } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import type { STTState } from '@/services/stt/types';

interface WhisperSTTOverlayProps {
  sttState: STTState;
  onStop: () => void;
}

export function WhisperSTTOverlay({ sttState, onStop }: WhisperSTTOverlayProps) {
  const [modelLoaded, setModelLoaded] = useState(false);
  const [waveform, setWaveform] = useState<number[]>(Array(20).fill(0));
  
  useEffect(() => {
    if (sttState.status === 'listening' || sttState.status === 'processing') {
      // Simulate model loading
      const timer = setTimeout(() => setModelLoaded(true), 2000);
      return () => clearTimeout(timer);
    } else {
      setModelLoaded(false);
    }
  }, [sttState.status]);
  
  useEffect(() => {
    if (modelLoaded && sttState.status === 'listening') {
      const interval = setInterval(() => {
        setWaveform(prev => prev.map(() => Math.random() * 40 + 10));
      }, 100);
      return () => clearInterval(interval);
    }
  }, [modelLoaded, sttState.status]);

  if (sttState.status !== 'listening' && sttState.status !== 'processing') {
    return null;
  }

  const isProcessing = sttState.status === 'processing';
  const isDesktop = !/Mobile|Android|iPhone|iPad/i.test(navigator.userAgent);
  
  // Show accumulated transcript from Whisper
  const transcript = sttState.status === 'listening' ? sttState.interimTranscript || '' : '';

  return (
    <div className="fixed inset-0 z-50 bg-gradient-to-b from-black/90 to-black/95 backdrop-blur-sm flex items-center justify-center">
      <div className="flex flex-col items-center gap-6 p-8 max-w-4xl w-full">
        {/* Title */}
        <div className="text-center">
          <h2 className="text-white text-2xl font-light mb-2">
            {!modelLoaded ? 'Loading Whisper AI...' : 
             isProcessing ? 'Processing...' : 'Listening...'}
          </h2>
          <p className="text-white/60 text-sm">
            {!modelLoaded ? 'Preparing speech recognition...' : 
             isProcessing ? 'Converting speech to text...' : 
             isDesktop ? 'Click stop when done speaking' : 'Tap stop when you\'re done speaking'}
          </p>
        </div>

        {/* Transcript or Waveform */}
        <div className="min-h-[200px] w-full flex items-center justify-center px-4">
          {!modelLoaded ? (
            <div className="flex items-center gap-3">
              <Loader2 className="w-6 h-6 text-white animate-spin" />
              <span className="text-white/60">Initializing local AI model...</span>
            </div>
          ) : transcript ? (
            <div className="bg-white/5 rounded-lg p-6 max-h-[300px] overflow-y-auto w-full">
              <p className="text-white text-lg leading-relaxed animate-fade-in">
                {transcript}
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4 w-full">
              {/* Waveform visualization */}
              <div className="flex items-center justify-center gap-1 h-16">
                {waveform.map((height, i) => (
                  <div
                    key={i}
                    className="w-1 bg-white/40 rounded-full transition-all duration-100"
                    style={{ height: `${height}px` }}
                  />
                ))}
              </div>
              <p className="text-white/40 text-sm animate-pulse">
                Start speaking...
              </p>
            </div>
          )}
        </div>

        {/* Stop Button */}
        {modelLoaded && (
          <button
            onClick={onStop}
            disabled={isProcessing}
            className="group relative touch-manipulation"
            style={{ WebkitTapHighlightColor: 'transparent' }}
          >
            <div className="absolute inset-0 bg-red-600 rounded-full blur-xl group-hover:blur-2xl opacity-50 transition-all" />
            <div className="relative bg-red-600 hover:bg-red-700 disabled:bg-red-800 disabled:opacity-50 text-white rounded-full px-8 py-4 transition-all transform hover:scale-105 disabled:scale-100 flex items-center gap-3">
              {isProcessing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span className="font-medium">Processing...</span>
                </>
              ) : (
                <>
                  <MicOff className="w-5 h-5" />
                  <span className="font-medium">Stop Recording</span>
                </>
              )}
            </div>
          </button>
        )}

        {/* Status */}
        <div className="text-center">
          <p className="text-white/40 text-xs">
            Powered by Whisper AI
          </p>
          <p className="text-white/30 text-xs mt-1">
            All processing happens locally in your browser
          </p>
        </div>
      </div>
    </div>
  );
}