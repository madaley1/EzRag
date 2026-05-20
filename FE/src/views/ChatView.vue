<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { useChatStore, type Rigidity } from '../stores/chat'
import { useStatusStore } from '../stores/status'

const chat = useChatStore()
const status = useStatusStore()
const input = ref('')
const messagesEl = ref<HTMLElement | null>(null)
const drawerOpen = ref(false)

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

function setRigidity(val: Rigidity) {
  chat.settings.rigidity = val
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
        <div v-if="msg.stored" class="stored-badge">📝 Saved to notes</div>
      </div>

      <div v-if="chat.pending" class="message assistant">
        <div class="bubble thinking">Thinking…</div>
      </div>
    </div>

    <!-- Settings drawer -->
    <transition name="drawer">
      <div v-if="drawerOpen" class="settings-drawer">
        <div class="drawer-header">
          <span>Query Settings</span>
          <button class="drawer-close" @click="drawerOpen = false">&times;</button>
        </div>

        <div class="setting-group">
          <label class="setting-label">
            Rigidity
            <span class="tooltip-wrap">
              <span class="tooltip-icon">?</span>
              <span class="tooltip-text">Controls how strictly answers must match your documents. Strict only uses strong matches; Suggestive offers nearby topics; Weak allows inference beyond your docs.</span>
            </span>
          </label>
          <div class="rigidity-toggle">
            <button
              class="rigidity-btn"
              :class="{ active: chat.settings.rigidity === 'strict' }"
              @click="setRigidity('strict')"
            >
              <span class="btn-label">Strict</span>
              <span class="btn-hint">Exact matches only — refuses if nothing found</span>
            </button>
            <button
              class="rigidity-btn"
              :class="{ active: chat.settings.rigidity === 'suggestive' }"
              @click="setRigidity('suggestive')"
            >
              <span class="btn-label">Suggestive</span>
              <span class="btn-hint">Suggests related topics when no strong match</span>
            </button>
            <button
              class="rigidity-btn"
              :class="{ active: chat.settings.rigidity === 'weak' }"
              @click="setRigidity('weak')"
            >
              <span class="btn-label">Weak</span>
              <span class="btn-hint">Allows inference and extrapolation from context</span>
            </button>
          </div>
        </div>

        <div class="setting-group">
          <label class="setting-label">
            <input type="checkbox" v-model="chat.settings.connectivity" />
            Connectivity
            <span class="tooltip-wrap">
              <span class="tooltip-icon">?</span>
              <span class="tooltip-text">When enabled, supplements your local documents with live web search results via SearXNG for broader context.</span>
            </span>
          </label>
        </div>

        <div class="setting-group">
          <label class="setting-label">
            <input type="checkbox" v-model="chat.settings.storage" />
            Storage
            <span class="tooltip-wrap">
              <span class="tooltip-icon">?</span>
              <span class="tooltip-text">When enabled, saves each answer as a timestamped Markdown note in your vault's generated folder.</span>
            </span>
          </label>
        </div>
      </div>
    </transition>

    <div class="input-bar">
      <div class="input-row">
        <span class="ws-dot" :class="{ connected: chat.connected }" />
        <textarea
          v-model="input"
          :placeholder="modelBlocked ? `Model loading (${modelProgressPct}%)…` : 'Ask a question…'"
          rows="2"
          @keydown="onKeydown"
          :disabled="inputDisabled"
        />
        <button class="icon-btn" @click="drawerOpen = !drawerOpen" title="Settings">⚙</button>
        <button @click="submit" :disabled="inputDisabled || !input.trim()">Send</button>
        <button class="secondary" @click="chat.clear" :disabled="chat.pending">Clear</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
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

.stored-badge {
  font-size: 0.72rem;
  color: #059669;
  margin-top: 0.15rem;
}

/* Settings drawer */
.settings-drawer {
  position: absolute;
  bottom: 5rem;
  right: 1rem;
  width: 280px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 1rem;
  z-index: 10;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  font-weight: 600;
  font-size: 0.9rem;
  color: #1e293b;
}

.drawer-close {
  background: none;
  border: none;
  font-size: 1.3rem;
  color: #64748b;
  cursor: pointer;
  padding: 0 0.3rem;
  line-height: 1;
}

.setting-group {
  margin-bottom: 0.75rem;
}

.setting-label {
  font-size: 0.82rem;
  font-weight: 500;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}



.rigidity-toggle {
  display: flex;
  gap: 2px;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 2px;
  margin-top: 0.3rem;
}

.rigidity-btn {
  padding: 0.4rem 0.5rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  font-size: 0.75rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
}

.rigidity-btn:hover { color: #334155; }

.rigidity-btn.active {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.btn-label {
  font-weight: 600;
  font-size: 0.75rem;
}

.btn-hint {
  font-size: 0.62rem;
  font-weight: 400;
  color: #94a3b8;
  line-height: 1.2;
}

.rigidity-btn.active .btn-hint {
  color: #60a5fa;
}

/* Tooltips */
.tooltip-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.tooltip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  font-size: 0.6rem;
  font-weight: 700;
  cursor: help;
}

.tooltip-text {
  display: none;
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  width: 200px;
  padding: 0.5rem 0.6rem;
  background: #1e293b;
  color: #f1f5f9;
  font-size: 0.68rem;
  font-weight: 400;
  line-height: 1.4;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 20;
}

.tooltip-text::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: #1e293b;
}

.tooltip-wrap:hover .tooltip-text {
  display: block;
}

/* Drawer transition */
.drawer-enter-active, .drawer-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.drawer-enter-from, .drawer-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

/* Input bar */
.input-bar {
  padding: 1rem;
  border-top: 1px solid #e2e8f0;
  background: #fff;
}

.input-row {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
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

.icon-btn {
  padding: 0.5rem 0.6rem;
  background: #f1f5f9;
  color: #475569;
  font-size: 1.1rem;
  line-height: 1;
}

.icon-btn:hover { background: #e2e8f0; }
</style>
