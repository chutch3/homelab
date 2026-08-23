import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import axios from 'axios'
import App from '../App.vue'

vi.mock('axios')

describe('App navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    axios.get.mockResolvedValue({ data: [] })
  })

  it('shows the Archives view when the Archives tab is selected', async () => {
    const wrapper = mount(App)
    await flushPromises()

    const archivesTab = wrapper.findAll('.tab').find((t) => t.text() === 'Archives')
    expect(archivesTab).toBeTruthy()

    await archivesTab.trigger('click')
    await flushPromises()

    expect(wrapper.find('.archive-list').exists()).toBe(true)
    expect(axios.get).toHaveBeenCalledWith('/api/archives')
  })

  it('shows the Timeline view when the Timeline tab is selected', async () => {
    const wrapper = mount(App)
    await flushPromises()

    const tab = wrapper.findAll('.tab').find((t) => t.text() === 'Timeline')
    expect(tab).toBeTruthy()

    await tab.trigger('click')
    await flushPromises()

    expect(wrapper.find('.timeline-view').exists()).toBe(true)
    expect(axios.get).toHaveBeenCalledWith('/api/timelines')
  })
})
