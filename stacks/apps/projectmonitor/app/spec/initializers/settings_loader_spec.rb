require 'spec_helper'
require 'tmpdir'

RSpec.describe SettingsLoader do
  around do |example|
    Dir.mktmpdir('projectmonitor-settings') do |directory|
      @path = File.join(directory, 'settings.yml')
      File.write(@path, <<~YAML)
        defaults: &defaults
          password_auth_enabled: true
          emailer_host:
            host: localhost
            port: 3000
        test:
          <<: *defaults
        production:
          <<: *defaults
          password_auth_enabled: false
      YAML
      example.run
    end
  end

  it 'loads aliases and selects the environment without mixing environments' do
    expect(described_class.load(@path, 'test').password_auth_enabled).to eq(true)
    expect(described_class.load(@path, 'production').password_auth_enabled).to eq(false)
  end

  it 'preserves nested Mash access and merges local overrides like choices' do
    File.write(@path.sub('.yml', '.local.yml'), <<~YAML)
      test:
        emailer_host:
          host: dashboard.example.com
    YAML
    settings = described_class.load(@path, 'test')
    expect(settings.emailer_host.to_hash).to eq('host' => 'dashboard.example.com', 'port' => 3000)
    expect(settings.password_auth_enabled).to eq(true)
  end

  it 'ignores an empty local override file' do
    File.write(@path.sub('.yml', '.local.yml'), '')
    expect(described_class.load(@path, 'test').password_auth_enabled).to eq(true)
  end

  it 'evaluates trusted configuration ERB before loading YAML' do
    File.write(@path, "test:\n  value: <%= 6 * 7 %>\n")
    expect(described_class.load(@path, 'test').value).to eq(42)
  end

  it 'rejects a missing environment' do
    expect { described_class.load(@path, 'missing') }.to raise_error(KeyError)
  end
end
