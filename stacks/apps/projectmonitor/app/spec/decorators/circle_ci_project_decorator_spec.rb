require 'spec_helper'

describe CircleCiProjectDecorator do
  let(:circle_ci_project) { build(:circle_ci_project) }

  subject { circle_ci_project.decorate }

  describe '#current_build_url' do
    subject { super().current_build_url }
    it { is_expected.to eq('https://circleci.com/api/v1/project/username/a-project?circle-token=projectmonitor-test-token-2') }
  end
end
