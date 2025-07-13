import { useState, useCallback, useEffect, useRef } from 'react';
import type { Message } from 'ai';
import type { Model } from './types/config';
import { KAIRIX_SERVER_URL } from './lib/config';
import { ChatStorage } from './lib/storage';
import { useTTS } from './contexts/TTSContext';
import { useSTT } from './contexts/STTContext';

export function useCustomChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  // Use a fixed model since we removed the model selector
  const selectedModel = 'kairix-ai/kairix-llama-3.1-8b';
  const abortControllerRef = useRef<AbortController | null>(null);
  const { ttsService, isEnabled: isTTSEnabled } = useTTS();
  const { sttService, sttState } = useSTT();
  const currentAssistantMessageIdRef = useRef<string | null>(null);
  const handleSubmitRef = useRef<(e?: React.FormEvent, overrideInput?: string) => Promise<void>>(null);
  const sttToggleTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isProcessingSTTRef = useRef(false);

  // Load chat history when model changes
  useEffect(() => {
    if (selectedModel) {
      const savedMessages = ChatStorage.getSession('kairix-server', selectedModel);
      setMessages(savedMessages);
    }
  }, [selectedModel]);

  // Save chat history when messages change
  useEffect(() => {
    if (selectedModel && messages.length > 0) {
      ChatStorage.saveSession('kairix-server', selectedModel, messages);
    }
  }, [messages, selectedModel]);

  // No longer fetching models since we use a fixed model

  const handleSTTToggle = useCallback(async () => {
    console.log('handleSTTToggle called, current STT state:', sttState);
    
    // Prevent multiple rapid calls
    if (isProcessingSTTRef.current) {
      console.log('STT toggle already processing, ignoring...');
      return;
    }
    
    // Clear any existing timeout
    if (sttToggleTimeoutRef.current) {
      clearTimeout(sttToggleTimeoutRef.current);
    }
    
    isProcessingSTTRef.current = true;
    
    try {
      if (sttState.status === 'listening') {
        console.log('Stopping STT recording...');
        // Stop recording and get transcript
        const transcript = await sttService.stopRecording();
        console.log('STT stopped, transcript:', transcript);
        
        // NEVER auto-submit - just keep the accumulated text in input
        if (transcript) {
          console.log('Setting input with accumulated transcript:', transcript);
          setInput(transcript);
        }
      } else {
        console.log('Starting STT recording...');
        
        // No need to check for browser speech recognition - we're using Whisper
        
        // Interrupt TTS when starting STT
        if (isTTSEnabled && currentAssistantMessageIdRef.current) {
          console.log('Interrupting TTS for message:', currentAssistantMessageIdRef.current);
          ttsService.interruptMessage(currentAssistantMessageIdRef.current);
        }
        
        // Start recording - Whisper will accumulate from existing transcript
        console.log('Calling sttService.startRecording...');
        await sttService.startRecording(currentAssistantMessageIdRef.current || undefined);
        console.log('STT recording started successfully');
      }
    } catch (error) {
      console.error('STT toggle error:', error);
      if (error instanceof Error) {
        console.error('Error details:', error.message, error.stack);
        
        // Check for common permission errors
        if (error.message.includes('Permission denied') || error.message.includes('NotAllowedError')) {
          alert('Microphone permission denied. Please allow microphone access and try again.');
        } else {
          alert(`Speech recognition error: ${error.message}`);
        }
      }
    } finally {
      // Reset processing flag after a short delay
      sttToggleTimeoutRef.current = setTimeout(() => {
        isProcessingSTTRef.current = false;
      }, 300);
    }
  }, [sttState, sttService, isTTSEnabled, ttsService]);

  const handleSubmit = useCallback(async (e?: React.FormEvent, overrideInput?: string) => {
    e?.preventDefault();
    
    const messageContent = overrideInput || input;
    
    if (!messageContent.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageContent,
    };

    // Add user message to UI
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    // Clear the STT transcript when message is sent
    if (sttService && 'clearTranscript' in (sttService as any).provider) {
      ((sttService as any).provider as any).clearTranscript();
    }

    // Create a new message for the assistant that we'll update as we stream
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
    };
    setMessages(prev => [...prev, assistantMessage]);
    
    // Track current assistant message for TTS interruption
    currentAssistantMessageIdRef.current = assistantMessageId;
    
    // Notify TTS service of new message
    if (isTTSEnabled) {
      ttsService.startNewMessage(assistantMessageId);
    }

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        'X-API-Key': localStorage.getItem('apiKey') || 'test-api-key-12345',
      };

      // Get context messages (last 20) for API call
      const contextMessages = [userMessage];

      // Call the Kairix server with streaming
      const chatUrl = `${KAIRIX_SERVER_URL}/v1/chat/completions`;
      
      console.log('Attempting to connect to Kairix server:', {
        url: chatUrl,
        model: selectedModel,
        messageCount: contextMessages.length,
        serverUrl: KAIRIX_SERVER_URL
      });
      
      const response = await fetch(chatUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model: selectedModel,
          messages: contextMessages.map(msg => ({
            role: msg.role,
            content: msg.content,
          })),
          temperature: 0.7,
          max_tokens: 500,
          stream: true, // Enable streaming
        }),
        signal: abortControllerRef.current.signal,
      }).catch(error => {
        console.error('Network error connecting to Kairix server:', {
          error: error.message,
          url: chatUrl,
          serverUrl: KAIRIX_SERVER_URL,
          type: error.name,
          stack: error.stack
        });
        throw error;
      });

      if (!response.ok) {
        console.error('HTTP error from Kairix server:', {
          status: response.status,
          statusText: response.statusText,
          url: chatUrl,
          headers: Object.fromEntries(response.headers.entries())
        });
        const errorText = await response.text().catch(() => 'Could not read error response');
        console.error('Error response body:', errorText);
        throw new Error(`Failed to get response from Kairix server: ${response.status} ${response.statusText}`);
      }
      
      console.log('Successfully connected to Kairix server, starting stream...');

      // Handle streaming response
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let accumulatedContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            
            try {
              const parsed = JSON.parse(data);
              const content = parsed.choices[0]?.delta?.content || '';
              if (content) {
                accumulatedContent += content;
                // Update the assistant message with accumulated content
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessageId 
                    ? { ...msg, content: accumulatedContent }
                    : msg
                ));
                
                // Process TTS if enabled and this is an assistant message
                if (isTTSEnabled) {
                  ttsService.processStreamingText(content, assistantMessageId);
                }
              }
            } catch (e) {
              // Skip invalid JSON
              console.error('Error parsing streaming data:', e);
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Request aborted');
      } else {
        console.error('Error calling API:', error);
        // Only update the assistant message with error if the messages still exist
        // (they would have been removed if max retries were reached)
        setMessages(prev => {
          const assistantMessageExists = prev.some(msg => msg.id === assistantMessageId);
          if (assistantMessageExists) {
            return prev.map(msg => 
              msg.id === assistantMessageId 
                ? { ...msg, content: `Sorry, I encountered an error with the Kairix server. Please try again.` }
                : msg
            );
          }
          return prev;
        });
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
      
      // Finish TTS streaming
      if (isTTSEnabled) {
        ttsService.finishStreaming();
      }
    }
  }, [input, isLoading, messages, selectedModel, isTTSEnabled, ttsService]);

  // Update the ref when handleSubmit changes
  useEffect(() => {
    handleSubmitRef.current = handleSubmit;
  }, [handleSubmit]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setInput(e.target.value);
  }, []);

  // Handle STT state changes - stream text directly to input
  useEffect(() => {
    console.log('STT State changed:', sttState);
    
    // Stream interim results directly to input box - this accumulates all text
    if (sttState.status === 'listening' && sttState.interimTranscript) {
      console.log('Streaming accumulated transcript:', sttState.interimTranscript);
      setInput(sttState.interimTranscript);
    }
    
    // Handle final transcription and auto-submit
    if (sttState.status === 'transcribed' && sttState.transcript) {
      console.log('Final accumulated transcript:', sttState.transcript);
      
      // Set the input first
      setInput(sttState.transcript);
      
      // Auto-submit by programmatically clicking the submit button
      setTimeout(() => {
        const submitButton = document.querySelector('button[type="submit"]');
        if (submitButton instanceof HTMLButtonElement) {
          submitButton.click();
        }
        sttService.resetState();
      }, 100);
    }
  }, [sttState, sttService]);

  const clearChat = useCallback(() => {
    setMessages([]);
    if (selectedModel) {
      ChatStorage.clearSession('kairix-server', selectedModel);
    }
  }, [selectedModel]);

  const stop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
    }
    // Also stop TTS
    ttsService.stop();
  }, [ttsService]);

  return {
    messages,
    input,
    isLoading,
    handleSubmit,
    handleInputChange,
    setInput,
    stop,
    clearChat,
    handleSTTToggle,
    currentAssistantMessageIdRef,
    handleSubmitRef,
  };
}
