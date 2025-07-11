export interface ContextRequest {
  id: string
  timestamp: number
  method: string
  url: string
  headers: HeadersInit
  body: any
  response?: {
    status: number
    statusText: string
    body: any
    timestamp: number
  }
}

export class ContextDebugStore {
  private static instance: ContextDebugStore
  private requests: ContextRequest[] = []
  private maxRequests = 100 // Keep last 100 requests
  private listeners: ((requests: ContextRequest[]) => void)[] = []
  
  private constructor() {}
  
  static getInstance(): ContextDebugStore {
    if (!ContextDebugStore.instance) {
      ContextDebugStore.instance = new ContextDebugStore()
    }
    return ContextDebugStore.instance
  }
  
  addRequest(request: Omit<ContextRequest, 'id' | 'timestamp'>): string {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const newRequest: ContextRequest = {
      ...request,
      id,
      timestamp: Date.now()
    }
    
    this.requests.unshift(newRequest) // Add to beginning
    
    // Keep only the last maxRequests
    if (this.requests.length > this.maxRequests) {
      this.requests = this.requests.slice(0, this.maxRequests)
    }
    
    this.notifyListeners()
    return id
  }
  
  updateRequestResponse(id: string, response: ContextRequest['response']): void {
    const request = this.requests.find(r => r.id === id)
    if (request) {
      request.response = response
      this.notifyListeners()
    }
  }
  
  getRequests(): ContextRequest[] {
    return [...this.requests]
  }
  
  clearRequests(): void {
    this.requests = []
    this.notifyListeners()
  }
  
  subscribe(listener: (requests: ContextRequest[]) => void): () => void {
    this.listeners.push(listener)
    
    // Immediately call with current state
    listener(this.getRequests())
    
    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener)
    }
  }
  
  private notifyListeners(): void {
    const requests = this.getRequests()
    this.listeners.forEach(listener => listener(requests))
  }
}