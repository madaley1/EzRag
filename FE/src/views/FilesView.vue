<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useFilesStore } from '../stores/files'
import { useStatusStore } from '../stores/status'

const store = useFilesStore()
const status = useStatusStore()

const activeFiles = computed(() => store.files.filter((f) => !f.deleted))
const deletedFiles = computed(() => store.files.filter((f) => f.deleted))

const ingestionPct = computed(() => Math.round(status.ingestion.progress * 100))

onMounted(() => store.fetchFiles())
</script>

<template>
  <div class="files-view">
    <div class="header-row">
      <h2>Knowledge Base Files</h2>
      <button @click="store.fetchFiles" :disabled="store.loading">
        {{ store.loading ? 'Refreshing…' : 'Refresh' }}
      </button>
    </div>

    <!-- Ingestion progress bar -->
    <div v-if="status.ingestion.state === 'running'" class="ingest-banner">
      <div class="banner-text">
        <span>Indexing files… {{ ingestionPct }}%</span>
        <span class="banner-count">
          {{ status.ingestion.files_done }} / {{ status.ingestion.files_total }} files
        </span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${ingestionPct}%` }" />
      </div>
    </div>

    <div v-if="store.error" class="error-banner">{{ store.error }}</div>

    <section v-if="activeFiles.length">
      <h3>Active ({{ activeFiles.length }})</h3>
      <ul class="file-list">
        <li v-for="f in activeFiles" :key="f.source" class="file-item">
          <span class="filename">{{ f.filename }}</span>
          <span class="source" :title="f.source">{{ f.source }}</span>
        </li>
      </ul>
    </section>

    <section v-if="deletedFiles.length" class="deleted-section">
      <h3>Deleted from disk ({{ deletedFiles.length }})</h3>
      <p class="hint">
        These files have been removed from the filesystem. Their vectors remain in the knowledge
        base until you purge them.
      </p>
      <ul class="file-list">
        <li v-for="f in deletedFiles" :key="f.source" class="file-item deleted">
          <div class="file-info">
            <span class="filename">{{ f.filename }}</span>
            <span class="source" :title="f.source">{{ f.source }}</span>
          </div>
          <button class="danger" @click="store.deleteFile(f.source)">Purge from DB</button>
        </li>
      </ul>
    </section>

    <div
      v-if="!store.loading && !activeFiles.length && !deletedFiles.length"
      class="empty-state"
    >
      <template v-if="status.ingestion.state === 'running'">
        Indexing in progress — files will appear here as they are processed.
      </template>
      <template v-else>
        No files have been ingested yet. Mount directories in docker-compose and they will appear
        here after ingestion.
      </template>
    </div>
  </div>
</template>

<style scoped>
.files-view {
  padding: 1.5rem;
  max-width: 860px;
}

.header-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

h2 { margin: 0; font-size: 1.25rem; color: #1e293b; }
h3 { font-size: 1rem; color: #475569; margin: 1.5rem 0 0.5rem; }

/* Ingestion banner */
.ingest-banner {
  margin-bottom: 1rem;
  padding: 0.6rem 0.75rem;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.banner-text {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  font-weight: 600;
  color: #1d4ed8;
}

.banner-count {
  font-weight: 400;
  color: #3b82f6;
}

.progress-track {
  height: 4px;
  background: #bfdbfe;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 999px;
  transition: width 0.5s ease;
}

.hint {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 0.75rem;
}

.error-banner {
  background: #fee2e2;
  color: #991b1b;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.file-item.deleted {
  background: #fff7ed;
  border-color: #fed7aa;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.filename {
  font-weight: 600;
  font-size: 0.9rem;
  color: #1e293b;
}

.source {
  font-size: 0.75rem;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deleted-section .file-item .filename {
  text-decoration: line-through;
  color: #9ca3af;
}

button {
  padding: 0.35rem 0.75rem;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  font-size: 0.85rem;
  cursor: pointer;
  white-space: nowrap;
}

button:disabled { opacity: 0.4; cursor: not-allowed; }
button.danger { background: #ef4444; }

.empty-state {
  color: #94a3b8;
  margin-top: 3rem;
  text-align: center;
  font-size: 0.95rem;
}
</style>
