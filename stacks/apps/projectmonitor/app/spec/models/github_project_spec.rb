require 'spec_helper'

describe GithubProject, :type => :model do

  subject { build(:github_project) }

  describe 'validations' do
    it { is_expected.to validate_presence_of(:ci_build_identifier) }
    it { is_expected.to validate_presence_of(:ci_auth_token) }
  end

  describe 'accessors' do
    subject { build(:github_project, build_branch: branch_name) }
    let(:branch_name) { "foo" }

    describe "branch related" do
      context "when a branch is specified" do
        let(:branch_name) { "foo" }

        describe '#feed_url' do
          it { expect(subject.feed_url).to eq('https://api.github.com/repos/octo-org/octo-repo/actions/runs?branch=foo&per_page=8') }
        end

        describe '#build_status_url' do
          it { expect(subject.build_status_url).to eq('https://api.github.com/repos/octo-org/octo-repo/actions/runs?branch=foo&per_page=8') }
        end
      end

      context "when a branch is not specified" do
        let(:branch_name) { nil }

        describe '#feed_url' do
          it { expect(subject.feed_url).to eq('https://api.github.com/repos/octo-org/octo-repo/actions/runs?branch=master&per_page=8') }
        end

        describe '#build_status_url' do
          it { expect(subject.build_status_url).to eq('https://api.github.com/repos/octo-org/octo-repo/actions/runs?branch=master&per_page=8') }
        end
      end
    end

    describe '#ci_build_identifier' do
      it { expect(subject.ci_build_identifier).to eq('octo-org/octo-repo') }
    end

    describe '#accept_mime_types' do
      it { expect(subject.accept_mime_types).to eq('application/vnd.github+json') }
    end

    describe '#additional_headers' do
      it 'sends the token as an Authorization header and a User-Agent' do
        expect(subject.additional_headers).to eq({
          'Authorization' => 'token projectmonitor-test-token-2',
          'User-Agent' => 'ProjectMonitor',
          'X-GitHub-Api-Version' => '2022-11-28',
        })
      end
    end

    describe '#fetch_payload' do
      it { expect(subject.fetch_payload).to be_an_instance_of(GithubPayload) }

      describe 'when a branch name is specified' do
        subject { build(:github_project, build_branch: 'abracadabra') }

        it 'sets build_branch for the created payload' do
          expect(subject.fetch_payload.branch).to eq(subject.build_branch)
        end
      end
    end
  end
end
