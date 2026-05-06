import { ref } from 'vue'
import { defineStore } from 'pinia'

export interface TrackedFile {
  source: string
  filename: string
  deleted: boolean
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const useFilesStore = defineStore('files', () => {
  const files = ref<TrackedFile[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchFiles() {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_URL}/files`)
      if (!res.ok) {
        error.value = `Server returned ${res.status} — the backend may still be starting up.`
        return
      }
      const data = await res.json()
      files.value = data.files
    } catch {
      error.value = 'Unable to reach the backend. It may still be initializing.'
    } finally {
      loading.value = false
    }
  }

  async function deleteFile(path: string) {
    try {
      const res = await fetch(`${API_URL}/files?path=${encodeURIComponent(path)}`, {
        method: 'DELETE',
      })
      if (!res.ok) {
        error.value = `Failed to delete file — server returned ${res.status}.`
        return
      }
      files.value = files.value.filter((f) => f.source !== path)
    } catch {
      error.value = 'Unable to reach the backend. It may still be initializing.'
    }
  }

  return { files, loading, error, fetchFiles, deleteFile }
})
