import React, { useState } from 'react';
import { Mic, MicOff } from 'lucide-react';
import type { STTState } from '@/services/stt/types';

interface STTOverlayProps {
  sttState: STTState;
  onStop: () => void;
}

export function STTOverlay({ sttState, onStop }: STTOverlayProps) {
  const [isHolding, setIsHolding] = useState(false);
  const [holdProgress, setHoldProgress] = useState(0);
  
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
                <Mic className="relative w-12 h-12 text-white" />
              </div>
              <p className="text-white/60 text-lg">Listening...</p>
            </div>
          )}
        </div>

        {/* Stop Button */}
        <button
          onMouseDown={(e) => {
            // For desktop, stop on click
            if (!/Mobile|Android|iPhone|iPad/i.test(navigator.userAgent)) {
              onStop();
            }
          }}
          onTouchStart={(e) => {
            e.preventDefault(); // Prevent any default touch behavior
            setIsHolding(true);
            setHoldProgress(0);
            const startTime = Date.now();
            
            // Progress animation
            const progressInterval = setInterval(() => {
              const elapsed = Date.now() - startTime;
              const progress = Math.min((elapsed / 500) * 100, 100);
              setHoldProgress(progress);
              if (progress >= 100) {
                clearInterval(progressInterval);
              }
            }, 10);
            
            const touchStartHandler = () => {
              const holdTime = Date.now() - startTime;
              if (holdTime >= 500) { // 500ms long press
                onStop();
                setIsHolding(false);
                setHoldProgress(0);
              }
            };
            
            const touchEndHandler = () => {
              document.removeEventListener('touchend', touchEndHandler);
              clearTimeout(timeoutId);
              clearInterval(progressInterval);
              setIsHolding(false);
              setHoldProgress(0);
            };
            
            const timeoutId = setTimeout(touchStartHandler, 500);
            document.addEventListener('touchend', touchEndHandler, { once: true });
          }}
          disabled={isProcessing}
          className="relative group touch-none select-none"
          style={{ WebkitTouchCallout: 'none', WebkitUserSelect: 'none' }}
        >
          {/* Progress ring for mobile long press */}
          {isHolding && /Mobile|Android|iPhone|iPad/i.test(navigator.userAgent) && (
            <svg className="absolute inset-0 w-full h-full -rotate-90 pointer-events-none">
              <circle
                cx="50%"
                cy="50%"
                r="48%"
                fill="none"
                stroke="rgba(255,255,255,0.3)"
                strokeWidth="4"
              />
              <circle
                cx="50%"
                cy="50%"
                r="48%"
                fill="none"
                stroke="white"
                strokeWidth="4"
                strokeDasharray={`${2 * Math.PI * 48} ${2 * Math.PI * 48}`}
                strokeDashoffset={2 * Math.PI * 48 * (1 - holdProgress / 100)}
                className="transition-all duration-100"
              />
            </svg>
          )}
          <div className={`absolute inset-0 bg-red-600 rounded-full blur-xl transition-all ${isHolding ? 'blur-3xl opacity-75' : 'group-hover:blur-2xl opacity-50'}`} />
          <div className={`relative bg-red-600 hover:bg-red-700 disabled:bg-red-800 disabled:opacity-50 text-white rounded-full p-8 transition-all transform hover:scale-105 disabled:scale-100 ${isHolding ? 'scale-95' : ''}`}>
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
          {isProcessing ? 'Processing...' : 
            /Mobile|Android|iPhone|iPad/i.test(navigator.userAgent) ? 
              'Hold button to stop recording' : 
              'Tap to stop and send'
          }
        </p>
      </div>
    </div>
  );
}