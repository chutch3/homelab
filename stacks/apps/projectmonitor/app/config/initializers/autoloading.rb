# Preserve the names of the legacy Cloud Foundry helpers.
Rails.autoloaders.each do |loader|
  loader.inflector.inflect(
    'ip_whitelisted_controller' => 'IPWhitelistedController',
    'ci_polling_strategy' => 'CIPollingStrategy',
    'cf_authenticator' => 'CF_authenticator',
    'cf_deploy' => 'CF_deploy',
    'cf_git_tagger' => 'CF_git_tagger'
  )
  loader.ignore(Rails.root.join('lib/tasks'), Rails.root.join('lib/cert'), Rails.root.join('lib/devise'))
end
