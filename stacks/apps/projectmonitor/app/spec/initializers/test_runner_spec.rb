require 'spec_helper'
require 'open3'
require 'tmpdir'

RSpec.describe 'Homelab test runner' do
  it 'runs Compose from the application root and cleans up after success or failure' do
    Dir.mktmpdir do |directory|
      log = File.join(directory, 'commands')
      command = File.join(directory, 'docker')
      File.write(command, <<~SH)
        #!/bin/sh
        printf '%s|%s\n' "$PWD" "$*" >> "$COMMAND_LOG"
        case "$*" in
          *' up '*) exit "$TEST_EXIT" ;;
        esac
      SH
      File.chmod(0755, command)

      [0, 7].each do |exit_code|
        File.write(log, '')
        _, status = Open3.capture2e(
          { 'PATH' => "#{directory}:#{ENV.fetch('PATH')}", 'COMMAND_LOG' => log,
            'PROJECTMONITOR_TEST_LOCAL' => '0', 'TEST_EXIT' => exit_code.to_s },
          '/bin/bash', Rails.root.join('script/test.sh').to_s, chdir: directory
        )
        expect(status.exitstatus).to eq(exit_code)
        commands = File.readlines(log, chomp: true)
        expect(commands.length).to eq(2)
        prefix = "#{Rails.root}|compose -p projectmonitor-tests-"
        expect(commands.first).to match(/\A#{Regexp.escape(prefix)}\d+ -f compose\.test\.yml up --build --abort-on-container-exit --exit-code-from tests\z/)
        expect(commands.last).to eq(commands.first.sub(
          'up --build --abort-on-container-exit --exit-code-from tests',
          'down --volumes --remove-orphans'
        ))
      end
    end
  end

  it 'runs the local suite from the application root and stops when a command fails' do
    Dir.mktmpdir do |directory|
      log = File.join(directory, 'commands')
      %w[bundle npm bash].each do |name|
        command = File.join(directory, name)
        File.write(command, <<~SH)
          #!/bin/sh
          printf '%s|%s|%s\n' "${0##*/}" "$PWD" "$*" >> "$COMMAND_LOG"
          if [ "${0##*/}" = "$FAIL_COMMAND" ]; then exit 7; fi
        SH
        File.chmod(0755, command)
      end
      expected = ["bundle|#{Rails.root}|check", "npm|#{Rails.root}|ci",
                  "bash|#{Rails.root}|script/test-all.sh"]
      { '' => 3, 'bundle' => 1, 'npm' => 2, 'bash' => 3 }.each do |failure, count|
        File.write(log, '')
        _, status = Open3.capture2e(
          { 'PATH' => "#{directory}:#{ENV.fetch('PATH')}", 'COMMAND_LOG' => log,
            'PROJECTMONITOR_TEST_LOCAL' => '1', 'FAIL_COMMAND' => failure },
          '/bin/bash', Rails.root.join('script/test.sh').to_s, chdir: directory
        )
        expect(status.exitstatus).to eq(failure.empty? ? 0 : 7)
        expect(File.readlines(log, chomp: true)).to eq(expected.take(count))
      end
    end
  end
end
