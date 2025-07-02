import { getStoredApiKey } from './auth';

interface FetchWithRetryOptions extends RequestInit {
  maxRetries?: number;
  onRetryAttempt?: (attempt: number, error: Error, nextDelay: number) => void;
  onMaxRetriesReached?: (error: Error) => void;
}

export async function authenticatedFetch(
  url: string, 
  options: FetchWithRetryOptions = {}
): Promise<Response> {
  const apiKey = getStoredApiKey();
  const { 
    maxRetries = 3, 
    onRetryAttempt,
    onMaxRetriesReached,
    ...fetchOptions 
  } = options;
  
  const headers = new Headers(fetchOptions.headers);
  
  // Add auth header if we have an API key
  if (apiKey) {
    headers.set('X-API-Key', apiKey);
  }
  
  let lastError: Error | null = null;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(url, {
        ...fetchOptions,
        headers
      });
      
      // Don't retry on client errors (4xx)
      if (response.status >= 400 && response.status < 500) {
        return response;
      }
      
      // If successful or non-retryable error, return
      if (response.ok || attempt === maxRetries - 1) {
        return response;
      }
      
      // Server error (5xx), continue to retry logic
      lastError = new Error(`HTTP ${response.status}: ${response.statusText}`);
      
    } catch (error) {
      lastError = error as Error;
      
      // Don't retry on abort
      if (error instanceof Error && error.name === 'AbortError') {
        throw error;
      }
    }
    
    // Calculate delay with exponential backoff
    // Delays: 1s, 4s, 16s (total ~21s for 3 attempts, but we'll cap at 10s per delay)
    const baseDelay = 1000; // 1 second
    const delay = Math.min(baseDelay * Math.pow(2, attempt * 2), 10000); // Cap at 10s
    
    // If this isn't the last attempt, wait before retrying
    if (attempt < maxRetries - 1) {
      if (onRetryAttempt) {
        onRetryAttempt(attempt + 1, lastError!, delay);
      }
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  // All retries exhausted
  if (onMaxRetriesReached && lastError) {
    onMaxRetriesReached(lastError);
  }
  
  throw lastError || new Error('Request failed after all retries');
}