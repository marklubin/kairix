import { useEffect, useState } from 'react';

export function PirateShip() {
  const [hasPlayed, setHasPlayed] = useState(false);

  const playMelody = () => {
    if (hasPlayed) return;
    setHasPlayed(true);
    
    // Create dramatic computer melody
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    
    // Resume context if suspended (browser autoplay policy)
    if (audioContext.state === 'suspended') {
      audioContext.resume();
    }
    
    // Create oscillator and gain nodes
    const createNote = (frequency: number, startTime: number, duration: number) => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      // Use triangle wave for that classic computer sound
      oscillator.type = 'triangle';
      oscillator.frequency.value = frequency;
      
      // Connect nodes
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // Envelope for each note
      gainNode.gain.setValueAtTime(0, startTime);
      gainNode.gain.linearRampToValueAtTime(0.2, startTime + 0.05);
      gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
      
      // Start and stop
      oscillator.start(startTime);
      oscillator.stop(startTime + duration);
    };
    
    // Note frequencies
    const E4 = 329.63, G4 = 392.00, A4 = 440.00;
    const C5 = 523.25, E5 = 659.25, F5 = 698.46, G5 = 783.99, Ab5 = 830.61;
    const Db5 = 554.37;
    
    const beat = 0.3;
    
    // Function to play one loop of the melody
    const playMelodyLoop = (loopStartTime: number) => {
      let t = 0;
      
      // Main melody - C major (happy)
      createNote(C5, loopStartTime + t, beat); t += beat;
      createNote(E5, loopStartTime + t, beat); t += beat;
      createNote(G5, loopStartTime + t, beat); t += beat;
      createNote(E5, loopStartTime + t, beat * 2); t += beat * 2;
      
      // Transition to A minor (sad)
      createNote(A4, loopStartTime + t, beat); t += beat;
      createNote(C5, loopStartTime + t, beat); t += beat;
      createNote(E5, loopStartTime + t, beat); t += beat;
      createNote(C5, loopStartTime + t, beat * 2); t += beat * 2;
      
      // Back to C major (happy)
      createNote(G5, loopStartTime + t, beat); t += beat;
      createNote(E5, loopStartTime + t, beat); t += beat;
      createNote(C5, loopStartTime + t, beat); t += beat;
      createNote(G4, loopStartTime + t, beat * 2); t += beat * 2;
      
      // A minor again (sad)
      createNote(E5, loopStartTime + t, beat); t += beat;
      createNote(C5, loopStartTime + t, beat); t += beat;
      createNote(A4, loopStartTime + t, beat); t += beat;
      createNote(E4, loopStartTime + t, beat * 2); t += beat * 2;
      
      // C major triumphant
      createNote(C5, loopStartTime + t, beat / 2); t += beat / 2;
      createNote(E5, loopStartTime + t, beat / 2); t += beat / 2;
      createNote(G5, loopStartTime + t, beat / 2); t += beat / 2;
      createNote(C5, loopStartTime + t, beat); t += beat;
      
      // Half step up to Db major - THE AMAZING MODULATION
      createNote(Db5, loopStartTime + t, beat); t += beat;
      createNote(F5, loopStartTime + t, beat); t += beat;
      createNote(Ab5, loopStartTime + t, beat); t += beat;
      createNote(F5, loopStartTime + t, beat); t += beat;
      createNote(Db5, loopStartTime + t, beat * 3); t += beat * 3;
      
      return t; // Return total duration
    };
    
    // Start the infinite loop
    let currentTime = audioContext.currentTime + 0.5;
    const loopDuration = playMelodyLoop(currentTime);
    
    // Schedule loops forever
    const scheduleNextLoop = () => {
      currentTime += loopDuration;
      playMelodyLoop(currentTime);
      // Schedule the next loop before this one ends
      setTimeout(scheduleNextLoop, (loopDuration - 1) * 1000);
    };
    
    // Start scheduling loops
    setTimeout(scheduleNextLoop, (loopDuration - 1) * 1000);
  };

  useEffect(() => {
    // Try to play on any user interaction
    const handleInteraction = () => {
      playMelody();
      // Remove listeners after first play
      document.removeEventListener('click', handleInteraction);
      document.removeEventListener('keydown', handleInteraction);
      document.removeEventListener('touchstart', handleInteraction);
      document.removeEventListener('mousedown', handleInteraction);
    };

    document.addEventListener('click', handleInteraction);
    document.addEventListener('keydown', handleInteraction);
    document.addEventListener('touchstart', handleInteraction);
    document.addEventListener('mousedown', handleInteraction);

    // Try multiple strategies to start audio
    const tryAutoplay = async () => {
      // Strategy 1: Direct play
      playMelody();
      
      // Strategy 2: Create and click a temporary button
      if (!hasPlayed) {
        setTimeout(() => {
          const tempButton = document.createElement('button');
          tempButton.style.position = 'absolute';
          tempButton.style.left = '-9999px';
          document.body.appendChild(tempButton);
          tempButton.click();
          document.body.removeChild(tempButton);
        }, 100);
      }
      
      // Strategy 3: Dispatch mouse event
      if (!hasPlayed) {
        setTimeout(() => {
          const event = new MouseEvent('click', {
            view: window,
            bubbles: true,
            cancelable: true
          });
          document.body.dispatchEvent(event);
        }, 200);
      }
    };
    
    tryAutoplay();

    return () => {
      document.removeEventListener('click', handleInteraction);
      document.removeEventListener('keydown', handleInteraction);
      document.removeEventListener('touchstart', handleInteraction);
      document.removeEventListener('mousedown', handleInteraction);
    };
  }, []);

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-b from-black via-purple-900/20 to-blue-900/30 p-2">
      <div className="text-center w-full max-w-[400px] relative">
        {/* Cyberpunk ASCII Art with City Skyline, Palm Trees, and Pirate Ship */}
        <div className="overflow-x-auto mb-4">
          <pre className="text-[0.5rem] font-mono leading-none relative inline-block">
          <div className="inline-block">
            <div>
              <span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span>
            </div>
            <div className="flex">
              <span className="text-red-500">|</span>
              <span className="text-cyan-400 animate-pulse">
{`▓▓ ▓▓  ▓▓▓▓  ▓▓▓▓▓ ▓▓▓▓▓▓ ▓▓▓▓▓ ▓▓ ▓▓`}
              </span>
              <span className="text-pink-500">|</span>
            </div>
            <div className="flex">
              <span className="text-orange-500">|</span>
              <span className="text-cyan-400 animate-pulse">
{`▓▓▓▓   ▓▓  ▓▓   ▓▓   ▓▓  ▓▓   ▓▓   ▓▓ ▓▓`}
              </span>
              <span className="text-purple-500">|</span>
            </div>
            <div className="flex">
              <span className="text-yellow-500">|</span>
              <span className="text-cyan-400 animate-pulse">
{`▓▓▓▓   ▓▓▓▓▓▓   ▓▓   ▓▓▓▓▓    ▓▓    ▓▓▓▓ `}
              </span>
              <span className="text-red-500">|</span>
            </div>
            <div className="flex">
              <span className="text-green-500">|</span>
              <span className="text-cyan-400 animate-pulse">
{`▓▓ ▓▓  ▓▓  ▓▓   ▓▓   ▓▓  ▓▓   ▓▓   ▓▓ ▓▓`}
              </span>
              <span className="text-orange-500">|</span>
            </div>
            <div className="flex">
              <span className="text-blue-500">|</span>
              <span className="text-cyan-400 animate-pulse">
{`▓▓ ▓▓  ▓▓  ▓▓  ▓▓▓▓▓ ▓▓  ▓▓  ▓▓▓▓▓ ▓▓ ▓▓`}
              </span>
              <span className="text-yellow-500">|</span>
            </div>
            <div>
              <span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span><span className="text-pink-500">-</span><span className="text-red-500">-</span><span className="text-orange-500">-</span><span className="text-yellow-500">-</span><span className="text-green-500">-</span><span className="text-blue-500">-</span><span className="text-purple-500">-</span>
            </div>
          </div>
          <span className="text-yellow-400 animate-bounce">
{`
   (o )  DUCKY BAND
  <(_ )>  ♪ ♫ ♪`}
          </span>
          <span className="text-orange-500">
{`            |>
            |
          __|__
         |_____|
         | ⚡ |
         |_____|`}
          </span>
          <span className="text-cyan-300">
{`      ___|_____|___
      \\          /
   ^^ \\SINKING / ^^
  ^^   \\      /  ^^
    ^^  \\____/  ^^
         \\__/`}
          </span>
          <span className="text-blue-400 animate-pulse">
{`    PACIFIC OCEAN
   ~~~~~~~~~~~~~~~
  ~~~~~~~~~~~~~~~~~
 ~~~~~~~~~~~~~~~~~~~`}
          </span>
        </pre>
        </div>
        
        <style dangerouslySetInnerHTML={{ __html: `
          @keyframes waveReveal {
            0% {
              -webkit-mask-position: -200% 0;
              mask-position: -200% 0;
            }
            100% {
              -webkit-mask-position: 200% 0;
              mask-position: 200% 0;
            }
          }
          
          .wave-line {
            -webkit-mask-image: linear-gradient(90deg, 
              transparent 0%, 
              rgba(0,0,0,0.1) 20%, 
              rgba(0,0,0,0.3) 30%, 
              rgba(0,0,0,0.6) 40%, 
              rgba(0,0,0,1) 50%, 
              rgba(0,0,0,0.6) 60%, 
              rgba(0,0,0,0.3) 70%, 
              rgba(0,0,0,0.1) 80%, 
              transparent 100%
            );
            mask-image: linear-gradient(90deg, 
              transparent 0%, 
              rgba(0,0,0,0.1) 20%, 
              rgba(0,0,0,0.3) 30%, 
              rgba(0,0,0,0.6) 40%, 
              rgba(0,0,0,1) 50%, 
              rgba(0,0,0,0.6) 60%, 
              rgba(0,0,0,0.3) 70%, 
              rgba(0,0,0,0.1) 80%, 
              transparent 100%
            );
            -webkit-mask-size: 200% 100%;
            mask-size: 200% 100%;
            -webkit-mask-repeat: no-repeat;
            mask-repeat: no-repeat;
            animation: waveReveal 8s linear infinite;
            display: inline-block;
            width: 100%;
          }
          
          .wave-line:nth-child(1) { animation-delay: 0s; }
          .wave-line:nth-child(3) { animation-delay: 0.7s; }
          .wave-line:nth-child(5) { animation-delay: 1.4s; }
          .wave-line:nth-child(7) { animation-delay: 2.1s; }
          .wave-line:nth-child(9) { animation-delay: 2.8s; }
          .wave-line:nth-child(11) { animation-delay: 3.5s; }
        `}} />
        
        <h1 className="text-base font-bold mb-4 leading-relaxed relative">
          <span className="wave-line bg-gradient-to-r from-yellow-400 via-orange-500 to-red-600 bg-clip-text text-transparent">
            The WINDSURF RUBBER DUCKY band
          </span>
          <br />
          <span className="wave-line bg-gradient-to-r from-cyan-400 via-pink-500 to-purple-600 bg-clip-text text-transparent">
            sings the crew off the sinking ship
          </span>
          <br />
          <span className="wave-line bg-gradient-to-r from-green-400 via-blue-500 to-pink-600 bg-clip-text text-transparent">
            as it descends into the Pacific Ocean
          </span>
          <br />
          <span className="wave-line bg-gradient-to-r from-orange-400 via-pink-500 to-cyan-600 bg-clip-text text-transparent">
            near the Farallon Islands
          </span>
          <br />
          <span className="wave-line bg-gradient-to-r from-purple-400 via-cyan-500 to-green-600 bg-clip-text text-transparent">
            while the great earthquake
          </span>
          <br />
          <span className="wave-line bg-gradient-to-r from-pink-400 via-orange-500 to-blue-600 bg-clip-text text-transparent">
            brings Los Angeles to the coast of San Francisco
          </span>
        </h1>
        
        <p className="text-sm mt-4">
          <span className="text-yellow-300 animate-pulse">The rubber duckies play </span>
          <span className="text-cyan-300">their final </span>
          <span className="text-pink-400">windsurf </span>
          <span className="text-purple-500 animate-pulse">serenade...</span>
        </p>

        {!hasPlayed && (
          <button
            onClick={playMelody}
            className="mt-4 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-sm rounded-full hover:from-purple-600 hover:to-pink-600 transition-all animate-pulse"
          >
            🎵 Play Dramatic Melody 🎵
          </button>
        )}

        {/* Additional cyberpunk decorative elements */}
        <div className="absolute bottom-2 right-2 text-pink-400/20 text-xs font-mono">
          {'ERR_403_FORBIDDEN'}
        </div>
        <div className="absolute top-2 right-2 text-yellow-400/30 text-2xl animate-bounce">
          🦆
        </div>
        <div className="absolute top-20 left-10 text-yellow-400/40 text-xl animate-bounce" style={{ animationDelay: '0.2s' }}>
          🦆
        </div>
        <div className="absolute bottom-20 right-20 text-yellow-400/25 text-3xl animate-bounce" style={{ animationDelay: '0.4s' }}>
          🦆
        </div>
        <div className="absolute top-40 right-10 text-yellow-400/35 text-lg animate-bounce" style={{ animationDelay: '0.6s' }}>
          🦆
        </div>
        <div className="absolute bottom-10 left-20 text-yellow-400/30 text-2xl animate-bounce" style={{ animationDelay: '0.8s' }}>
          🦆
        </div>
      </div>
    </div>
  );
}
