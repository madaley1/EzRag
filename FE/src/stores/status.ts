import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export interface ModelStatus {
  state: 'idle' | 'loading' | 'ready' | 'error'
  progress: number
  message: string
}

export interface IngestionStatus {
  state: 'idle' | 'running' | 'done'
  progress: number
  files_done: number
  files_total: number
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const POLL_INTERVAL_ACTIVE = 2000   // while something is loading
const POLL_INTERVAL_IDLE = 30_000   // once everything is ready

export const useStatusStore = defineStore('status', () => {
  const model = ref<ModelStatus>({ state: 'idle', progress: 0, message: '' })
  const ingestion = ref<IngestionStatus>({
    state: 'idle',
    progress: 0,
    files_done: 0,
    files_total: 0,
  })

  const isAnythingLoading = computed(
    () => model.value.state === 'loading' || ingestion.value.state === 'running',
  )

  let timer: ReturnType<typeof setTimeout> | null = null

  async function fetch() {
    try {
      const res = await window.fetch(`${API_URL}/status`)
      if (!res.ok) return
      const data = await res.json()
      model.value = data.model
      ingestion.value = data.ingestion
    } catch {
      // Backend not reachable yet — silently retry
    } finally {
      schedule()
    }
  }

  function schedule() {
    if (timer) clearTimeout(timer)
    timer = setTimeout(fetch, isAnythingLoading.value ? POLL_INTERVAL_ACTIVE : POLL_INTERVAL_IDLE)
  }

  function start() {
    fetch() // immediate first fetch
  }

  function stop() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  return { model, ingestion, isAnythingLoading, start, stop }
})
