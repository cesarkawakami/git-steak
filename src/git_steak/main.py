from dataclasses import dataclass
import subprocess
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
    before_rev: str, after_rev: str
) -> GitCommitInfo:
    result = subprocess.run(
        [
            "git",
            "log",
            "--pretty=format:%s%n%b",
            "-n",
            "1",
            f"{before_rev}..{after_rev}",
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


@app.command()
def submit() -> None:
    stack_branches = _git_stack_branches()


def main():
    typer.run(app)
