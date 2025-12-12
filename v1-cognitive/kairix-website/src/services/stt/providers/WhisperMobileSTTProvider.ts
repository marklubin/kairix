import { pipeline, env } from '@xenova/transformers';
import type { STTProvider } from '../types';

// Configure Transformers.js to use local models
env.allowLocalModels = false;
env.useBrowserCache = true;

export class WhisperMobileSTTProvider implements STTProvider {
  name = 'Whisper Mobile';
  private transcriber: any = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private stream: MediaStream | null = null;
  private isRecording = false;
  private audioBuffer: Float32Array[] = [];
  private chunkInterval: NodeJS.Timeout | null = null;
  private accumulatedTranscript = '';
  private lastProcessedLength = 0;
  private modelName: string;
  
  onInterimResult?: (transcript: string) => void;
  
  constructor(modelName: string = 'Xenova/whisper-tiny.en') {
    this.modelName = modelName;
  }

  async initialize() {
    console.log('Initializing Whisper model for mobile...');
    if (!this.transcriber) {
      try {
        this.transcriber = await pipeline('automatic-speech-recognition', this.modelName, {
          quantized: true,
          progress_callback: (progress: any) => {
            console.log('Model loading progress:', progress);
          }
        });
        console.log('Whisper model loaded successfully');
      } catch (error) {
        console.error('Failed to load Whisper model:', error);
        throw error;
      }
    }
  }

  isSupported(): boolean {
    return typeof window !== 'undefined' && 
           'MediaRecorder' in window && 
           'AudioContext' in window &&
           'WebAssembly' in window;
  }

  async startRecording(): Promise<void> {
    if (this.isRecording) {
      throw new Error('Already recording');
    }

    console.log('WhisperMobile: Starting recording...');
    
    // Initialize model if not already done
    await this.initialize();
    
    // Reset state
    this.audioBuffer = [];
    this.accumulatedTranscript = '';
    this.lastProcessedLength = 0;
    
    try {
      // Get user media with mobile-optimized settings
      this.stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000 // Whisper expects 16kHz
        } 
      });
      
      // Create audio context
      this.audioContext = new AudioContext({ sampleRate: 16000 });
      this.source = this.audioContext.createMediaStreamSource(this.stream);
      
      // Create processor for real-time audio chunks
      const bufferSize = 4096;
      this.processor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);
      
      this.processor.onaudioprocess = (e) => {
        if (!this.isRecording) return;
        
        const inputData = e.inputBuffer.getChannelData(0);
        const float32Array = new Float32Array(inputData);
        this.audioBuffer.push(float32Array);
      };
      
      // Connect audio nodes
      this.source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
      
      this.isRecording = true;
      
      // Start processing chunks every 2 seconds for near real-time transcription
      this.startChunkProcessing();
      
      console.log('WhisperMobile: Recording started');
    } catch (error) {
      this.cleanup();
      console.error('Failed to start recording:', error);
      throw error;
    }
  }

  private startChunkProcessing() {
    // Process audio chunks every 2 seconds
    this.chunkInterval = setInterval(async () => {
      if (!this.isRecording || this.audioBuffer.length === 0) return;
      
      try {
        // Combine audio chunks
        const totalLength = this.audioBuffer.reduce((acc, chunk) => acc + chunk.length, 0);
        const combinedAudio = new Float32Array(totalLength);
        let offset = 0;
        
        for (const chunk of this.audioBuffer) {
          combinedAudio.set(chunk, offset);
          offset += chunk.length;
        }
        
        // Only process new audio since last transcription
        if (combinedAudio.length > this.lastProcessedLength) {
          console.log('Processing audio chunk...', combinedAudio.length, 'samples');
          
          // Transcribe the audio
          const output = await this.transcriber(combinedAudio, {
            return_timestamps: false,
            chunk_length_s: 30,
            stride_length_s: 5
          });
          
          if (output.text) {
            this.accumulatedTranscript = output.text.trim();
            console.log('Interim transcript:', this.accumulatedTranscript);
            
            // Call interim result callback
            if (this.onInterimResult) {
              this.onInterimResult(this.accumulatedTranscript);
            }
          }
          
          this.lastProcessedLength = combinedAudio.length;
        }
      } catch (error) {
        console.error('Error processing audio chunk:', error);
      }
    }, 2000); // Process every 2 seconds
  }

  async stopRecording(): Promise<string> {
    if (!this.isRecording) {
      throw new Error('Not recording');
    }

    console.log('WhisperMobile: Stopping recording...');
    this.isRecording = false;
    
    // Stop chunk processing
    if (this.chunkInterval) {
      clearInterval(this.chunkInterval);
      this.chunkInterval = null;
    }
    
    try {
      // Process any remaining audio
      if (this.audioBuffer.length > 0) {
        const totalLength = this.audioBuffer.reduce((acc, chunk) => acc + chunk.length, 0);
        const combinedAudio = new Float32Array(totalLength);
        let offset = 0;
        
        for (const chunk of this.audioBuffer) {
          combinedAudio.set(chunk, offset);
          offset += chunk.length;
        }
        
        console.log('Processing final audio...', combinedAudio.length, 'samples');
        
        // Final transcription
        const output = await this.transcriber(combinedAudio, {
          return_timestamps: false,
          chunk_length_s: 30,
          stride_length_s: 5
        });
        
        if (output.text) {
          this.accumulatedTranscript = output.text.trim();
        }
      }
      
      const finalTranscript = this.accumulatedTranscript;
      console.log('Final transcript:', finalTranscript);
      
      // Cleanup
      this.cleanup();
      
      return finalTranscript;
    } catch (error) {
      this.cleanup();
      console.error('Error in stopRecording:', error);
      throw error;
    }
  }

  abort(): void {
    console.log('WhisperMobile: Aborting...');
    if (this.chunkInterval) {
      clearInterval(this.chunkInterval);
      this.chunkInterval = null;
    }
    this.isRecording = false;
    this.cleanup();
  }

  private cleanup() {
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }
    
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    this.audioBuffer = [];
    this.lastProcessedLength = 0;
  }
}