import type { TTSProvider, TTSOptions, TTSVoice } from '../types';

export class BrowserTTSProvider implements TTSProvider {
  name = 'Browser Speech Synthesis';
  private synthesis: SpeechSynthesis;

  constructor() {
    this.synthesis = window.speechSynthesis;
  }

  isSupported(): boolean {
    return 'speechSynthesis' in window;
  }

  async speak(text: string, options?: TTSOptions): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.isSupported()) {
        reject(new Error('Speech synthesis not supported'));
        return;
      }

      this.stop(); // Cancel any ongoing speech

      const utterance = new SpeechSynthesisUtterance(text);

      // Apply options
      if (options?.voice) {
        const voices = this.synthesis.getVoices();
        const voice = voices.find(v => v.voiceURI === options.voice);
        if (voice) utterance.voice = voice;
      }
      
      if (options?.rate !== undefined) utterance.rate = options.rate;
      if (options?.pitch !== undefined) utterance.pitch = options.pitch;
      if (options?.volume !== undefined) utterance.volume = options.volume;

      utterance.onend = () => {
        resolve();
      };

      utterance.onerror = (event) => {
        reject(new Error(`Speech synthesis error: ${event.error}`));
      };

      this.synthesis.speak(utterance);
    });
  }

  stop(): void {
    if (this.synthesis.speaking) {
      this.synthesis.cancel();
    }
  }

  async getVoices(): Promise<TTSVoice[]> {
    // Voices might not be loaded immediately
    await new Promise(resolve => {
      if (this.synthesis.getVoices().length > 0) {
        resolve(undefined);
      } else {
        this.synthesis.addEventListener('voiceschanged', () => resolve(undefined), { once: true });
      }
    });

    return this.synthesis.getVoices().map(voice => ({
      id: voice.voiceURI,
      name: voice.name,
      lang: voice.lang,
    }));
  }
}