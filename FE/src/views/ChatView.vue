<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import { useStatusStore } from '../stores/status'

const chat = useChatStore()
const status = useStatusStore()
const input = ref('')
const messagesEl = ref<HTMLElement | null>(null)

onMounted(() => chat.connect())

watch(
  () => chat.messages.length,
  async () => {
    await nextTick()
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  },
)

const modelBlocked = computed(() => status.model.state === 'loading')
const inputDisabled = computed(() => chat.pending || modelBlocked.value)

const modelProgressPct = computed(() => Math.round(status.model.progress * 100))

function submit() {
  const text = input.value.trim()
  if (!text || inputDisabled.value) return
  chat.send(text)
  input.value = ''
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <div class="chat-view">
    <!-- Model loading banner -->
    <div v-if="modelBlocked" class="loading-banner">
      <div class="banner-text">
        <span>Loading model… {{ modelProgressPct }}%</span>
        <span class="banner-sub">{{ status.model.message }}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${modelProgressPct}%` }" />
      </div>
    </div>

    <div v-if="status.model.state === 'error'" class="error-banner">
      Model failed to load: {{ status.model.message }}
    </div>

    <div class="messages" ref="messagesEl">
      <div v-if="chat.messages.length === 0" class="empty-state">
        <template v-if="modelBlocked">
          Model is warming up — you can ask a question once it finishes loading.
        </template>
        <template v-else>Ask a question about your documents.</template>
      </div>

      <div
        v-for="(msg, i) in chat.messages"
        :key="i"
        class="message"
        :class="[msg.role, { error: msg.error }]"
      >
        <div class="bubble">{{ msg.content }}</div>
        <div v-if="msg.sources && msg.sources.length" class="sources">
          <span class="sources-label">Sources:</span>
          <span v-for="(s, j) in msg.sources" :key="j" class="source-chip" :title="s.source">
            {{ s.filename }}
          </span>
        </div>
      </div>

      <div v-if="chat.pending" class="message assistant">
        <div class="bubble thinking">Thinking…</div>
      </div>
    </div>

    <div class="input-bar">
      <span class="ws-dot" :class="{ connected: chat.connected }" />
      <textarea
        v-model="input"
        :placeholder="modelBlocked ? `Model loading (${modelProgressPct}%)…` : 'Ask a question…'"
        rows="2"
        @keydown="onKeydown"
        :disabled="inputDisabled"
      />
      <button @click="submit" :disabled="inputDisabled || !input.trim()">Send</button>
      <button class="secondary" @click="chat.clear" :disabled="chat.pending">Clear</button>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* Model loading banner */
.loading-banner {
  padding: 0.6rem 1rem;
  background: #fffbeb;
  border-bottom: 1px solid #fde68a;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.banner-text {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 0.85rem;
  color: #92400e;
  font-weight: 600;
}

.banner-sub {
  font-size: 0.75rem;
  font-weight: 400;
  color: #b45309;
}

.progress-track {
  height: 4px;
  background: #fde68a;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #f59e0b;
  border-radius: 999px;
  transition: width 0.5s ease;
}

.error-banner {
  padding: 0.5rem 1rem;
  background: #fee2e2;
  border-bottom: 1px solid #fca5a5;
  font-size: 0.85rem;
  color: #991b1b;
}

/* Messages */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empty-state {
  color: #94a3b8;
  text-align: center;
  margin-top: 4rem;
  font-size: 0.95rem;
}

.message {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.message.user     { align-items: flex-end; }
.message.assistant { align-items: flex-start; }

.bubble {
  max-width: 72%;
  padding: 0.6rem 0.9rem;
  border-radius: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.message.user .bubble {
  background: #2563eb;
  color: #fff;
  border-bottom-right-radius: 3px;
}

.message.assistant .bubble {
  background: #f1f5f9;
  color: #1e293b;
  border-bottom-left-radius: 3px;
}

.message.error .bubble {
  background: #fee2e2;
  color: #991b1b;
}

.thinking {
  opacity: 0.6;
  font-style: italic;
}

.sources {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  align-items: center;
  max-width: 72%;
}

.sources-label {
  font-size: 0.75rem;
  color: #64748b;
}

.source-chip {
  font-size: 0.7rem;
  background: #e2e8f0;
  color: #475569;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  cursor: default;
}

/* Input bar */
.input-bar {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
  padding: 1rem;
  border-top: 1px solid #e2e8f0;
  background: #fff;
}

.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f87171;
  flex-shrink: 0;
  margin-bottom: 0.6rem;
  transition: background 0.3s;
}

.ws-dot.connected { background: #4ade80; }

textarea {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.95rem;
  resize: none;
  outline: none;
  font-family: inherit;
}

textarea:focus { border-color: #2563eb; }
textarea:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }

button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  font-size: 0.9rem;
  cursor: pointer;
  white-space: nowrap;
}

button:disabled { opacity: 0.4; cursor: not-allowed; }
button.secondary { background: #e2e8f0; color: #475569; }
</style>
