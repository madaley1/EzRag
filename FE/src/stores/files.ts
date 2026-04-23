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
      const data = await res.json()
      files.value = data.files
    } catch (e) {
      error.value = String(e)
    } finally {
      loading.value = false
    }
  }

  async function deleteFile(path: string) {
    try {
      await fetch(`${API_URL}/files?path=${encodeURIComponent(path)}`, { method: 'DELETE' })
      files.value = files.value.filter((f) => f.source !== path)
    } catch (e) {
      error.value = String(e)
    }
  }

  return { files, loading, error, fetchFiles, deleteFile }
})
