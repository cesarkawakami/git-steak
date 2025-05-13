from ast import Not
from dataclasses import dataclass
import subprocess
from github import Github
import github
import typer

app = typer.Typer()


def _git_stack_branches() -> list[str]:
    result = subprocess.run(
        ["git", "branchless", "query", "--branches", "main() | stack() & branches()"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip().split()


@dataclass
class GitCommitInfo:
    commit_title: str
    commit_body: str


def _git_first_commit_info_between_two_revs(
    base_rev: str, head_rev: str
) -> GitCommitInfo:
    result = subprocess.run(
        [
            "git",
            "log",
            "--pretty=format:%s%n%b",
            "-n",
            "1",
            f"{base_rev}..{head_rev}",
        ],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    output = result.stdout.strip()
    commit_title, _, commit_body = output.partition("\n")
    return GitCommitInfo(
        commit_title=commit_title,
        commit_body=commit_body.strip() + "\n",
    )


def _git_get_github_repo_name() -> str:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    url = result.stdout.strip()
    if url.startswith("git@github.com:"):
        repo_name = url.removeprefix("git@github.com:")
    elif url.startswith("https://github.com/"):
        repo_name = url.removeprefix("https://github.com/")
    else:
        raise ValueError(f"Unsupported git remote URL format: {url}")

    if repo_name.endswith(".git"):
        repo_name = repo_name.removesuffix(".git")
    return repo_name


def _gh_get_token() -> str:
    result = subprocess.run(
        ["gh", "auth", "token"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


@dataclass
class PullRequestWorkflow:
    index: int
    base_rev: str
    head_rev: str
    first_commit: GitCommitInfo
    gh_pr_number: int | None = None


def _run_pull_request_workflow(wf: PullRequestWorkflow) -> None:
    raise NotImplementedError()


@app.command()
def submit() -> None:
    stack_branches = _git_stack_branches()

    gh = Github(auth=github.Auth.Token(_gh_get_token()))
    gh_repo = gh.get_repo(_git_get_github_repo_name())
    gh_repo.get_pulls(head=)


def main():
    typer.run(app)
