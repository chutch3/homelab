#!/usr/bin/env bash
set -euo pipefail
export RAILS_ENV=test
export DATABASE_NAME=projectmonitor_test
bundle exec ruby docker/wait-for-database.rb
bundle exec rake db:schema:load
bundle exec rspec
bundle exec ruby script/check-compatibility-coverage.rb
npm run test:javascript
