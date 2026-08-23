<template>
  <div class="archive-list">
    <div class="card">
      <div class="card-header">
        <h2>Archives</h2>
        <button @click="fetchArchives" class="btn btn-secondary" :disabled="loading">
          {{ loading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>

      <div v-if="loading && archives.length === 0" class="loading">
        Loading archives...
      </div>

      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <div v-else-if="archives.length === 0" class="empty-state">
        <p>No archives found on disk.</p>
      </div>

      <table v-else class="archives-table">
        <thead>
          <tr>
            <th>Archive</th>
            <th>Size</th>
            <th>Export</th>
            <th>Source</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="archive in archives" :key="archive.filename">
            <tr class="archive">
              <td class="archive-name">{{ archive.filename }}</td>
              <td class="archive-size">{{ formatSize(archive.size_bytes) }}</td>
              <td class="archive-timestamp">{{ archive.export_timestamp || '—' }}</td>
              <td>
                <span class="archive-source" :class="archive.source">{{ archive.source }}</span>
              </td>
              <td class="archive-status">{{ archive.extract_status }}</td>
              <td>
                <button
                  class="extract-btn btn btn-secondary"
                  :disabled="busy[archive.filename]"
                  @click="extractArchive(archive.filename)"
                >
                  {{ busy[archive.filename] ? '…' : 'Extract' }}
                </button>
                <button
                  class="timeline-btn btn btn-secondary"
                  :disabled="busy[archive.filename]"
                  @click="loadTimeline(archive.filename)"
                >
                  {{ busy[archive.filename] ? '…' : 'Timeline' }}
                </button>
                <button class="delete-btn btn btn-danger" @click="startDelete(archive.filename)">
                  Delete
                </button>
                <span v-if="notices[archive.filename]" class="action-notice">
                  {{ notices[archive.filename] }}
                </span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <div v-if="pendingDelete" class="delete-confirm">
      <div class="delete-confirm-box">
        <h3>Delete this archive?</h3>
        <p class="delete-name">{{ pendingDelete }}</p>
        <p class="delete-warning">
          This permanently removes a backup archive from disk. Check the
          <strong>Timeline</strong> tab first — an export flagged <strong>fully covered</strong>
          is safe to delete; otherwise you may be removing the only copy of some months.
        </p>
        <div class="delete-actions">
          <button class="cancel-delete-btn btn btn-secondary" @click="cancelDelete">Cancel</button>
          <button class="confirm-delete-btn btn btn-danger" @click="confirmDelete">
            Delete permanently
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'ArchiveList',
  setup() {
    const archives = ref([])
    const loading = ref(false)
    const error = ref(null)
    const busy = ref({})
    const notices = ref({})

    const setBusy = (filename, value) => {
      const next = { ...busy.value }
      if (value) next[filename] = true
      else delete next[filename]
      busy.value = next
    }
    const setNotice = (filename, message) => {
      notices.value = { ...notices.value, [filename]: message }
    }

    const fetchArchives = async () => {
      try {
        loading.value = true
        error.value = null
        const response = await axios.get('/api/archives')
        archives.value = response.data
      } catch (err) {
        error.value = 'Failed to load archives'
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    const extractArchive = async (filename) => {
      setBusy(filename, true)
      try {
        await axios.post(`/api/archives/${encodeURIComponent(filename)}/extract`)
        setNotice(filename, 'Extraction queued')
        await fetchArchives()
      } catch (err) {
        setNotice(filename, 'Extraction failed')
        console.error(err)
      } finally {
        setBusy(filename, false)
      }
    }

    const pendingDelete = ref(null)

    const startDelete = (filename) => {
      pendingDelete.value = filename
    }

    const cancelDelete = () => {
      pendingDelete.value = null
    }

    const confirmDelete = async () => {
      const filename = pendingDelete.value
      pendingDelete.value = null
      try {
        await axios.delete(`/api/archives/${encodeURIComponent(filename)}`)
        await fetchArchives()
      } catch (err) {
        error.value = 'Failed to delete archive'
        console.error(err)
      }
    }

    // Request a background scan; the result shows on the Timeline tab.
    const loadTimeline = async (filename) => {
      setBusy(filename, true)
      try {
        await axios.post(`/api/archives/${encodeURIComponent(filename)}/timeline`)
        setNotice(filename, 'Timeline scan requested — see the Timeline tab')
      } catch (err) {
        setNotice(filename, 'Timeline request failed')
        console.error(err)
      } finally {
        setBusy(filename, false)
      }
    }

    const formatSize = (bytes) => {
      if (bytes < 1024) return `${bytes} B`
      const units = ['KB', 'MB', 'GB', 'TB']
      let value = bytes / 1024
      let unit = 0
      while (value >= 1024 && unit < units.length - 1) {
        value /= 1024
        unit += 1
      }
      return `${value.toFixed(1)} ${units[unit]}`
    }

    onMounted(fetchArchives)

    return {
      archives, loading, error, pendingDelete, busy, notices,
      fetchArchives, extractArchive, formatSize, loadTimeline,
      startDelete, cancelDelete, confirmDelete,
    }
  },
}
</script>

<style scoped>
.archive-list {
  padding: 2rem 0;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.card-header h2 {
  margin: 0;
  color: #333;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading,
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #999;
}

.alert-error {
  padding: 1rem;
  border-radius: 4px;
  background: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

.archives-table {
  width: 100%;
  border-collapse: collapse;
}

.archives-table th,
.archives-table td {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #eee;
}

.archives-table th {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #999;
}

.archive-name {
  font-family: monospace;
  color: #333;
}

.archive-source {
  padding: 0.15rem 0.6rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.archive-source.db {
  background: #d1e7dd;
  color: #0a3622;
}

.archive-source.disk {
  background: #fff3cd;
  color: #856404;
}
</style>
