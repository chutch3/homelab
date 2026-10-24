class GithubProject < Project

  GITHUB_API_BASE_URL = 'https://api.github.com'

  validates_presence_of :ci_build_identifier, :ci_auth_token, unless: ->(project) { project.webhooks_enabled }

  def build_status_url
    feed_url
  end

  def self.project_specific_attributes
    ['ci_build_identifier', 'ci_auth_token']
  end

  def feed_url
    branch = build_branch.presence || 'master'
    "#{GITHUB_API_BASE_URL}/repos/#{ci_build_identifier}/actions/runs?branch=#{branch}&per_page=#{Project::RECENT_STATUS_COUNT}"
  end

  def fetch_payload
    GithubPayload.new.tap do |payload|
      payload.branch = build_branch
    end
  end

  alias_method :webhook_payload, :fetch_payload

  def accept_mime_types
    'application/vnd.github+json'
  end

  # GitHub's REST API rejects requests without a User-Agent, and the token is
  # sent as an Authorization header rather than a query param (unlike CircleCI).
  def additional_headers
    {
      'Authorization' => "token #{ci_auth_token}",
      'User-Agent' => 'ProjectMonitor',
      'X-GitHub-Api-Version' => '2022-11-28',
    }
  end

  def requires_branch_name?
    true
  end

end
