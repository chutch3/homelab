class TeamCityRestProject < Project

  validates_presence_of :ci_build_identifier, :ci_base_url, unless: ->(project) { project.webhooks_enabled }

  def build_status_url
    feed_url
  end
  def project_name
    feed_url
  end

  def feed_url
    url_with_scheme "#{ci_base_url}/app/rest/builds?locator=running:all,buildType:(id:#{ci_build_identifier}),personal:false"
  end

  def fetch_payload
    TeamCityXmlPayload.new(self)
  end

  def webhook_payload
    TeamCityJsonPayload.new
  end

  def has_dependencies?
    true
  end

end
