require 'spec_helper'

describe TddiumProjectDecorator do
  let(:tddium_project) { build(:tddium_project) }

  subject { tddium_project.decorate }

  describe '#current_build_url' do
    subject { super().current_build_url }
    it { is_expected.to eq('https://api.tddium.com/dashboard?auth_token=projectmonitor-test-token-2') }
  end
end
