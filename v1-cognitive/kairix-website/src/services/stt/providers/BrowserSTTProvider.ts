import type { STTProvider } from '../types';

export class BrowserSTTProvider implements STTProvider {
  name = 'Browser Speech Recognition';
  private recognition: any; // SpeechRecognition type not available in all environments
  private isRecording = false;
  private finalTranscript = '';
  private allTranscript = ''; // Track all text recognized so far
  private currentResolve: ((transcript: string) => void) | null = null;
  private currentReject: ((error: Error) => void) | null = null;
  private language: string;
  private continuous: boolean;
  private interimResults: boolean;
  private startTime = 0;
  onInterimResult?: (transcript: string) => void;

  constructor(language: string = 'en-US', continuous: boolean = false, interimResults: boolean = true) {
    this.language = language;
    // Detect mobile and override continuous mode for better mobile support
    const isMobile = /Mobile|Android|iPhone|iPad/i.test(navigator.userAgent);
    this.continuous = isMobile ? false : continuous;
    this.interimResults = interimResults;
    
    // Check for browser support
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      throw new Error('Speech recognition not supported in this browser');
    }

    console.log('BrowserSTTProvider initialized:', {
      language: this.language,
      continuous: this.continuous,
      interimResults: this.interimResults,
      isMobile,
      userAgent: navigator.userAgent
    });

    this.createRecognition();
  }

  private createRecognition() {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = this.continuous;
    this.recognition.interimResults = this.interimResults;
    this.recognition.lang = this.language;
    this.recognition.maxAlternatives = 1;
    
    console.log('BrowserSTTProvider: Created new recognition instance with:', {
      continuous: this.continuous,
      interimResults: this.interimResults,
      language: this.language
    });

    // Set up event handlers
    this.recognition.onstart = () => {
      console.log('BrowserSTTProvider: Recognition started (onstart event)');
    };

    this.recognition.onsoundstart = () => {
      console.log('BrowserSTTProvider: Sound detected (onsoundstart event)');
    };

    this.recognition.onspeechstart = () => {
      console.log('BrowserSTTProvider: Speech detected (onspeechstart event)');
    };

    this.recognition.onaudiostart = () => {
      console.log('BrowserSTTProvider: Audio capture started (onaudiostart event)');
    };

    this.recognition.onresult = (event: any) => {
      console.log('BrowserSTTProvider: onresult fired, results:', event.results);
      let interimText = '';
      let finalText = '';

      // Build complete transcript from all results
      for (let i = event.resultIndex || 0; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        
        if (event.results[i].isFinal) {
          finalText += transcript + ' ';
        } else {
          interimText += transcript + ' ';
        }
      }

      // ALWAYS accumulate - never overwrite
      if (finalText) {
        // Add new final text to our accumulated transcript
        this.allTranscript += (this.allTranscript ? ' ' : '') + finalText.trim();
        this.finalTranscript = this.allTranscript;
      }
      
      // Show accumulated text plus current interim
      const displayText = this.allTranscript + (this.allTranscript && interimText ? ' ' : '') + interimText.trim();

      console.log('BrowserSTTProvider: Transcript update - all:', this.allTranscript, 'final:', this.finalTranscript, 'interim:', interimText);

      // Always call callback with complete text so far
      if (this.onInterimResult && displayText) {
        this.onInterimResult(displayText);
      }
    };

    this.recognition.onnomatch = () => {
      console.log('BrowserSTTProvider: No speech was detected (onnomatch event)');
    };

    this.recognition.onsoundend = () => {
      console.log('BrowserSTTProvider: Sound has stopped being detected (onsoundend event)');
    };

    this.recognition.onspeechend = () => {
      console.log('BrowserSTTProvider: Speech has stopped being detected (onspeechend event)');
    };

    this.recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      
      // Handle specific error types
      if (event.error === 'no-speech') {
        console.log('No speech detected - this is normal if user was silent');
        // For no-speech, we might want to resolve with empty string instead of rejecting
        if (this.currentResolve) {
          this.currentResolve('');
          this.currentResolve = null;
          this.currentReject = null;
        }
      } else {
        // For other errors, reject
        this.isRecording = false;
        if (this.currentReject) {
          this.currentReject(new Error(`Speech recognition error: ${event.error}`));
          this.currentReject = null;
          this.currentResolve = null;
        }
      }
    };

    this.recognition.onend = () => {
      console.log('Recognition ended, all transcript:', this.allTranscript);
      
      // On mobile, if recognition ends too quickly (less than 1 second), restart it
      const isMobile = /Mobile|Android|iPhone|iPad/i.test(navigator.userAgent);
      if (isMobile && this.isRecording && Date.now() - this.startTime < 1000) {
        console.log('Mobile STT ended too quickly, restarting...');
        try {
          this.recognition.start();
          return;
        } catch (error) {
          console.error('Failed to restart recognition:', error);
        }
      }
      
      // Don't set isRecording to false here, it's managed by stopRecording
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
    
    // Don't reset allTranscript - keep accumulating
    this.isRecording = true;
    this.finalTranscript = '';
    // Keep allTranscript to accumulate across sessions
    this.startTime = Date.now();
    
    try {
      // Request microphone permission explicitly with better mobile settings
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      console.log('Microphone permission granted');
      
      // Stop the permission check stream immediately - we don't need it
      stream.getTracks().forEach(track => track.stop());
      
      // Small delay for mobile devices to release audio resources
      if (/Mobile|Android|iPhone|iPad/i.test(navigator.userAgent)) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // Start recognition
      this.recognition.start();
      console.log('Speech recognition started');
    } catch (error) {
      this.isRecording = false;
      console.error('Failed to start recording:', error);
      
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
          throw new Error('Microphone permission denied. Please allow microphone access.');
        } else if (error.name === 'NotFoundError') {
          throw new Error('No microphone found. Please connect a microphone.');
        } else if (error.message.includes('recognition has already started')) {
          // Handle case where recognition is already running
          console.warn('Recognition already started, stopping and retrying...');
          this.recognition.stop();
          await new Promise(resolve => setTimeout(resolve, 200));
          this.recognition.start();
        } else {
          throw new Error(`Failed to start recording: ${error.message}`);
        }
      }
      throw error;
    }
  }

  async stopRecording(): Promise<string> {
    if (!this.isRecording) {
      console.warn('BrowserSTTProvider: stopRecording called but not recording');
      return this.finalTranscript || '';
    }

    return new Promise((resolve, reject) => {
      this.currentResolve = resolve;
      this.currentReject = reject;
      this.isRecording = false; // Set here instead of in onend
      this.recognition.stop();
    });
  }

  abort(): void {
    console.log('BrowserSTTProvider: abort called, isRecording:', this.isRecording);
    
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch (error) {
        console.error('Error aborting recognition:', error);
      }
    }
    
    this.isRecording = false;
    // Don't clear transcripts on abort - keep accumulated text
    this.currentResolve = null;
    this.currentReject = null;
  }
  
  clearTranscript(): void {
    this.allTranscript = '';
    this.finalTranscript = '';
  }
}