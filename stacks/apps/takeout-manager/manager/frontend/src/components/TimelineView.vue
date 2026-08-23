<template>
  <div class="timeline-view">
    <div class="card">
      <div class="card-header">
        <h2>Export Timeline</h2>
        <button @click="fetchTimelines" class="btn btn-secondary" :disabled="loading">
          {{ loading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>

      <p class="help-text">
        Each bar is one Takeout export, spanning its earliest to latest photo month.
        Overlapping bars cover the same months; an export flagged
        <strong>fully covered</strong> is entirely contained in others — a safe candidate
        to delete.
      </p>

      <div v-if="exports.length === 0" class="empty-state">
        <p>No timelines yet. Scan an archive's Timeline from the Archives tab, or extract one.</p>
      </div>

      <div v-else class="timeline">
        <div class="axis">
          <span v-for="year in axisYears" :key="year" class="axis-year">{{ year }}</span>
        </div>
        <div
          v-for="exp in exports"
          :key="exp.key"
          class="export-bar"
          :class="{ 'fully-covered': exp.fullyCovered }"
        >
          <div class="export-label">
            {{ exp.key }}
            <span v-if="exp.fullyCovered" class="covered-badge">fully covered</span>
          </div>
          <div class="track">
            <div
              class="span"
              :style="{ left: exp.left + '%', width: exp.width + '%' }"
              :title="`${exp.start} → ${exp.end} · ${exp.count} media`"
            >
              {{ exp.start }} → {{ exp.end }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

function exportKey(filename) {
  const match = filename.match(/(\d{8}T\d{6})/)
  return match ? match[1] : filename
}

export default {
  name: 'TimelineView',
  setup() {
    const timelines = ref([])
    const loading = ref(false)

    const fetchTimelines = async () => {
      try {
        loading.value = true
        const response = await axios.get('/api/timelines')
        timelines.value = response.data
      } finally {
        loading.value = false
      }
    }

    // Group archives into exports, unioning their month sets.
    const grouped = computed(() => {
      const byExport = {}
      for (const t of timelines.value) {
        if (t.status !== 'completed' || !t.months) continue
        const key = exportKey(t.filename)
        const bucket = (byExport[key] = byExport[key] || { key, months: {} })
        for (const [month, count] of Object.entries(t.months)) {
          bucket.months[month] = (bucket.months[month] || 0) + count
        }
      }
      return Object.values(byExport)
    })

    const allMonths = computed(() => {
      const set = new Set()
      for (const g of grouped.value) for (const m of Object.keys(g.months)) set.add(m)
      return [...set].sort()
    })

    const axisYears = computed(() => {
      const years = new Set(allMonths.value.map((m) => m.slice(0, 4)))
      return [...years].sort()
    })

    const exports = computed(() => {
      const months = allMonths.value
      const span = Math.max(months.length, 1)
      return grouped.value
        .map((g) => {
          const keys = Object.keys(g.months).sort()
          const start = keys[0]
          const end = keys[keys.length - 1]
          const startIdx = months.indexOf(start)
          const endIdx = months.indexOf(end)
          // Months covered by every OTHER export.
          const others = new Set()
          for (const o of grouped.value) {
            if (o === g) continue
            for (const m of Object.keys(o.months)) others.add(m)
          }
          const fullyCovered = keys.length > 0 && keys.every((m) => others.has(m))
          return {
            key: g.key,
            start,
            end,
            count: Object.values(g.months).reduce((a, b) => a + b, 0),
            left: (startIdx / span) * 100,
            width: ((endIdx - startIdx + 1) / span) * 100,
            fullyCovered,
          }
        })
        .sort((a, b) => a.start.localeCompare(b.start))
    })

    onMounted(fetchTimelines)

    return { timelines, loading, exports, axisYears, fetchTimelines }
  },
}
</script>

<style scoped>
.timeline-view { padding: 2rem 0; }
.card { background: white; border-radius: 8px; padding: 2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.card-header h2 { margin: 0; color: #333; }
.help-text { color: #666; margin-bottom: 1.5rem; }
.btn { padding: 0.5rem 1rem; border: none; border-radius: 4px; font-weight: 600; cursor: pointer; }
.btn-secondary { background: #f0f0f0; color: #333; }
.empty-state { text-align: center; padding: 3rem; color: #999; }
.axis { display: flex; justify-content: space-between; color: #999; font-size: 0.75rem; margin-bottom: 0.5rem; padding-left: 180px; }
.export-bar { display: flex; align-items: center; margin-bottom: 0.5rem; }
.export-bar.fully-covered .span { background: #f8d7da; color: #842029; }
.export-label { width: 180px; font-family: monospace; font-size: 0.8rem; color: #333; flex: none; }
.covered-badge { display: inline-block; margin-left: 6px; padding: 0 6px; border-radius: 10px; background: #f8d7da; color: #842029; font-size: 0.65rem; font-family: sans-serif; }
.track { position: relative; flex: 1; height: 22px; background: #f3f3f3; border-radius: 4px; }
.span { position: absolute; top: 0; height: 22px; min-width: 2px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; font-size: 0.7rem; border-radius: 4px; display: flex; align-items: center; justify-content: center; white-space: nowrap; overflow: hidden; }
</style>
