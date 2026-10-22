require 'erb'
require 'yaml'
require 'hashie/mash'

# The original choices gem is incompatible with modern Ruby/Psych. Keep its
# environment selection and local override semantics using the same Mash merge.
module SettingsLoader
  def self.load(path, environment)
    settings = Hashie::Mash.new(read(path))
    local = path.to_s.sub(/(\.\w+)?$/, '.local\1')
    settings.update(read(local) || {}) if File.exist?(local)
    settings.fetch(environment.to_s)
  end

  def self.read(path)
    YAML.safe_load(ERB.new(File.read(path)).result, aliases: true)
  end
end
