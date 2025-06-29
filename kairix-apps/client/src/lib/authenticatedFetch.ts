import { getStoredApiKey } from './auth';

export async function authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const apiKey = getStoredApiKey();
  
  const headers = new Headers(options.headers);
  
  // Add auth header if we have an API key
  if (apiKey) {
    headers.set('X-API-Key', apiKey);
  }
  
  return fetch(url, {
    ...options,
    headers
  });
}