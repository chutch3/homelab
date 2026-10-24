require 'spec_helper'

describe GithubProjectDecorator do
  let(:github_project) { build(:github_project) }

  subject { github_project.decorate }

  describe '#current_build_url' do
    subject { super().current_build_url }
    it { is_expected.to eq('https://github.com/octo-org/octo-repo/actions') }
  end
end
