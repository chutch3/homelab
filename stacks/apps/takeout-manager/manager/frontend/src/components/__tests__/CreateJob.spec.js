import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import axios from 'axios'
import CreateJob from '../CreateJob.vue'

vi.mock('axios')

async function submit(wrapper) {
  await wrapper.find('#job_id').setValue('j')
  await wrapper.find('#user_id').setValue('u')
  await wrapper.find('#timestamp').setValue('20240101T000000')
  await wrapper.find('#auth_user').setValue('0')
  await wrapper.find('#total_chunks').setValue(1)
  await wrapper.find('#cookie').setValue('c')
  await wrapper.find('form').trigger('submit.prevent')
  await flushPromises()
}

describe('CreateJob auto-extract toggle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    axios.post.mockResolvedValue({ data: { message: 'ok', job_id: 1 } })
  })

  it('sends auto_extract true by default', async () => {
    const wrapper = mount(CreateJob)
    await submit(wrapper)

    expect(axios.post).toHaveBeenCalledWith(
      '/api/jobs',
      expect.objectContaining({ auto_extract: true })
    )
  })

  it('sends auto_extract false when the toggle is unchecked', async () => {
    const wrapper = mount(CreateJob)
    await wrapper.find('#auto_extract').setValue(false)
    await submit(wrapper)

    expect(axios.post).toHaveBeenCalledWith(
      '/api/jobs',
      expect.objectContaining({ auto_extract: false })
    )
  })
})
