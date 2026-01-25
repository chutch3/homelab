<template>
  <div class="modal-overlay" @click="$emit('close')">
    <div class="modal" @click.stop>
      <div class="modal-header">
        <h2>Job Details: {{ job.job_id.substring(0, 12) }}...</h2>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <div class="job-info">
          <div class="info-row">
            <span class="label">Status:</span>
            <span :class="['status-badge', job.status]">{{ job.status }}</span>
          </div>
          <div class="info-row">
            <span class="label">Job ID:</span>
            <span class="value">{{ job.job_id }}</span>
          </div>
          <div class="info-row">
            <span class="label">User ID:</span>
            <span class="value">{{ job.user_id }}</span>
          </div>
          <div class="info-row">
            <span class="label">Timestamp:</span>
            <span class="value">{{ job.timestamp }}</span>
          </div>
          <div class="info-row">
            <span class="label">Total Chunks:</span>
            <span class="value">{{ job.total_chunks }}</span>
          </div>
          <div class="info-row">
            <span class="label">Progress:</span>
            <span class="value">{{ job.progress }}% ({{ job.completed_chunks }}/{{ job.total_chunks }})</span>
          </div>
        </div>

        <div class="progress-section">
          <h3>Overall Progress</h3>
          <div class="progress-bar-large">
            <div
              class="progress-fill"
              :style="{ width: job.progress + '%' }"
            ></div>
          </div>
        </div>

        <div class="chunks-section">
          <h3>Chunks Status</h3>
          <div class="chunks-stats">
            <div class="stat">
              <div class="stat-value">{{ job.downloaded_chunks }}</div>
              <div class="stat-label">Downloaded</div>
            </div>
            <div class="stat">
              <div class="stat-value">{{ job.extracted_chunks }}</div>
              <div class="stat-label">Extracted</div>
            </div>
            <div class="stat">
              <div class="stat-value pending">{{ pendingChunks }}</div>
              <div class="stat-label">Pending</div>
            </div>
            <div class="stat">
              <div class="stat-value error">{{ job.failed_chunks }}</div>
              <div class="stat-label">Failed</div>
            </div>
          </div>

          <div class="chunks-grid">
            <div
              v-for="chunk in chunks"
              :key="chunk.id"
              :class="['chunk', getChunkStatusClass(chunk.status)]"
              :title="`Chunk ${chunk.chunk_index}: ${chunk.status}${chunk.message ? ' - ' + chunk.message : ''}`"
            >
              {{ chunk.chunk_index }}
            </div>
          </div>
        </div>

        <div class="actions-section" v-if="job.failed_chunks > 0">
          <h3>Error Recovery</h3>
          <p class="help-text">{{ job.failed_chunks }} chunk(s) failed. You can retry them:</p>
          <button
            @click="retryFailedChunks"
            class="btn btn-warning"
            :disabled="retryingChunks"
          >
            {{ retryingChunks ? 'Retrying...' : 'Retry All Failed Chunks' }}
          </button>
          <div v-if="retrySuccess" class="alert alert-success">
            {{ retrySuccess }}
          </div>
          <div v-if="retryError" class="alert alert-error">
            {{ retryError }}
          </div>
        </div>

        <div class="cookie-section">
          <h3>Update Cookie</h3>
          <p class="help-text">If downloads are failing due to expired cookies, paste a new cookie here:</p>
          <textarea
            v-model="newCookie"
            rows="3"
            placeholder="Paste new cookie..."
          ></textarea>
          <button
            @click="updateCookie"
            class="btn btn-primary"
            :disabled="!newCookie || updatingCookie"
          >
            {{ updatingCookie ? 'Updating...' : 'Update Cookie' }}
          </button>
          <div v-if="cookieUpdateSuccess" class="alert alert-success">
            Cookie updated successfully!
          </div>
          <div v-if="cookieUpdateError" class="alert alert-error">
            {{ cookieUpdateError }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

export default {
  name: 'JobModal',
  props: {
    job: {
      type: Object,
      required: true
    }
  },
  emits: ['close'],
  setup(props) {
    const chunks = ref([])
    const newCookie = ref('')
    const updatingCookie = ref(false)
    const cookieUpdateSuccess = ref(false)
    const cookieUpdateError = ref(null)
    const retryingChunks = ref(false)
    const retrySuccess = ref(null)
    const retryError = ref(null)
    let refreshInterval = null

    const pendingChunks = computed(() => {
      return props.job.total_chunks - props.job.completed_chunks - props.job.failed_chunks
    })

    const getChunkStatusClass = (status) => {
      if (status === 'extracted') return 'completed'
      if (status === 'failed') return 'failed'
      if (status === 'downloaded' || status === 'pending_extraction') return 'downloaded'
      if (status === 'downloading' || status === 'extracting') return 'in-progress'
      return 'pending'
    }

    const fetchChunks = async () => {
      try {
        const response = await axios.get(`/api/jobs/${props.job.id}/chunks`)
        chunks.value = response.data
      } catch (err) {
        console.error('Failed to fetch chunks:', err)
      }
    }

    const retryFailedChunks = async () => {
      retryingChunks.value = true
      retrySuccess.value = null
      retryError.value = null

      try {
        const response = await axios.post(`/api/jobs/${props.job.id}/retry-failed`)
        retrySuccess.value = response.data.message

        // Refresh chunks to show updated status
        await fetchChunks()

        setTimeout(() => {
          retrySuccess.value = null
        }, 5000)
      } catch (err) {
        retryError.value = err.response?.data?.detail || 'Failed to retry chunks'
      } finally {
        retryingChunks.value = false
      }
    }

    const updateCookie = async () => {
      updatingCookie.value = true
      cookieUpdateSuccess.value = false
      cookieUpdateError.value = null

      try {
        await axios.post(`/api/jobs/${props.job.id}/cookie`, {
          cookie: newCookie.value
        })
        cookieUpdateSuccess.value = true
        newCookie.value = ''

        setTimeout(() => {
          cookieUpdateSuccess.value = false
        }, 3000)
      } catch (err) {
        cookieUpdateError.value = err.response?.data?.detail || 'Failed to update cookie'
      } finally {
        updatingCookie.value = false
      }
    }

    onMounted(() => {
      fetchChunks()
      // Auto-refresh chunks every 3 seconds
      refreshInterval = setInterval(fetchChunks, 3000)
    })

    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    })

    return {
      chunks,
      newCookie,
      updatingCookie,
      cookieUpdateSuccess,
      cookieUpdateError,
      retryingChunks,
      retrySuccess,
      retryError,
      pendingChunks,
      getChunkStatusClass,
      retryFailedChunks,
      updateCookie
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal {
  background: white;
  border-radius: 8px;
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  cursor: pointer;
  color: #999;
  line-height: 1;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.3s;
}

.close-btn:hover {
  background: #f0f0f0;
  color: #333;
}

.modal-body {
  padding: 2rem;
}

.job-info {
  margin-bottom: 2rem;
}

.info-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.75rem;
  align-items: center;
}

.label {
  font-weight: 600;
  color: #666;
  min-width: 120px;
}

.value {
  color: #333;
  word-break: break-all;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.pending {
  background: #fff3cd;
  color: #856404;
}

.status-badge.in_progress {
  background: #cfe2ff;
  color: #084298;
}

.status-badge.completed {
  background: #d1e7dd;
  color: #0a3622;
}

.status-badge.failed {
  background: #f8d7da;
  color: #842029;
}

.progress-section, .chunks-section, .cookie-section {
  margin: 2rem 0;
}

h3 {
  margin-bottom: 1rem;
  color: #333;
}

.progress-bar-large {
  height: 24px;
  background: #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transition: width 0.5s ease;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 0.5rem;
  color: white;
  font-weight: 600;
  font-size: 0.875rem;
}

.chunks-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat {
  text-align: center;
  padding: 1rem;
  background: #f8f8f8;
  border-radius: 8px;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #667eea;
}

.stat-value.pending {
  color: #f0ad4e;
}

.stat-value.error {
  color: #c33;
}

.stat-label {
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.25rem;
  text-transform: uppercase;
  font-weight: 600;
}

.chunks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(50px, 1fr));
  gap: 0.5rem;
}

.chunk {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: help;
  transition: transform 0.2s;
}

.chunk:hover {
  transform: scale(1.1);
}

.chunk.pending {
  background: #f0f0f0;
  color: #999;
}

.chunk.in-progress {
  background: #cfe2ff;
  color: #084298;
  animation: pulse 1.5s infinite;
}

.chunk.downloaded {
  background: #fff3cd;
  color: #856404;
}

.chunk.completed {
  background: #d1e7dd;
  color: #0a3622;
}

.chunk.failed {
  background: #f8d7da;
  color: #842029;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.actions-section, .cookie-section {
  margin: 2rem 0;
}

.help-text {
  color: #666;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.875rem;
  resize: vertical;
  margin-bottom: 1rem;
}

textarea:focus {
  outline: none;
  border-color: #667eea;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-warning {
  background: linear-gradient(135deg, #f0ad4e 0%, #ec971f 100%);
  color: white;
}

.btn-warning:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(240, 173, 78, 0.4);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.alert {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.alert-success {
  background: #efe;
  color: #3a3;
  border: 1px solid #cfc;
}

.alert-error {
  background: #fee;
  color: #c33;
  border: 1px solid #fcc;
}
</style>
