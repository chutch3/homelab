class TeamCityProject < Project

  validates_presence_of :ci_build_identifier, :ci_base_url, unless: ->(project) { project.webhooks_enabled }
  validates :ci_build_identifier, format: {with: /\Abt\d+\Z/, message: 'must begin with bt'}, unless: ->(project) { project.webhooks_enabled }

  def build_status_url
    feed_url
  end
  def project_name
    feed_url
  end

  def feed_url
    url_with_scheme "#{ci_base_url}/guestAuth/cradiator.html?buildTypeId=#{ci_build_identifier}"
  end

  def fetch_payload
    LegacyTeamCityXmlPayload.new
  end

end
