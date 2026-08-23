import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import axios from 'axios'
import TimelineView from '../TimelineView.vue'

vi.mock('axios')

describe('TimelineView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('groups archive timelines into one bar per export', async () => {
    axios.get.mockResolvedValue({
      data: [
        { filename: 'takeout-20240101T000000Z-1-001.tgz', status: 'completed', months: { '2019-07': 10, '2019-08': 5 } },
        { filename: 'takeout-20240101T000000Z-1-002.tgz', status: 'completed', months: { '2020-01': 3 } },
        { filename: 'takeout-20250505T000000Z-1-001.tgz', status: 'completed', months: { '2019-07': 2 } },
      ],
    })
    const wrapper = mount(TimelineView)
    await flushPromises()

    expect(axios.get).toHaveBeenCalledWith('/api/timelines')
    // Two exports (20240101, 20250505) -> two bars.
    expect(wrapper.findAll('.export-bar')).toHaveLength(2)
  })

  it('flags an export whose months are fully covered by other exports', async () => {
    axios.get.mockResolvedValue({
      data: [
        { filename: 'takeout-20240101T000000Z-1-001.tgz', status: 'completed', months: { '2019-07': 10, '2019-08': 5 } },
        { filename: 'takeout-20250505T000000Z-1-001.tgz', status: 'completed', months: { '2019-07': 2 } },
      ],
    })
    const wrapper = mount(TimelineView)
    await flushPromises()

    const covered = wrapper.findAll('.export-bar.fully-covered')
    expect(covered).toHaveLength(1)
    expect(covered[0].text()).toContain('20250505')
  })

  it('shows an empty state when no timelines are cached', async () => {
    axios.get.mockResolvedValue({ data: [] })
    const wrapper = mount(TimelineView)
    await flushPromises()

    expect(wrapper.text()).toContain('No timelines')
  })
})
