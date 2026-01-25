<template>
  <div class="job-list">
    <div class="card">
      <div class="card-header">
        <h2>Takeout Jobs</h2>
        <button @click="refreshJobs" class="btn btn-secondary" :disabled="loading">
          {{ loading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>

      <div v-if="loading && jobs.length === 0" class="loading">
        Loading jobs...
      </div>

      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <div v-else-if="jobs.length === 0" class="empty-state">
        <p>No jobs found. Create your first takeout job to get started!</p>
      </div>

      <div v-else class="jobs-grid">
        <div
          v-for="job in jobs"
          :key="job.id"
          class="job-card"
          @click="$emit('select-job', job)"
        >
          <div class="job-header">
            <div class="job-title">
              <h3>Job {{ job.job_id.substring(0, 8) }}...</h3>
              <span :class="['status-badge', job.status]">{{ job.status }}</span>
            </div>
          </div>

          <div class="job-details">
            <div class="detail-row">
              <span class="label">Chunks:</span>
              <span class="value">{{ job.completed_chunks }} / {{ job.total_chunks }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Progress:</span>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: job.progress + '%' }"
                ></div>
              </div>
              <span class="value">{{ job.progress }}%</span>
            </div>
            <div class="detail-row">
              <span class="label">Timestamp:</span>
              <span class="value">{{ job.timestamp }}</span>
            </div>
          </div>

          <div class="job-phases">
            <div class="phase">
              <span class="phase-label">Download:</span>
              <span class="phase-value">{{ job.downloaded_chunks }}</span>
            </div>
            <div class="phase">
              <span class="phase-label">Extracted:</span>
              <span class="phase-value">{{ job.extracted_chunks }}</span>
            </div>
            <div class="phase">
              <span class="phase-label">Failed:</span>
              <span class="phase-value error">{{ job.failed_chunks }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

export default {
  name: 'JobList',
  emits: ['select-job'],
  setup() {
    const jobs = ref([])
    const loading = ref(false)
    const error = ref(null)
    let refreshInterval = null

    const fetchJobs = async () => {
      try {
        loading.value = true
        error.value = null
        const response = await axios.get('/api/jobs')
        jobs.value = response.data
      } catch (err) {
        error.value = 'Failed to load jobs'
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    const refreshJobs = () => {
      fetchJobs()
    }

    onMounted(() => {
      fetchJobs()
      // Auto-refresh every 5 seconds
      refreshInterval = setInterval(fetchJobs, 5000)
    })

    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    })

    return {
      jobs,
      loading,
      error,
      refreshJobs
    }
  }
}
</script>

<style scoped>
.job-list {
  padding: 2rem 0;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
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
  transition: all 0.3s;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading, .empty-state {
  text-align: center;
  padding: 3rem;
  color: #999;
}

.alert {
  padding: 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.alert-error {
  background: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

.jobs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.job-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s;
}

.job-card:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
  transform: translateY(-2px);
}

.job-header {
  margin-bottom: 1rem;
}

.job-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.job-title h3 {
  margin: 0;
  font-size: 1.125rem;
  color: #333;
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

.job-details {
  margin: 1rem 0;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.label {
  font-weight: 600;
  color: #666;
  min-width: 80px;
}

.value {
  color: #333;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transition: width 0.5s ease;
}

.job-phases {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}

.phase {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.phase-label {
  font-size: 0.75rem;
  color: #999;
  text-transform: uppercase;
  font-weight: 600;
}

.phase-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #667eea;
}

.phase-value.error {
  color: #c33;
}
</style>
