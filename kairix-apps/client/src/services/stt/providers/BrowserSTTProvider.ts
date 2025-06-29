import type { STTProvider } from '../types';

export class BrowserSTTProvider implements STTProvider {
  name = 'Browser Speech Recognition';
  private recognition: any; // SpeechRecognition type not available in all environments
  private isRecording = false;
  private finalTranscript = '';
  private allTranscript = ''; // Track all text recognized so far
  private currentResolve: ((transcript: string) => void) | null = null;
  private currentReject: ((error: Error) => void) | null = null;

  constructor(language: string = 'en-US', continuous: boolean = false, interimResults: boolean = true) {
    // Check for browser support
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      throw new Error('Speech recognition not supported in this browser');
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = continuous;
    this.recognition.interimResults = interimResults;
    this.recognition.lang = language;

    // Set up event handlers
    this.recognition.onresult = (event: any) => {
      let allText = '';
      let finalText = '';

      // Build complete transcript from all results
      for (let i = 0; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        allText += transcript + ' ';
        
        if (event.results[i].isFinal) {
          finalText += transcript + ' ';
        }
      }

      // Update transcripts
      this.allTranscript = allText.trim();
      if (finalText) {
        this.finalTranscript = finalText.trim();
      }

      // Always call callback with complete text so far
      if (this.onInterimResult) {
        this.onInterimResult(this.allTranscript);
      }
    };

    this.recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      this.isRecording = false;
      if (this.currentReject) {
        this.currentReject(new Error(`Speech recognition error: ${event.error}`));
        this.currentReject = null;
        this.currentResolve = null;
      }
    };

    this.recognition.onend = () => {
      console.log('Recognition ended, all transcript:', this.allTranscript);
      this.isRecording = false;
      if (this.currentResolve) {
        // Return all recognized text, not just final
        this.currentResolve(this.allTranscript || this.finalTranscript);
        this.currentResolve = null;
        this.currentReject = null;
      }
    };
  }

  isSupported(): boolean {
    return !!(window as any).SpeechRecognition || !!(window as any).webkitSpeechRecognition;
  }

  async startRecording(): Promise<void> {
    if (this.isRecording) {
      throw new Error('Already recording');
    }

    console.log('BrowserSTTProvider: Starting recording');
    this.isRecording = true;
    this.finalTranscript = '';
    this.allTranscript = '';
    this.recognition.start();
  }

  async stopRecording(): Promise<string> {
    if (!this.isRecording) {
      console.warn('BrowserSTTProvider: stopRecording called but not recording');
      return this.finalTranscript || '';
    }

    return new Promise((resolve, reject) => {
      this.currentResolve = resolve;
      this.currentReject = reject;
      this.recognition.stop();
    });
  }

  abort(): void {
    if (this.isRecording) {
      this.recognition.abort();
      this.isRecording = false;
      this.currentResolve = null;
      this.currentReject = null;
    }
  }

  onInterimResult?: (transcript: string) => void;
}