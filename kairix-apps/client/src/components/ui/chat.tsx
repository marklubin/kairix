import * as React from "react"
import { Send, StopCircle, Mic, MicOff, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import type { Message } from "ai"
import type { STTState } from "@/services/stt/types"

interface ChatProps {
  messages: Message[]
  input: string
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
  handleSubmit: (e?: React.FormEvent) => void
  isGenerating: boolean
  stop: () => void
  sttState: STTState
  onSTTToggle: () => void
  inputRef?: React.RefObject<HTMLInputElement | null>
}

export function Chat({
  messages,
  input,
  handleInputChange,
  handleSubmit,
  isGenerating,
  stop,
  sttState,
  onSTTToggle,
  inputRef: externalInputRef
}: ChatProps) {
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const internalInputRef = React.useRef<HTMLInputElement>(null)
  const inputRef = externalInputRef || internalInputRef

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Show loading indicator in input when STT is processing
  const isSTTActive = sttState.status === 'listening' || sttState.status === 'processing'
  const showSTTPlaceholder = isSTTActive && !input

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-8">
            <p className="text-sm">Start a conversation to begin</p>
          </div>
        )}
        {messages.map((message, index) => (
          <div
            key={message.id}
            className={cn(
              "flex",
              message.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[80%] rounded-lg px-4 py-2",
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              )}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              {/* Show loading indicator for empty assistant messages */}
              {message.role === "assistant" && 
               message.content === "" && 
               isGenerating && 
               index === messages.length - 1 && (
                <div className="flex items-center gap-2 mt-2">
                  <Spinner className="h-3 w-3" />
                  <span className="text-xs text-muted-foreground">Generating...</span>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input Form */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={handleInputChange}
              placeholder={showSTTPlaceholder ? "Listening..." : "Type a message..."}
              className={cn(
                "w-full px-3 py-2 pr-10 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-ring",
                isSTTActive && "text-muted-foreground"
              )}
              disabled={isGenerating || sttState.status === 'processing'}
            />
            {sttState.status === 'processing' && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            )}
          </div>
          
          {/* Push to Talk Button */}
          <Button
            type="button"
            size="icon"
            variant={sttState.status === 'listening' ? "destructive" : "outline"}
            onClick={onSTTToggle}
            disabled={isGenerating || sttState.status === 'processing'}
          >
            {sttState.status === 'listening' ? (
              <MicOff className="h-4 w-4" />
            ) : (
              <Mic className="h-4 w-4" />
            )}
          </Button>

          {/* Send/Stop Button */}
          {isGenerating ? (
            <Button 
              type="button" 
              size="icon" 
              variant="destructive"
              onClick={stop}
            >
              <StopCircle className="h-4 w-4" />
            </Button>
          ) : (
            <Button 
              type="submit" 
              size="icon" 
              disabled={!input.trim() && sttState.status !== 'transcribed'}
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>
      </form>
    </div>
  )
}