import React, { useState } from 'react';
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
  let transcript: string = '';
  if (sttState.status === "listening") {
    transcript = sttState.interimTranscript || '';
  }

  return (
    <div 
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center"
      onTouchStart={(e) => {
        // Prevent any touch events from bubbling up on mobile
        if (/Mobile|Android|iPhone|iPad/i.test(navigator.userAgent)) {
          e.stopPropagation();
        }
      }}
    >
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
                <div className="absolute inset-0 bg-red-500 rounded-full animate-pulse" />
                <Mic className="relative w-12 h-12 text-white animate-pulse" />
              </div>
              <p className="text-white text-lg font-medium">Recording...</p>
              <p className="text-white/60 text-sm">Speak now</p>
            </div>
          )}
        </div>

        {/* Stop Button */}
        <button
          onClick={(e) => {
            e.preventDefault();
            if (!isProcessing) {
              onStop();
            }
          }}
          onTouchEnd={(e) => {
            e.preventDefault();
            e.stopPropagation();
            if (!isProcessing) {
              onStop();
            }
          }}
          disabled={isProcessing}
          className="relative group touch-none select-none"
          style={{ WebkitTouchCallout: 'none', WebkitUserSelect: 'none' }}
        >
          <div className="absolute inset-0 bg-red-600 rounded-full blur-xl transition-all group-hover:blur-2xl opacity-50" />
          <div className="relative bg-red-600 hover:bg-red-700 active:scale-95 disabled:bg-red-800 disabled:opacity-50 text-white rounded-full p-8 transition-all transform hover:scale-105 disabled:scale-100">
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