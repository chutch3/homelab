require File.expand_path('../boot', __FILE__)

require 'rails'
require 'active_record/railtie'
require 'action_controller/railtie'
require 'action_mailer/railtie'
require 'sprockets/railtie'

Bundler.require(:default, Rails.env)

require 'tilt/coffee'
require_relative 'settings_loader'

module ProjectMonitor
  class Application < Rails::Application
    # Settings in config/environments/* take precedence over those specified here.
    # Application configuration should go into files in config/initializers
    # -- all .rb files in that directory are automatically loaded.

    # Set Time.zone default to the specified zone and make Active Record auto-convert to this zone.
    # Run "rake -D time" for a list of tasks for finding time zone names. Default is UTC.
    # config.time_zone = 'Central Time (US & Canada)'

    # The default locale is :en and all translations from config/locales/*.rb,yml are auto loaded.
    # config.i18n.load_path += Dir[Rails.root.join('my', 'locales', '*.{rb,yml}').to_s]
    # config.i18n.default_locale = :de

    # Do not swallow errors in after_commit/after_rollback callbacks.
    # Preserve Rails 4 association semantics while updating the framework.
    config.active_record.belongs_to_required_by_default = false
    config.active_record.yaml_column_permitted_classes = [Symbol, Time, Date]

    SettingsLoader.load(config.root.join('config/settings.yml'), Rails.env).each do |key, value|
      config.public_send("#{key}=", value)
    end
    config.add_autoload_paths_to_load_path = true
    config.autoload_paths += %W(#{config.root}/lib #{config.root}/lib/payload)
    config.eager_load_paths += %W(#{config.root}/lib #{config.root}/lib/payload)
    config.encoding = 'utf-8'

    config.action_mailer.default_url_options = Rails.configuration.emailer_host.to_hash.symbolize_keys
    config.secret_key_base = ENV.fetch('SECRET_KEY_BASE') {
      raise 'SECRET_KEY_BASE is required in production' if Rails.env.production?
      'projectmonitor-development-and-test-only-' * 2
    }

    config.cache_store = :memory_store
    config.public_file_server.headers = { "Cache-Control" => "public, max-age=3600" }
    config.hosts = ENV.fetch("RAILS_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if Rails.env.production?
  end
end
