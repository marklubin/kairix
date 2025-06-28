export interface Endpoint {
  name: string
  url: string
  apiKey: string
}

export interface Model {
  id: string
  object: string
  created: number
  owned_by: string
}

export const ENDPOINTS: Endpoint[] = [
  {
    name: "Local Server",
    url: "http://localhost:8000/v1",
    apiKey: ""
  },
  {
    name: "OpenAI",
    url: "https://api.openai.com/v1",
    apiKey: "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"
  },
  {
    name: "Ollama (Kairix)",
    url: "https://ollama.kairix.net/v1",
    apiKey: "key-1244"
  }
]