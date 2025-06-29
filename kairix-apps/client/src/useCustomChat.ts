import { useState, useCallback, useEffect, useRef } from 'react';
import type { Message } from 'ai';
import type { Endpoint, Model } from './types/config';
import { ENDPOINTS } from './types/config';
import { ChatStorage } from './lib/storage';
import { useTTS } from './contexts/TTSContext';
import { useSTT } from './contexts/STTContext';
import { authenticatedFetch } from './lib/authenticatedFetch';

export function useCustomChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedEndpoint, setSelectedEndpoint] = useState<Endpoint>(ENDPOINTS[0]);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [loadingModels, setLoadingModels] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const { ttsService, isEnabled: isTTSEnabled } = useTTS();
  const { sttService, sttState } = useSTT();
  const currentAssistantMessageIdRef = useRef<string | null>(null);

  // Load chat history when endpoint or model changes
  useEffect(() => {
    if (selectedEndpoint && selectedModel) {
      const savedMessages = ChatStorage.getSession(selectedEndpoint.name, selectedModel);
      setMessages(savedMessages);
    }
  }, [selectedEndpoint, selectedModel]);

  // Save chat history when messages change
  useEffect(() => {
    if (selectedEndpoint && selectedModel && messages.length > 0) {
      ChatStorage.saveSession(selectedEndpoint.name, selectedModel, messages);
    }
  }, [messages, selectedEndpoint, selectedModel]);

  // Fetch models when endpoint changes
  useEffect(() => {
    const fetchModels = async () => {
      setLoadingModels(true);
      try {
        const headers: HeadersInit = {
          'Content-Type': 'application/json',
        };
        
        if (selectedEndpoint.apiKey) {
          headers['Authorization'] = `Bearer ${selectedEndpoint.apiKey}`;
        }

        const response = await authenticatedFetch(`${selectedEndpoint.url}/models`, {
          headers,
        });

        if (response.ok) {
          const data = await response.json();
          setModels(data.data || []);
          // Set default model if available
          if (data.data && data.data.length > 0) {
            const defaultModel = data.data[0].id;
            setSelectedModel(defaultModel);
          }
        } else {
          console.error('Failed to fetch models');
          setModels([]);
        }
      } catch (error) {
        console.error('Error fetching models:', error);
        setModels([]);
      } finally {
        setLoadingModels(false);
      }
    };

    fetchModels();
  }, [selectedEndpoint]);

  const handleSTTToggle = useCallback(async () => {
    try {
      if (sttState.status === 'listening') {
        // Stop recording and get transcript
        await sttService.stopRecording();
      } else {
        // Interrupt TTS when starting STT
        if (isTTSEnabled && currentAssistantMessageIdRef.current) {
          ttsService.interruptMessage(currentAssistantMessageIdRef.current);
        }
        
        // Start recording
        await sttService.startRecording(currentAssistantMessageIdRef.current || undefined);
      }
    } catch (error) {
      console.error('STT toggle error:', error);
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
      };
      
      if (selectedEndpoint.apiKey) {
        headers['Authorization'] = `Bearer ${selectedEndpoint.apiKey}`;
      }

      // Get context messages (last 20) for API call
      const contextMessages = ChatStorage.getContextMessages([...messages, userMessage]);

      // Call the selected endpoint with streaming
      const response = await authenticatedFetch(`${selectedEndpoint.url}/chat/completions`, {
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
      });

      if (!response.ok) {
        throw new Error(`Failed to get response from ${selectedEndpoint.name}`);
      }

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
        // Update the assistant message with error
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? { ...msg, content: `Sorry, I encountered an error with ${selectedEndpoint.name}. Please try again.` }
            : msg
        ));
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
      
      // Finish TTS streaming
      if (isTTSEnabled) {
        ttsService.finishStreaming();
      }
    }
  }, [input, isLoading, messages, selectedEndpoint, selectedModel]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setInput(e.target.value);
  }, []);

  // Handle STT state changes - stream text directly to input
  useEffect(() => {
    console.log('STT State changed:', sttState);
    
    // Stream interim results directly to input box
    if (sttState.status === 'listening' && sttState.interimTranscript) {
      console.log('Streaming interim transcript:', sttState.interimTranscript);
      setInput(sttState.interimTranscript);
    }
    
    // Handle final transcription
    if (sttState.status === 'transcribed' && sttState.transcript) {
      console.log('Final transcript:', sttState.transcript);
      setInput(sttState.transcript);
      
      // Auto-submit if enabled
      if (sttService.isAutoSubmitEnabled()) {
        // Small delay to ensure input state is updated
        setTimeout(() => {
          console.log('Auto-submitting with input:', sttState.transcript);
          // Pass the transcript directly to handleSubmit
          handleSubmit(undefined, sttState.transcript);
        }, 100);
      }
    }
  }, [sttState, sttService, handleSubmit]);

  const handleEndpointChange = useCallback((endpoint: Endpoint) => {
    setSelectedEndpoint(endpoint);
  }, []);

  const handleModelChange = useCallback((modelId: string) => {
    setSelectedModel(modelId);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    if (selectedEndpoint && selectedModel) {
      ChatStorage.clearSession(selectedEndpoint.name, selectedModel);
    }
  }, [selectedEndpoint, selectedModel]);

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
    selectedEndpoint,
    handleEndpointChange,
    models,
    selectedModel,
    handleModelChange,
    loadingModels,
    stop,
    clearChat,
    handleSTTToggle,
  };
}