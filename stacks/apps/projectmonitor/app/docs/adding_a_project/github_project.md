## GitHub Actions

Project Monitor polls the GitHub Actions
[workflow runs API](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository)
for a repository and reports the status of the most recent run on a branch.

__Polling__

1. Add the repository to the "Repository (owner/repo)" field below, e.g. `rails/rails`.
2. Set the "Branch Name" field to the branch you want to watch. The default is `master`.
3. Create a [personal access token](https://github.com/settings/tokens) with read
   access to Actions for the repository (the `repo` scope for classic tokens, or
   `actions:read` for fine-grained tokens) and paste it into the "Personal Access
   Token" field below.

To test the token, call the API with curl:

~~~
$ curl -H "Authorization: token :token" \
       -H "Accept: application/vnd.github+json" \
       https://api.github.com/repos/:owner/:repo/actions/runs
~~~

You should see a JSON response containing a `workflow_runs` array, each entry of
which has `status`, `conclusion`, `run_number` and `html_url` fields.
