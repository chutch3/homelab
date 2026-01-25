<template>
  <div class="create-job">
    <div class="card">
      <h2>Create New Takeout Job</h2>
      <p class="help-text">
        Enter the parameters from your Google Takeout download page. You can find these in the download URLs.
      </p>

      <form @submit.prevent="createJob">
        <div class="form-group">
          <label for="job_id">Job ID</label>
          <input
            id="job_id"
            v-model="form.job_id"
            type="text"
            required
            placeholder="e.g., 1234567890abcdef"
          />
          <small>Found in the download URL parameter: j=...</small>
        </div>

        <div class="form-group">
          <label for="user_id">User ID</label>
          <input
            id="user_id"
            v-model="form.user_id"
            type="text"
            required
            placeholder="e.g., 1234567890"
          />
          <small>Found in the download URL parameter: user=...</small>
        </div>

        <div class="form-group">
          <label for="timestamp">Timestamp</label>
          <input
            id="timestamp"
            v-model="form.timestamp"
            type="text"
            required
            placeholder="e.g., 20240101T120000"
          />
          <small>Found in the filename: takeout-{timestamp}Z-001.tgz</small>
        </div>

        <div class="form-group">
          <label for="auth_user">Auth User</label>
          <input
            id="auth_user"
            v-model="form.auth_user"
            type="text"
            required
            placeholder="e.g., 0"
          />
          <small>Found in the download URL parameter: authuser=...</small>
        </div>

        <div class="form-group">
          <label for="total_chunks">Total Chunks</label>
          <input
            id="total_chunks"
            v-model.number="form.total_chunks"
            type="number"
            required
            min="1"
            placeholder="e.g., 10"
          />
          <small>How many archive files are in your takeout?</small>
        </div>

        <div class="form-group">
          <label for="cookie">Cookie</label>
          <textarea
            id="cookie"
            v-model="form.cookie"
            required
            rows="4"
            placeholder="Paste your full cookie header here..."
          ></textarea>
          <small>Copy the full Cookie header from your browser's network inspector</small>
        </div>

        <div class="form-actions">
          <button type="submit" class="btn btn-primary" :disabled="loading">
            {{ loading ? 'Creating Job...' : 'Create Job' }}
          </button>
        </div>

        <div v-if="error" class="alert alert-error">
          {{ error }}
        </div>

        <div v-if="success" class="alert alert-success">
          Job created successfully! Check the Jobs tab to monitor progress.
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import axios from 'axios'

export default {
  name: 'CreateJob',
  emits: ['job-created'],
  setup(props, { emit }) {
    const form = ref({
      job_id: '',
      user_id: '',
      timestamp: '',
      auth_user: '0',
      total_chunks: 1,
      cookie: ''
    })

    const loading = ref(false)
    const error = ref(null)
    const success = ref(false)

    const createJob = async () => {
      loading.value = true
      error.value = null
      success.value = false

      try {
        await axios.post('/api/jobs', form.value)
        success.value = true

        // Reset form
        form.value = {
          job_id: '',
          user_id: '',
          timestamp: '',
          auth_user: '0',
          total_chunks: 1,
          cookie: ''
        }

        // Notify parent
        setTimeout(() => {
          emit('job-created')
        }, 1500)
      } catch (err) {
        error.value = err.response?.data?.detail || 'Failed to create job. Please check your inputs.'
      } finally {
        loading.value = false
      }
    }

    return {
      form,
      loading,
      error,
      success,
      createJob
    }
  }
}
</script>

<style scoped>
.create-job {
  padding: 2rem 0;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

h2 {
  margin-bottom: 0.5rem;
  color: #333;
}

.help-text {
  color: #666;
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #333;
}

input, textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

input:focus, textarea:focus {
  outline: none;
  border-color: #667eea;
}

small {
  display: block;
  margin-top: 0.25rem;
  color: #999;
  font-size: 0.875rem;
}

textarea {
  font-family: monospace;
  resize: vertical;
}

.form-actions {
  margin-top: 2rem;
}

.btn {
  padding: 0.875rem 2rem;
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

.alert-error {
  background: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

.alert-success {
  background: #efe;
  color: #3a3;
  border: 1px solid #cfc;
}
</style>
