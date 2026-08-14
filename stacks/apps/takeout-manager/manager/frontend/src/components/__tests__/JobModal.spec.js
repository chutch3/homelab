import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import axios from 'axios'
import JobModal from '../JobModal.vue'

vi.mock('axios')

const job = {
  id: 1,
  job_id: 'abc-123',
  user_id: 'user-1',
  timestamp: '20240101T000000',
  total_chunks: 2,
  status: 'in_progress',
  downloaded_chunks: 0,
  extracted_chunks: 1,
  failed_chunks: 0,
  completed_chunks: 1,
  progress: 50,
}

describe('JobModal chunk retry', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    axios.get.mockResolvedValue({
      data: [
        { id: 5, chunk_index: 5, status: 'downloading', message: null },
        { id: 6, chunk_index: 6, status: 'extracted', message: 'Extracted 10 pictures and 2 videos' },
      ],
    })
    axios.post.mockResolvedValue({ data: { message: 'Chunk queued for retry' } })
  })

  it('retries the individual chunk that was clicked', async () => {
    const wrapper = mount(JobModal, { props: { job } })
    await flushPromises()

    const chunkEls = wrapper.findAll('.chunk')
    await chunkEls[0].trigger('click')
    await flushPromises()

    expect(axios.post).toHaveBeenCalledWith('/api/chunks/5/retry')
  })

  it('re-fetches chunks after an individual retry succeeds', async () => {
    const wrapper = mount(JobModal, { props: { job } })
    await flushPromises()
    axios.get.mockClear()

    const chunkEls = wrapper.findAll('.chunk')
    await chunkEls[0].trigger('click')
    await flushPromises()

    expect(axios.get).toHaveBeenCalledWith('/api/jobs/1/chunks')
  })

  it('does not retry a chunk that has already been extracted', async () => {
    const wrapper = mount(JobModal, { props: { job } })
    await flushPromises()

    const chunkEls = wrapper.findAll('.chunk')
    await chunkEls[1].trigger('click') // chunk 6, status: extracted
    await flushPromises()

    expect(axios.post).not.toHaveBeenCalled()
  })

  it('does not call retry-all when an individual chunk is clicked', async () => {
    const wrapper = mount(JobModal, { props: { job } })
    await flushPromises()

    const chunkEls = wrapper.findAll('.chunk')
    await chunkEls[0].trigger('click')
    await flushPromises()

    expect(axios.post).not.toHaveBeenCalledWith('/api/jobs/1/retry-failed')
  })
})
