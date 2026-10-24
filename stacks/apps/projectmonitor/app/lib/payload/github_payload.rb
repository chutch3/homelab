class GithubPayload < Payload
  def branch=(new_branch)
    @branch = new_branch unless new_branch.blank?
  end

  def branch
    @branch
  end

  def building?
    content = status_content.first
    content && (content['status'] == 'queued' || content['status'] == 'in_progress')
  end

  def content_ready?(content)
    content['status'] == 'completed' &&
      content['conclusion'].present? &&
      specified_branch?(content)
  end

  def convert_content!(raw_content)
    parsed = JSON.parse(raw_content)
    Array.wrap(parsed.is_a?(Hash) ? parsed['workflow_runs'] : parsed)
  rescue => e
    handle_processing_exception e
  end

  def convert_webhook_content!(params)
    Array.wrap(params['workflow_run'])
  end

  def parse_success(content)
    content['conclusion'] == 'success'
  end

  def parse_url(content)
    content['html_url']
  end

  def parse_build_id(content)
    content['run_number']
  end

  def parse_published_at(content)
    timestamp = content['run_started_at'] || content['created_at']
    timestamp ? Time.parse(timestamp) : Time.now
  end

  private

  def specified_branch?(content)
    branch.blank? || content['head_branch'] == branch
  end
end
