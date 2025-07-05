import type { TTSProvider, TTSVoice } from '../types';

export class MacOSTTSProvider implements TTSProvider {
  name = 'macOS';
  private synthesis: SpeechSynthesis;
  private currentUtterance: SpeechSynthesisUtterance | null = null;

  constructor() {
    this.synthesis = window.speechSynthesis;
  }

  isSupported(): boolean {
    return typeof window !== 'undefined' && 'speechSynthesis' in window;
  }

  async getVoices(): Promise<TTSVoice[]> {
    return new Promise((resolve) => {
      const processVoices = () => {
        const voices = this.synthesis.getVoices();
        
        // Filter and enhance voice information
        const enhancedVoices = voices.map(voice => {
          // Detect voice quality/type
          let quality = 'standard';
          let category = 'system';
          
          // Premium voices often have specific patterns in their names
          if (voice.name.includes('Premium') || voice.name.includes('Enhanced')) {
            quality = 'premium';
          } else if (voice.name.includes('Siri') || voice.name.includes('Neural')) {
            quality = 'neural';
            category = 'siri';
          } else if (voice.name.includes('Personal Voice')) {
            quality = 'personal';
            category = 'cloned';
          }
          
          // macOS voices often have (Enhanced) or (Premium) in their names
          const cleanName = voice.name
            .replace(' (Enhanced)', '')
            .replace(' (Premium)', '')
            .replace(' (Siri)', '');
          
          return {
            id: voice.voiceURI,
            name: cleanName,
            lang: voice.lang,
            localService: voice.localService,
            quality,
            category,
            original: voice
          };
        });
        
        // Sort voices by quality and language
        enhancedVoices.sort((a, b) => {
          // Personal voices first
          if (a.category === 'cloned' && b.category !== 'cloned') return -1;
          if (b.category === 'cloned' && a.category !== 'cloned') return 1;
          
          // Then neural/siri voices
          if (a.quality === 'neural' && b.quality !== 'neural') return -1;
          if (b.quality === 'neural' && a.quality !== 'neural') return 1;
          
          // Then premium
          if (a.quality === 'premium' && b.quality === 'standard') return -1;
          if (b.quality === 'premium' && a.quality === 'standard') return 1;
          
          // Then by language
          return a.lang.localeCompare(b.lang);
        });
        
        resolve(enhancedVoices);
      };

      // macOS sometimes needs a moment to load all voices
      if (this.synthesis.getVoices().length > 0) {
        processVoices();
      } else {
        this.synthesis.addEventListener('voiceschanged', processVoices, { once: true });
        // Fallback timeout
        setTimeout(() => processVoices(), 100);
      }
    });
  }

  async speak(text: string, options?: any): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Cancel any ongoing speech
        this.stop();

        const utterance = new SpeechSynthesisUtterance(text);
        this.currentUtterance = utterance;

        // Apply options
        if (options?.voice) {
          const voices = this.synthesis.getVoices();
          const voice = voices.find(v => v.voiceURI === options.voice);
          if (voice) {
            utterance.voice = voice;
          }
        }

        // Set speech parameters with macOS-optimized defaults
        utterance.rate = options?.rate || 1.0;
        utterance.pitch = options?.pitch || 1.0;
        utterance.volume = options?.volume || 1.0;

        // macOS-specific: slightly slower rate often sounds better with neural voices
        if (utterance.voice?.name.includes('Siri') || utterance.voice?.name.includes('Neural')) {
          utterance.rate *= 0.95;
        }

        // Event handlers
        utterance.onend = () => {
          this.currentUtterance = null;
          resolve();
        };

        utterance.onerror = (event) => {
          this.currentUtterance = null;
          reject(new Error(`Speech synthesis error: ${event.error}`));
        };

        // Speak
        this.synthesis.speak(utterance);

        // macOS bug workaround: sometimes needs a resume
        if (this.synthesis.paused) {
          this.synthesis.resume();
        }
      } catch (error) {
        reject(error);
      }
    });
  }

  pause(): void {
    this.synthesis.pause();
  }

  resume(): void {
    this.synthesis.resume();
  }

  stop(): void {
    this.synthesis.cancel();
    this.currentUtterance = null;
  }

  // Preview a voice with sample text
  async previewVoice(voiceId: string, sampleText?: string): Promise<void> {
    const text = sampleText || "Hello, this is a preview of this voice. It can speak naturally with good pronunciation.";
    await this.speak(text, { voice: voiceId, rate: 1.0 });
  }

  // Get system information
  getSystemInfo(): { platform: string; voiceCount: number; hasNeuralVoices: boolean; hasPersonalVoice: boolean } {
    const voices = this.synthesis.getVoices();
    const hasNeuralVoices = voices.some(v => 
      v.name.includes('Siri') || v.name.includes('Neural') || v.name.includes('Premium')
    );
    const hasPersonalVoice = voices.some(v => v.name.includes('Personal Voice'));
    
    return {
      platform: 'macOS',
      voiceCount: voices.length,
      hasNeuralVoices,
      hasPersonalVoice
    };
  }
}