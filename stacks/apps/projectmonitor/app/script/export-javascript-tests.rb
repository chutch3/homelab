ENV['RAILS_ENV'] = 'test'
require_relative '../config/environment'
require 'fileutils'
require 'json'

output = Rails.root.join('tmp/javascript-tests')
FileUtils.mkdir_p(output)
assets = Rails.application.assets
sources = ['application.js']
sources += Dir[Rails.root.join('spec/javascripts/helpers/**/*.js')].sort.map { |p| p.delete_prefix("#{Rails.root}/spec/javascripts/") }
sources += Dir[Rails.root.join('spec/javascripts/backbone/factories/*.{js,coffee}')].sort.map { |p| p.delete_prefix("#{Rails.root}/spec/javascripts/") }
sources += Dir[Rails.root.join('spec/javascripts/**/*{Spec,spec}.{js,coffee,js.coffee}')].sort.map { |p| p.delete_prefix("#{Rails.root}/spec/javascripts/") }
sources.each_with_index do |logical_path, index|
  logical_path = logical_path.sub(/\.coffee$/, '')
  logical_path += '.js' unless logical_path.end_with?('.js')
  asset = assets.find_asset(logical_path) or abort "Missing test asset: #{logical_path}"
  File.write(output.join("#{index}.js"), asset.to_s)
end
File.write(output.join('sources.json'), JSON.generate(sources.each_index.map { |index| "#{index}.js" }))
