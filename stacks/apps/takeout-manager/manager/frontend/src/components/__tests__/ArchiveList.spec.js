import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import axios from 'axios'
import ArchiveList from '../ArchiveList.vue'

vi.mock('axios')

const archives = [
  {
    filename: 'takeout-20240101T000000Z-1-001.tgz',
    size_bytes: 10,
    export_timestamp: '2024-01-01T00:00:00Z',
    source: 'db',
    extract_status: 'extracted',
  },
  {
    filename: 'takeout-Z-001.tgz',
    size_bytes: 20,
    export_timestamp: null,
    source: 'disk',
    extract_status: 'unknown',
  },
]

describe('ArchiveList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    axios.get.mockResolvedValue({ data: archives })
    axios.post.mockResolvedValue({ data: { message: 'Archive queued for extraction' } })
  })

  it('fetches archives from the API on mount', async () => {
    mount(ArchiveList)
    await flushPromises()

    expect(axios.get).toHaveBeenCalledWith('/api/archives')
  })

  it('renders one row per archive with its filename and extract status', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()

    const rows = wrapper.findAll('.archive')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('takeout-20240101T000000Z-1-001.tgz')
    expect(rows[0].text()).toContain('extracted')
  })

  it('marks a disk-only archive as an orphan', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()

    const orphan = wrapper.findAll('.archive')[1]
    expect(orphan.find('.archive-source').text()).toBe('disk')
  })

  it('shows a placeholder when an archive has no export timestamp', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()

    const orphan = wrapper.findAll('.archive')[1]
    expect(orphan.find('.archive-timestamp').text()).toBe('—')
  })

  it('renders a human-readable size', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()

    expect(wrapper.findAll('.archive')[0].find('.archive-size').text()).toBe('10 B')
  })

  it('shows an empty state when there are no archives', async () => {
    axios.get.mockResolvedValue({ data: [] })
    const wrapper = mount(ArchiveList)
    await flushPromises()

    expect(wrapper.text()).toContain('No archives')
  })

  it('queues extraction for the archive whose Extract button is clicked', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()

    await wrapper.findAll('.archive')[1].find('.extract-btn').trigger('click')
    await flushPromises()

    expect(axios.post).toHaveBeenCalledWith('/api/archives/takeout-Z-001.tgz/extract')
  })

  it('refreshes the list after queuing an extraction', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()
    axios.get.mockClear()

    await wrapper.findAll('.archive')[0].find('.extract-btn').trigger('click')
    await flushPromises()

    expect(axios.get).toHaveBeenCalledWith('/api/archives')
  })

  it('requests a timeline scan for an archive (shown on the Timeline tab)', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()

    await wrapper.findAll('.archive')[0].find('.timeline-btn').trigger('click')
    await flushPromises()

    expect(axios.post).toHaveBeenCalledWith(
      '/api/archives/takeout-20240101T000000Z-1-001.tgz/timeline'
    )
  })

  it('shows confirmation feedback after requesting a timeline', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()

    await wrapper.findAll('.archive')[0].find('.timeline-btn').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('.archive')[0].find('.action-notice').text().toLowerCase())
      .toContain('requested')
  })

  it('shows confirmation feedback after queuing an extraction', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()

    await wrapper.findAll('.archive')[1].find('.extract-btn').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('.archive')[1].find('.action-notice').text().toLowerCase())
      .toContain('queued')
  })

  it('deletes an archive after confirming', async () => {
    axios.delete.mockResolvedValue({ data: { message: 'Archive deleted' } })
    const wrapper = mount(ArchiveList)
    await flushPromises()

    await wrapper.findAll('.archive')[1].find('.delete-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.delete-confirm').exists()).toBe(true)

    await wrapper.find('.confirm-delete-btn').trigger('click')
    await flushPromises()

    expect(axios.delete).toHaveBeenCalledWith('/api/archives/takeout-Z-001.tgz')
    expect(wrapper.find('.delete-confirm').exists()).toBe(false)
  })

  it('cancels deletion without calling the api', async () => {
    const wrapper = mount(ArchiveList)
    await flushPromises()

    await wrapper.findAll('.archive')[0].find('.delete-btn').trigger('click')
    await flushPromises()
    await wrapper.find('.cancel-delete-btn').trigger('click')
    await flushPromises()

    expect(axios.delete).not.toHaveBeenCalled()
    expect(wrapper.find('.delete-confirm').exists()).toBe(false)
  })

})
