import React from 'react';
import { Mic, MicOff } from 'lucide-react';
import type { STTState } from '@/services/stt/types';

interface STTOverlayProps {
  sttState: STTState;
  onStop: () => void;
}

export function STTOverlay({ sttState, onStop }: STTOverlayProps) {
  if (sttState.status !== 'listening' && sttState.status !== 'processing') {
    return null;
  }

  const isProcessing = sttState.status === 'processing';
  const transcript = sttState.interimTranscript || '';

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center">
      <div className="flex flex-col items-center gap-8 p-8 max-w-2xl w-full">
        {/* Transcript Display */}
        <div className="min-h-[200px] flex items-center justify-center">
          {transcript ? (
            <p className="text-white text-2xl md:text-3xl text-center leading-relaxed animate-fade-in">
              {transcript}
            </p>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-red-500 rounded-full animate-ping opacity-75" />
                <Mic className="relative w-12 h-12 text-white" />
              </div>
              <p className="text-white/60 text-lg">Listening...</p>
            </div>
          )}
        </div>

        {/* Stop Button */}
        <button
          onClick={onStop}
          disabled={isProcessing}
          className="relative group"
        >
          <div className="absolute inset-0 bg-red-600 rounded-full blur-xl group-hover:blur-2xl transition-all opacity-50" />
          <div className="relative bg-red-600 hover:bg-red-700 disabled:bg-red-800 disabled:opacity-50 text-white rounded-full p-8 transition-all transform hover:scale-105 active:scale-95 disabled:scale-100">
            {isProcessing ? (
              <div className="w-16 h-16 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white" />
              </div>
            ) : (
              <MicOff className="w-16 h-16" />
            )}
          </div>
        </button>

        {/* Status Text */}
        <p className="text-white/60 text-sm">
          {isProcessing ? 'Processing...' : 'Tap to stop and send'}
        </p>
      </div>
    </div>
  );
}