from ast import Not
from dataclasses import dataclass
import subprocess
from github import Github
import github
import rich
import rich.progress
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
    base_rev: str
    head_rev: str
    first_commit: GitCommitInfo
    gh_pr_number: int | None = None


def _run_pull_request_workflow(
    progress: rich.progress.Progress,
    gh_repo: github.Repository,
    wf: PullRequestWorkflow,
    stack: list[PullRequestWorkflow],
) -> None:
    # head_rev is already the final one, no need to construct head_branch_name. AI!
    # Construct the head string in the format owner:branch
    head_branch_name = wf.head_rev
    if ":" not in head_branch_name: # Ensure owner prefix if not already there
        head_branch_name = f"{gh_repo.owner.login}:{wf.head_rev}"

    existing_pulls = gh_repo.get_pulls(
        state="open", head=head_branch_name, base=wf.base_rev
    )

    pr_to_update_or_create = None
    if existing_pulls.totalCount > 0:
        pr_to_update_or_create = existing_pulls[0]
        wf.gh_pr_number = pr_to_update_or_create.number

        needs_update = False
        update_args = {}
        if pr_to_update_or_create.title != wf.first_commit.commit_title:
            update_args["title"] = wf.first_commit.commit_title
            needs_update = True
        if pr_to_update_or_create.body != wf.first_commit.commit_body:
            update_args["body"] = wf.first_commit.commit_body
            needs_update = True

        # Base is already confirmed by the get_pulls query, but if we wanted to allow changing it:
        # if pr_to_update_or_create.base.ref != wf.base_rev:
        #     update_args["base"] = wf.base_rev
        #     needs_update = True

        if needs_update:
            pr_to_update_or_create.edit(**update_args)
            rich.print(f"Updated PR #{pr_to_update_or_create.number}: {pr_to_update_or_create.html_url}")
        else:
            rich.print(f"PR #{pr_to_update_or_create.number} is already up-to-date: {pr_to_update_or_create.html_url}")


    else:
        pr_to_update_or_create = gh_repo.create_pull(
            title=wf.first_commit.commit_title,
            body=wf.first_commit.commit_body,
            head=wf.head_rev,  # For create_pull, just branch name is fine
            base=wf.base_rev,
        )
        wf.gh_pr_number = pr_to_update_or_create.number
        rich.print(f"Created PR #{pr_to_update_or_create.number}: {pr_to_update_or_create.html_url}")


@app.command()
def submit() -> None:
    stack_branches = _git_stack_branches()

    gh = Github(auth=github.Auth.Token(_gh_get_token()))
    gh_repo = gh.get_repo(_git_get_github_repo_name())
    # gh_repo.get_pulls(head=)


def main():
    typer.run(app)
