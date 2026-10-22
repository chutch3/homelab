require 'simplecov'
SimpleCov.start do
  cover '{app,lib,config,docker}/**/*.rb'
  merge_subprocesses true
  skip '/spec/'
  enable_coverage :branch
end
ENV["RAILS_ENV"] = 'test'
require File.expand_path("../../config/environment", __FILE__)
require 'rspec/rails'
require 'webmock/rspec'
require 'capybara/rspec'
require 'capybara/rails'
require 'pry'

Dir[Rails.root.join("spec/support/**/*.rb")].each {|f| require f}

RSpec.configure do |config|
  config.infer_spec_type_from_file_location!
  config.mock_with :rspec
  config.fixture_paths = [ "#{::Rails.root}/spec/fixtures"]
  config.use_transactional_fixtures = false
  config.use_instantiated_fixtures  = false
  config.global_fixtures = :project_statuses, :projects, :taggings, :tags, :aggregate_projects

  config.include Devise::Test::ControllerHelpers, type: :controller
  config.include ViewHelpers, type: :view

  config.after(:each) { Timecop.return }

  config.order = 'random'
  config.include Rails.application.routes.url_helpers

  config.filter_run focus: true
  config.run_all_when_everything_filtered = true

  Capybara.javascript_driver = :selenium_chromium

  config.before(:all) do
    DeferredGarbageCollection.start
  end

  config.after(:all) do
    DeferredGarbageCollection.reconsider
  end
end
