import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ContextDebugStore } from './ContextDebugStore'

describe('ContextDebugStore', () => {
  let store: ContextDebugStore
  
  beforeEach(() => {
    // Reset the singleton instance
    (ContextDebugStore as any).instance = undefined
    store = ContextDebugStore.getInstance()
  })
  
  it('should be a singleton', () => {
    const store1 = ContextDebugStore.getInstance()
    const store2 = ContextDebugStore.getInstance()
    expect(store1).toBe(store2)
  })
  
  it('should add requests and generate IDs', () => {
    const requestData = {
      method: 'POST',
      url: 'http://localhost:8000/test',
      headers: { 'Content-Type': 'application/json' },
      body: { test: 'data' }
    }
    
    const id = store.addRequest(requestData)
    
    expect(id).toBeTruthy()
    expect(typeof id).toBe('string')
    
    const requests = store.getRequests()
    expect(requests).toHaveLength(1)
    expect(requests[0]).toMatchObject({
      ...requestData,
      id,
      timestamp: expect.any(Number)
    })
  })
  
  it('should update request response', () => {
    const id = store.addRequest({
      method: 'GET',
      url: 'http://localhost:8000/test',
      headers: {},
      body: null
    })
    
    const response = {
      status: 200,
      statusText: 'OK',
      body: { success: true },
      timestamp: Date.now()
    }
    
    store.updateRequestResponse(id, response)
    
    const requests = store.getRequests()
    expect(requests[0].response).toEqual(response)
  })
  
  it('should maintain request order with newest first', () => {
    const id1 = store.addRequest({
      method: 'GET',
      url: 'http://localhost:8000/test1',
      headers: {},
      body: null
    })
    
    const id2 = store.addRequest({
      method: 'GET',
      url: 'http://localhost:8000/test2',
      headers: {},
      body: null
    })
    
    const requests = store.getRequests()
    expect(requests[0].id).toBe(id2)
    expect(requests[1].id).toBe(id1)
  })
  
  it('should limit requests to maxRequests', () => {
    // Add more than max requests (100)
    for (let i = 0; i < 105; i++) {
      store.addRequest({
        method: 'GET',
        url: `http://localhost:8000/test${i}`,
        headers: {},
        body: null
      })
    }
    
    const requests = store.getRequests()
    expect(requests).toHaveLength(100)
    
    // Verify newest requests are kept
    expect(requests[0].url).toContain('test104')
    expect(requests[99].url).toContain('test5')
  })
  
  it('should clear all requests', () => {
    store.addRequest({
      method: 'GET',
      url: 'http://localhost:8000/test',
      headers: {},
      body: null
    })
    
    expect(store.getRequests()).toHaveLength(1)
    
    store.clearRequests()
    
    expect(store.getRequests()).toHaveLength(0)
  })
  
  it('should notify subscribers on changes', () => {
    const listener = vi.fn()
    const unsubscribe = store.subscribe(listener)
    
    // Should be called immediately with current state
    expect(listener).toHaveBeenCalledTimes(1)
    expect(listener).toHaveBeenCalledWith([])
    
    // Add request
    store.addRequest({
      method: 'GET',
      url: 'http://localhost:8000/test',
      headers: {},
      body: null
    })
    
    expect(listener).toHaveBeenCalledTimes(2)
    expect(listener).toHaveBeenLastCalledWith(expect.arrayContaining([
      expect.objectContaining({
        method: 'GET',
        url: 'http://localhost:8000/test'
      })
    ]))
    
    // Clear requests
    store.clearRequests()
    expect(listener).toHaveBeenCalledTimes(3)
    expect(listener).toHaveBeenLastCalledWith([])
    
    // Unsubscribe
    unsubscribe()
    
    // Should not be called after unsubscribe
    store.addRequest({
      method: 'POST',
      url: 'http://localhost:8000/test2',
      headers: {},
      body: null
    })
    
    expect(listener).toHaveBeenCalledTimes(3)
  })
  
  it('should handle multiple subscribers', () => {
    const listener1 = vi.fn()
    const listener2 = vi.fn()
    
    store.subscribe(listener1)
    store.subscribe(listener2)
    
    store.addRequest({
      method: 'GET',
      url: 'http://localhost:8000/test',
      headers: {},
      body: null
    })
    
    expect(listener1).toHaveBeenCalledTimes(2)
    expect(listener2).toHaveBeenCalledTimes(2)
  })
  
  it('should return a copy of requests', () => {
    store.addRequest({
      method: 'GET',
      url: 'http://localhost:8000/test',
      headers: {},
      body: { data: 'test' }
    })
    
    const requests1 = store.getRequests()
    const requests2 = store.getRequests()
    
    expect(requests1).not.toBe(requests2)
    expect(requests1).toEqual(requests2)
    
    // Modifying the returned array should not affect the store
    requests1.push({} as any)
    expect(store.getRequests()).toHaveLength(1)
  })
})