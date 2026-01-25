<template>
  <div class="app">
    <header class="header">
      <div class="container">
        <h1>Google Photos Takeout Manager</h1>
        <p>Automated download and organization of Google Photos archives</p>
      </div>
    </header>

    <main class="container">
      <div class="tabs">
        <button
          :class="['tab', { active: activeTab === 'create' }]"
          @click="activeTab = 'create'"
        >
          Create Job
        </button>
        <button
          :class="['tab', { active: activeTab === 'jobs' }]"
          @click="activeTab = 'jobs'"
        >
          Jobs
        </button>
      </div>

      <CreateJob v-if="activeTab === 'create'" @job-created="handleJobCreated" />
      <JobList v-else @select-job="selectJob" :key="jobListKey" />
    </main>

    <JobModal v-if="selectedJob" :job="selectedJob" @close="selectedJob = null" />
  </div>
</template>

<script>
import { ref } from 'vue'
import CreateJob from './components/CreateJob.vue'
import JobList from './components/JobList.vue'
import JobModal from './components/JobModal.vue'

export default {
  name: 'App',
  components: {
    CreateJob,
    JobList,
    JobModal
  },
  setup() {
    const activeTab = ref('create')
    const selectedJob = ref(null)
    const jobListKey = ref(0)

    const handleJobCreated = () => {
      activeTab.value = 'jobs'
      jobListKey.value++
    }

    const selectJob = (job) => {
      selectedJob.value = job
    }

    return {
      activeTab,
      selectedJob,
      jobListKey,
      handleJobCreated,
      selectJob
    }
  }
}
</script>

<style>
.app {
  min-height: 100vh;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.header p {
  opacity: 0.9;
  font-size: 1rem;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.tabs {
  display: flex;
  gap: 0.5rem;
  margin: 2rem 0 1rem;
  border-bottom: 2px solid #e0e0e0;
}

.tab {
  padding: 0.75rem 1.5rem;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.3s;
}

.tab:hover {
  color: #667eea;
}

.tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
}
</style>
