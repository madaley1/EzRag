import { ref } from 'vue'
import { defineStore } from 'pinia'

export interface Source {
  source: string
  filename: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  error?: boolean
}

const WS_URL = (import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000') + '/ws/chat'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const pending = ref(false)
  const connected = ref(false)

  let socket: WebSocket | null = null

  function connect() {
    if (socket && socket.readyState <= WebSocket.OPEN) return

    socket = new WebSocket(WS_URL)

    socket.onopen = () => {
      connected.value = true
    }

    socket.onclose = () => {
      connected.value = false
      socket = null
      // Reconnect after 3 s
      setTimeout(connect, 3000)
    }

    socket.onerror = () => {
      socket?.close()
    }

    socket.onmessage = (event) => {
      pending.value = false
      const data = JSON.parse(event.data)
      if (data.type === 'answer') {
        messages.value.push({
          role: 'assistant',
          content: data.content,
          sources: data.sources ?? [],
        })
      } else if (data.type === 'error') {
        messages.value.push({
          role: 'assistant',
          content: data.content,
          error: true,
        })
      }
    }
  }

  function send(text: string) {
    if (!text.trim() || pending.value) return
    messages.value.push({ role: 'user', content: text })
    pending.value = true

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      connect()
      const wait = setInterval(() => {
        if (socket?.readyState === WebSocket.OPEN) {
          clearInterval(wait)
          socket.send(JSON.stringify({ message: text }))
        }
      }, 100)
    } else {
      socket.send(JSON.stringify({ message: text }))
    }
  }

  function clear() {
    messages.value = []
  }

  return { messages, pending, connected, connect, send, clear }
})
