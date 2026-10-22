require 'mysql2'

module DatabaseReadiness
  def self.wait!
    deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + 120
    begin
      client = Mysql2::Client.new(
        host: ENV.fetch('DATABASE_HOST', '127.0.0.1'),
        port: ENV.fetch('DATABASE_PORT', '3306').to_i,
        username: ENV.fetch('DATABASE_USER', 'projectmonitor'),
        password: ENV.fetch('DATABASE_PASSWORD', ''),
        database: ENV.fetch('DATABASE_NAME', 'projectmonitor'),
        connect_timeout: 5
      )
      client.close
    rescue Mysql2::Error
      raise if Process.clock_gettime(Process::CLOCK_MONOTONIC) >= deadline
      warn 'Waiting for Project Monitor database'
      sleep 2
      retry
    end
  end
end

DatabaseReadiness.wait! if $PROGRAM_NAME == __FILE__
