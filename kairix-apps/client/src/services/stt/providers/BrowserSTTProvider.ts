import type { STTProvider } from '../types';

export class BrowserSTTProvider implements STTProvider {
  name = 'Browser Speech Recognition';
  private recognition: any; // SpeechRecognition type not available in all environments
  private isRecording = false;
  private finalTranscript = '';
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
      let interimTranscript = '';
      this.finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          this.finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      // Call interim result callback if provided
      if (this.onInterimResult && interimTranscript) {
        this.onInterimResult(interimTranscript);
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
      this.isRecording = false;
      if (this.currentResolve) {
        this.currentResolve(this.finalTranscript);
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

    this.isRecording = true;
    this.finalTranscript = '';
    this.recognition.start();
  }

  async stopRecording(): Promise<string> {
    if (!this.isRecording) {
      throw new Error('Not recording');
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