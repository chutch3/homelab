Capybara.register_driver :selenium_chromium do |app|
  options = Selenium::WebDriver::Chrome::Options.new
  options.binary = ENV['CHROME_BIN'] if ENV['CHROME_BIN']
  options.add_argument('--headless=new')
  options.add_argument('--no-sandbox')
  options.add_argument('--disable-dev-shm-usage')
  Capybara::Selenium::Driver.new(app, browser: :chrome, options: options)
end
Capybara.server = :puma, { Silent: true }
