require 'json'
require 'digest'

root = File.expand_path('..', __dir__)
manifest = JSON.parse(File.read(File.join(__dir__, 'compatibility-coverage.json')))
results = JSON.parse(File.read(File.join(root, 'coverage/.resultset.json')))
coverage = results.fetch('RSpec').fetch('coverage')
failures = []
checked = 0
paths = Dir[File.join(root, '{app,lib}/**/*.rb')]
paths += %w[config/settings_loader.rb docker/wait-for-database.rb].map { |path| File.join(root, path) }
paths.each do |path|
  relative = path.delete_prefix("#{root}/")
  digest = Digest::SHA256.file(path).hexdigest
  next if manifest.fetch('original')[relative] == digest
  change = manifest.fetch('changes')[relative]
  unless change && change.fetch('sha256') == digest
    failures << "#{relative}: coverage manifest is stale; regenerate against the pinned upstream"
    next
  end
  lines = coverage.dig(path, 'lines')
  unless lines
    failures << "#{relative}: no coverage collected"
    next
  end
  change.fetch('lines').each do |line|
    hits = lines[line - 1]
    next if hits.nil? # comments, whitespace, and Ruby syntax with no executable instruction
    checked += 1
    failures << "#{relative}:#{line}: changed executable line was not exercised" if hits.zero?
  end
end
abort failures.join("\n") unless failures.empty?
puts "Compatibility coverage: #{checked} changed executable lines exercised (100%)."
