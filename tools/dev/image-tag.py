"""Read-only semantic-release adapter for local build/publish image tags."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from time import time_ns

from git import Repo
from semantic_release.cli.config import BranchConfig, GlobalCommandLineOptions, RawConfig, RuntimeContext
from semantic_release.cli.util import load_raw_config_file
from semantic_release.enums import LevelBump
from semantic_release.version.algorithm import next_version


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    config = load_raw_config_file(root / "pyproject.toml")
    config["repo_dir"] = str(root)
    raw = RawConfig.model_validate(config)
    # Calculation only: accept feature branches without changing release policy.
    raw.branches = {"image": BranchConfig(match=".*", prerelease=True, prerelease_token="dev")}
    with Repo(root) as repo:
        if repo.head.is_detached or repo.git.rev_parse("--is-shallow-repository") == "true":
            raise ValueError("automatic image tags require a branch and full local Git history; set IMAGE_TAG to override")
        runtime = RuntimeContext.from_raw_config(raw, GlobalCommandLineOptions(noop=True))
        version = next_version(
            repo, runtime.version_translator, runtime.commit_parser,
            allow_zero_version=runtime.allow_zero_version,
            major_on_zero=runtime.major_on_zero, prerelease=True,
        )
        # Docs-only or uncommitted work still needs a development tag, never a
        # previously released stable version. PSR performs the patch increment.
        if not version.is_prerelease:
            version = version.bump(LevelBump.PATCH).to_prerelease(token="dev")
        sha = repo.git.rev_parse("--short=12", "HEAD")
        dirty = ".dirty" if repo.is_dirty(untracked_files=True) else ""
        print(f"{version}.t{time_ns()}.g{sha}{dirty}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Unable to determine IMAGE_TAG: {type(exc).__name__}. Check release configuration and Git history, or set IMAGE_TAG explicitly.", file=sys.stderr)
        raise SystemExit(1) from None
