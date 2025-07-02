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
    url: "http://mbp.thrush-escalator.ts.net:8000",
    apiKey: ""
  },

  {
    name: "Ollama (Kairix)",
    url: "https://ollama.kairix.net/v1",
    apiKey: "key-1244"
  }
]
