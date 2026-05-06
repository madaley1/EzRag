<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useStatusStore } from './stores/status'

const status = useStatusStore()
onMounted(() => status.start())
onUnmounted(() => status.stop())
</script>

<template>
  <div class="app-shell">
    <nav class="sidebar">
      <div class="logo">EZRag</div>

      <RouterLink to="/chat" class="nav-link">
        Chat
        <span
          v-if="status.model.state === 'loading'"
          class="nav-badge loading"
          :title="status.model.message"
        >
          {{ Math.round(status.model.progress * 100) }}%
        </span>
        <span v-else-if="status.model.state === 'error'" class="nav-badge error" title="Model error">!</span>
      </RouterLink>

      <RouterLink to="/files" class="nav-link">
        Files
        <span
          v-if="status.ingestion.state === 'running'"
          class="nav-badge loading"
          :title="`Indexing ${status.ingestion.files_done}/${status.ingestion.files_total} files`"
        >
          {{ status.ingestion.files_done }}/{{ status.ingestion.files_total }}
        </span>
      </RouterLink>

      <!-- Status footer -->
      <div class="status-footer">
        <div class="status-row" v-if="status.model.state !== 'idle'">
          <span class="dot" :class="status.model.state" />
          <span class="status-label">
            {{
              status.model.state === 'loading'
                ? `Model ${Math.round(status.model.progress * 100)}%`
                : status.model.state === 'ready'
                  ? 'Model ready'
                  : status.model.state === 'error'
                    ? 'Model error'
                    : ''
            }}
          </span>
        </div>
        <div class="status-row" v-if="status.ingestion.state !== 'idle'">
          <span class="dot" :class="status.ingestion.state" />
          <span class="status-label">
            {{
              status.ingestion.state === 'running'
                ? `Indexing ${status.ingestion.files_done}/${status.ingestion.files_total}`
                : 'Index ready'
            }}
          </span>
        </div>
      </div>
    </nav>

    <main class="main-content">
      <div v-if="!status.backendReachable" class="connectivity-banner">
        Waiting for backend to start…
      </div>
      <RouterView />
    </main>
  </div>
</template>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body,
#app {
  height: 100%;
  margin: 0;
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  font-size: 16px;
  background: #f8fafc;
  color: #1e293b;
}
</style>

<style scoped>
.app-shell {
  display: flex;
  height: 100%;
}

.sidebar {
  width: 180px;
  flex-shrink: 0;
  background: #1e293b;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  gap: 0.5rem;
}

.logo {
  font-size: 1.2rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 1rem;
  letter-spacing: -0.02em;
}

.nav-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.45rem 0.75rem;
  border-radius: 6px;
  text-decoration: none;
  color: #94a3b8;
  font-size: 0.9rem;
  transition: background 0.15s, color 0.15s;
}

.nav-link:hover {
  background: #334155;
  color: #f1f5f9;
}

.nav-link.router-link-active {
  background: #2563eb;
  color: #fff;
}

.nav-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.1rem 0.35rem;
  border-radius: 999px;
  line-height: 1.4;
}

.nav-badge.loading {
  background: #f59e0b;
  color: #1e293b;
}

.nav-badge.error {
  background: #ef4444;
  color: #fff;
}

/* Status footer */
.status-footer {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot.loading  { background: #f59e0b; animation: pulse 1.2s ease-in-out infinite; }
.dot.ready    { background: #4ade80; }
.dot.done     { background: #4ade80; }
.dot.error    { background: #ef4444; }
.dot.running  { background: #f59e0b; animation: pulse 1.2s ease-in-out infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

.status-label {
  font-size: 0.72rem;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.main-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.connectivity-banner {
  background: #fef3c7;
  color: #92400e;
  padding: 0.6rem 1rem;
  font-size: 0.85rem;
  font-weight: 500;
  text-align: center;
  border-bottom: 1px solid #fde68a;
}
</style>
