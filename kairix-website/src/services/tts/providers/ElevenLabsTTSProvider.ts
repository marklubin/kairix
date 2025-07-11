import type { TTSProvider, TTSVoice } from '../types';

export class ElevenLabsTTSProvider implements TTSProvider {
  name = 'ElevenLabs';
  private apiKey: string;
  private voiceId: string;
  private modelId: string;
  private audioQueue: HTMLAudioElement[] = [];
  private isPlaying = false;
  private currentAudio: HTMLAudioElement | null = null;

  constructor(voiceId: string = '0NkECxcbkydDMspBKvQp', modelId: string = 'eleven_flash_v2_5') {
    this.apiKey = import.meta.env.VITE_ELEVENLABS_API_KEY || '';
    console.log('ElevenLabs API Key loaded:', this.apiKey ? 'Yes' : 'No');
    console.log('API Key length:', this.apiKey.length);
    console.log('API Key prefix:', this.apiKey.substring(0, 10));
    console.log('All VITE env vars:', Object.keys(import.meta.env).filter(k => k.startsWith('VITE_')));
    this.voiceId = voiceId;
    this.modelId = modelId;
  }

  isSupported(): boolean {
    return typeof window !== 'undefined' && 'Audio' in window;
  }

  async getVoices(): Promise<TTSVoice[]> {
    if (!this.apiKey) {
      console.error('ElevenLabs API key is missing');
      return [];
    }

    console.log('Fetching voices with API key:', this.apiKey.substring(0, 10) + '...');
    
    try {
      const response = await fetch('https://api.elevenlabs.io/v1/voices', {
        headers: {
          'xi-api-key': this.apiKey
        }
      });

      console.log('ElevenLabs voices response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to fetch ElevenLabs voices:', response.status, errorText);
        return [];
      }

      const data = await response.json();
      return data.voices.map((voice: any) => ({
        id: voice.voice_id,
        name: voice.name,
        lang: voice.labels?.language || 'en',
        localService: false
      }));
    } catch (error) {
      console.error('Error fetching ElevenLabs voices:', error);
      return [];
    }
  }

  async speak(text: string, options?: any): Promise<void> {
    if (!this.apiKey) {
      console.error('ElevenLabs API key not configured');
      throw new Error('ElevenLabs API key not configured');
    }

    const voiceId = options?.voice || this.voiceId;

    try {
      console.log('Making ElevenLabs API request with key:', this.apiKey.substring(0, 10) + '...');
      const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'xi-api-key': this.apiKey
        },
        body: JSON.stringify({
          text,
          model_id: this.modelId,
          voice_settings: {
            stability: options?.stability || 0.5,
            similarity_boost: options?.similarity_boost || 0.75,
            style: options?.style || 0,
            use_speaker_boost: options?.use_speaker_boost || true
          }
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('ElevenLabs API error response:', errorText);
        console.error('Response status:', response.status);
        console.error('Using API key:', this.apiKey);
        throw new Error(`ElevenLabs API error: ${response.status} - ${errorText}`);
      }

      // Get audio data
      const audioData = await response.arrayBuffer();
      const blob = new Blob([audioData], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(blob);

      // Create audio element
      const audio = new Audio(audioUrl);
      audio.volume = options?.volume || 1;
      audio.playbackRate = options?.rate || 1;

      // Add to queue
      this.audioQueue.push(audio);

      // Play if not already playing
      if (!this.isPlaying) {
        this.playNext();
      }

      // Return promise that resolves when this specific audio finishes
      return new Promise((resolve) => {
        audio.addEventListener('ended', () => {
          URL.revokeObjectURL(audioUrl);
          resolve();
        });
      });
    } catch (error) {
      console.error('ElevenLabs TTS error:', error);
      throw error;
    }
  }

  private async playNext() {
    if (this.audioQueue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    this.currentAudio = this.audioQueue.shift()!;

    this.currentAudio.addEventListener('ended', () => {
      this.currentAudio = null;
      this.playNext();
    });

    try {
      await this.currentAudio.play();
    } catch (error) {
      console.error('Error playing audio:', error);
      this.currentAudio = null;
      this.playNext();
    }
  }

  pause(): void {
    if (this.currentAudio) {
      this.currentAudio.pause();
    }
  }

  resume(): void {
    if (this.currentAudio) {
      this.currentAudio.play();
    }
  }

  stop(): void {
    // Stop current audio
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }

    // Clear queue
    this.audioQueue.forEach(audio => {
      audio.pause();
      if (audio.src) {
        URL.revokeObjectURL(audio.src);
      }
    });
    this.audioQueue = [];
    this.isPlaying = false;
  }


  setVoiceId(voiceId: string): void {
    this.voiceId = voiceId;
  }

  setModelId(modelId: string): void {
    this.modelId = modelId;
  }
}