bind 'tcp://0.0.0.0:3000'
threads 1, 1
workers Integer(ENV.fetch('WEB_CONCURRENCY', '2'))
preload_app!
