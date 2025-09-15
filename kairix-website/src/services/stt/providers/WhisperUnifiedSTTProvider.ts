import { pipeline } from '@xenova/transformers';
import type { STTProvider } from '../types';

export class WhisperUnifiedSTTProvider implements STTProvider {
  name = 'Whisper Unified';
  private transcriber: any = null;
  private isRecording = false;
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private audioBuffer: Float32Array[] = [];
  private chunkInterval: NodeJS.Timeout | null = null;
  private accumulatedTranscript = '';
  private lastProcessedLength = 0;
  private modelLoaded = false;
  
  onInterimResult?: (transcript: string) => void;

  async initialize() {
    if (!this.modelLoaded) {
      console.log('Initializing Whisper model...');
      
      // Configure transformers.js for browser
      const { env } = await import('@xenova/transformers');
      env.allowLocalModels = false;
      env.useBrowserCache = true;
      
      this.transcriber = await pipeline(
        'automatic-speech-recognition',
        'Xenova/whisper-tiny.en',
        {
          quantized: true,
          progress_callback: (progress: any) => {
            if (progress.status === 'progress') {
              console.log(`Loading model: ${Math.round(progress.progress)}%`);
            }
          }
        }
      );
      
      this.modelLoaded = true;
      console.log('Whisper model loaded successfully');
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

    console.log('WhisperUnified: Starting recording...');
    
    // Initialize model first
    await this.initialize();
    
    // Reset state but KEEP accumulated transcript
    this.isRecording = true;
    this.audioBuffer = [];
    this.lastProcessedLength = 0;
    
    // Get microphone access
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        sampleRate: 16000
      }
    });
    
    // Setup audio processing
    this.audioContext = new AudioContext({ sampleRate: 16000 });
    this.source = this.audioContext.createMediaStreamSource(this.stream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    
    this.processor.onaudioprocess = (e) => {
      if (!this.isRecording) return;
      
      const inputData = e.inputBuffer.getChannelData(0);
      const buffer = new Float32Array(inputData.length);
      buffer.set(inputData);
      this.audioBuffer.push(buffer);
    };
    
    this.source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
    
    console.log('WhisperUnified: Recording started');
    
    // Start chunk processing for real-time updates
    this.startChunkProcessing();
  }

  private startChunkProcessing() {
    // Process audio chunks every 2 seconds for interim results
    this.chunkInterval = setInterval(async () => {
      if (!this.isRecording || this.audioBuffer.length === 0) return;
      
      try {
        // Combine all audio chunks
        const totalLength = this.audioBuffer.reduce((acc, chunk) => acc + chunk.length, 0);
        const combinedAudio = new Float32Array(totalLength);
        let offset = 0;
        
        for (const chunk of this.audioBuffer) {
          combinedAudio.set(chunk, offset);
          offset += chunk.length;
        }
        
        console.log('Processing audio chunk...', combinedAudio.length, 'samples');
        
        // Transcribe the audio
        const output = await this.transcriber(combinedAudio, {
          return_timestamps: false,
          chunk_length_s: 30,
          stride_length_s: 5
        });
        
        if (output.text) {
          // Update accumulated transcript with new text
          this.accumulatedTranscript = output.text.trim();
          console.log('Accumulated transcript:', this.accumulatedTranscript);
          
          // Send interim result
          if (this.onInterimResult) {
            this.onInterimResult(this.accumulatedTranscript);
          }
        }
      } catch (error) {
        console.error('Error processing audio chunk:', error);
      }
    }, 2000);
  }

  async stopRecording(): Promise<string> {
    if (!this.isRecording) {
      throw new Error('Not recording');
    }

    console.log('WhisperUnified: Stopping recording...');
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
      
      // DON'T clear accumulated transcript - keep it for next recording
      // Only cleanup audio resources
      this.cleanup();
      
      return finalTranscript;
    } catch (error) {
      this.cleanup();
      console.error('Error in stopRecording:', error);
      throw error;
    }
  }

  abort(): void {
    console.log('WhisperUnified: Aborting...');
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
  
  // Method to clear accumulated transcript when needed
  clearTranscript(): void {
    this.accumulatedTranscript = '';
  }
}