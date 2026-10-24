class GithubProjectDecorator < ProjectDecorator
  BASE_WEB_URL = 'https://github.com'

  def current_build_url
    "#{self.class.const_get(:BASE_WEB_URL)}/#{object.ci_build_identifier}/actions"
  end
end
