const AUTH_KEY = 'kairix-auth-key';

export function getStoredApiKey(): string | null {
  return localStorage.getItem(AUTH_KEY);
}

export function setApiKey(key: string): void {
  localStorage.setItem(AUTH_KEY, key);
}

export function hasApiKey(): boolean {
  return !!getStoredApiKey();
}
