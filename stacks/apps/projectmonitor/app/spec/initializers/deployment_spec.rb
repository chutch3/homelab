require 'spec_helper'
require 'open3'
require 'tmpdir'
require Rails.root.join('docker/wait-for-database')

RSpec.describe 'Container startup' do
  it 'runs the complete test entrypoint by default and propagates failures' do
    Dir.mktmpdir do |directory|
      command = File.join(directory, 'bash')
      File.write(command, "#!/bin/sh\nprintf '%s\\n' \"$*\"\nexit \"$TEST_EXIT\"\n")
      File.chmod(0755, command)
      [0, 7].each do |exit_code|
        output, status = Open3.capture2e(
          { 'PATH' => "#{directory}:#{ENV.fetch('PATH')}", 'TEST_EXIT' => exit_code.to_s },
          'bundle', 'exec', 'rake'
        )
        expect(output.lines.map(&:strip)).to include('script/test-all.sh')
        expect(status.success?).to eq(exit_code.zero?)
      end
    end
  end

  it 'registers the job worker once so shutdown cannot start a second worker' do
    output, status = Open3.capture2e(
      'bundle', 'exec', 'ruby', '-rrake', '-e',
      'load "Rakefile"; abort "Duplicate worker task" unless Rake::Task["jobs:work"].actions.length == 1; puts "registered once"'
    )
    expect(status).to be_success
    expect(output).to include('registered once')
  end

  it 'keeps New Relic disabled without an explicitly configured account' do
    allow(ENV).to receive(:fetch).and_call_original
    allow(ENV).to receive(:fetch).with('NEW_RELIC_LICENSE_KEY', '').and_return('')
    config = YAML.safe_load(ERB.new(File.read(Rails.root.join('config/newrelic.yml'))).result, aliases: true)
    expect(config.fetch('production').fetch('agent_enabled')).to eq(false)
    expect(config.fetch('production').fetch('ssl')).to eq(true)
  end

  it 'migrates only in the web process and starts each background role in the foreground' do
    Dir.mktmpdir do |directory|
      command = File.join(directory, 'bundle')
      log = File.join(directory, 'commands')
      File.write(command, "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$COMMAND_LOG\"\n")
      File.chmod(0755, command)
      roles = { 'web' => 'puma -C config/puma.rb', 'worker' => 'rake jobs:work',
                'poller' => 'rake projectmonitor:poller', 'housekeeping' => 'clockwork clockwork.rb' }
      roles.each do |role, process|
        File.write(log, '')
        _, status = Open3.capture2e(
          { 'PATH' => "#{directory}:#{ENV.fetch('PATH')}", 'COMMAND_LOG' => log },
          'sh', Rails.root.join('docker/entrypoint.sh').to_s, role
        )
        expect(status).to be_success
        commands = File.readlines(log, chomp: true)
        expect(commands.first).to eq('exec ruby docker/wait-for-database.rb')
        expect(commands.last).to eq("exec #{process}")
        if role == 'web'
          expect(commands).to include('exec rake db:prepare')
        else
          expect(commands).to include('exec rake db:abort_if_pending_migrations')
          expect(commands).not_to include('exec rake db:prepare')
        end
      end
    end
  end

  it 'loads Swarm secrets without printing them and preserves command arguments' do
    Dir.mktmpdir do |directory|
      secret = File.join(directory, 'secret')
      File.write(secret, "test-only-secret\n")
      output, status = Open3.capture2e(
        { 'SECRET_KEY_BASE_FILE' => secret, 'DATABASE_PASSWORD_FILE' => secret,
          'password_auth_pepper_FILE' => secret },
        'sh', Rails.root.join('docker/entrypoint.sh').to_s,
        'ruby', '-e', 'abort unless ARGV == ["two words"] && ENV.values_at("SECRET_KEY_BASE", "DATABASE_PASSWORD", "password_auth_pepper").all? { |v| v == "test-only-secret" }; puts "ok"', 'two words'
      )
      expect(status).to be_success
      expect(output).to eq("ok\n")
    end
  end

  it 'fails before launching a command when a configured secret file is missing' do
    output, status = Open3.capture2e(
      { 'SECRET_KEY_BASE_FILE' => '/nonexistent/projectmonitor-secret' },
      'sh', Rails.root.join('docker/entrypoint.sh').to_s, 'echo', 'should-not-run'
    )
    expect(status).not_to be_success
    expect(output).not_to include('should-not-run')
  end

  it 'closes a successful database readiness connection' do
    client = instance_double(Mysql2::Client)
    expect(Mysql2::Client).to receive(:new).with(hash_including(connect_timeout: 5)).and_return(client)
    expect(client).to receive(:close)
    DatabaseReadiness.wait!
  end

  it 'retries a database that is still starting' do
    client = instance_double(Mysql2::Client, close: nil)
    attempts = 0
    allow(Mysql2::Client).to receive(:new) do
      attempts += 1
      raise Mysql2::Error, 'starting' if attempts == 1
      client
    end
    allow(DatabaseReadiness).to receive(:sleep).with(2)
    expect { DatabaseReadiness.wait! }.to output(/Waiting/).to_stderr
    expect(attempts).to eq(2)
  end

  it 'fails instead of waiting indefinitely for an unavailable database' do
    allow(Mysql2::Client).to receive(:new).and_raise(Mysql2::Error, 'unavailable')
    allow(Process).to receive(:clock_gettime).with(Process::CLOCK_MONOTONIC).and_return(0, 121)
    expect { DatabaseReadiness.wait! }.to raise_error(Mysql2::Error, 'unavailable')
  end

  it 'recognizes the imported schema without replaying historical migrations' do
    expect(ActiveRecord::Base.connection_pool.migration_context.needs_migration?).to eq(false)
    expect(Project.columns_hash.fetch('id').type).to eq(:integer)
    expect(ProjectStatus.columns_hash.fetch('build_id').type).to eq(:integer)
  end
end
