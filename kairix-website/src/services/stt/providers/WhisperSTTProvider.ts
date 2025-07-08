import { pipeline } from '@xenova/transformers';
import type { STTProvider } from '../types';

export class WhisperSTTProvider implements STTProvider {
  name = 'Whisper Web';
  private transcriber: any = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private isRecording = false;
  private stream: MediaStream | null = null;

  private modelName: string;
  
  constructor(modelName: string = 'Xenova/whisper-tiny.en') {
    this.modelName = modelName;
  }

  async initialize() {
    if (!this.transcriber) {
      this.transcriber = await pipeline('automatic-speech-recognition', this.modelName);
    }
  }

  isSupported(): boolean {
    return typeof window !== 'undefined' && 
           'MediaRecorder' in window && 
           'AudioContext' in window;
  }

  async startRecording(): Promise<void> {
    if (this.isRecording) {
      throw new Error('Already recording');
    }

    // Get user media
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    // Create media recorder
    this.mediaRecorder = new MediaRecorder(this.stream);
    this.audioChunks = [];

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    // Start recording
    this.mediaRecorder.start();
    this.isRecording = true;
  }

  async stopRecording(): Promise<string> {
    if (!this.isRecording || !this.mediaRecorder) {
      throw new Error('Not recording');
    }

    return new Promise(async (resolve, reject) => {
      this.mediaRecorder!.onstop = async () => {
        try {
          // Create audio blob
          const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
          
          // Convert to audio data
          const audioContext = new AudioContext({ sampleRate: 16000 });
          const audioBuffer = await audioBlob.arrayBuffer();
          const decodedAudio = await audioContext.decodeAudioData(audioBuffer);
          
          // Get mono channel data
          const audio = decodedAudio.getChannelData(0);
          
          // Initialize transcriber if needed
          await this.initialize();
          
          // Transcribe
          const output = await this.transcriber(audio, {
            return_timestamps: false,
            chunk_length_s: 30,
            stride_length_s: 5
          });
          
          // Clean up
          this.cleanup();
          
          resolve(output.text || '');
        } catch (error) {
          this.cleanup();
          reject(error);
        }
      };

      // Stop recording
      this.mediaRecorder!.stop();
    });
  }

  abort(): void {
    if (this.isRecording && this.mediaRecorder) {
      this.mediaRecorder.stop();
      this.cleanup();
    }
  }

  private cleanup() {
    this.isRecording = false;
    this.audioChunks = [];
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    this.mediaRecorder = null;
  }

  onInterimResult?: (transcript: string) => void;
}