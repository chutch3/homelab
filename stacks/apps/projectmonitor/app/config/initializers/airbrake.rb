# Error reporting is opt-in; upstream credentials do not belong to this deployment.
Airbrake.configure do |config|
  config.project_id = ENV.fetch('AIRBRAKE_PROJECT_ID', 0).to_i
  config.project_key = ENV.fetch('AIRBRAKE_PROJECT_KEY', '')
  config.error_notifications = config.project_id.positive?
  config.performance_stats = false
  config.query_stats = false
  config.job_stats = false
  config.remote_config = false
end
