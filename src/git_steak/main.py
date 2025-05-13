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
    before_rev: str, afte_rev: str
) -> GitCommitInfo:
    result = subprocess.run(
        [
            "git",
            "log",
            "--pretty=format:%s%n%b",
            "-n",
            "1",
            f"{before_rev}..{afte_rev}",
        ],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    output = result.stdout.strip()
    parts = output.split("\n", 1)
    commit_title = parts[0]
    commit_body = parts[1] if len(parts) > 1 else ""
    return GitCommitInfo(commit_title=commit_title, commit_body=commit_body)


def _gh_pr_exists(branch_name: str) -> bool:
    result = subprocess.run(
        ["gh", "pr", "view", branch_name],
        capture_output=True,
        encoding="utf-8",
    )
    return result.returncode == 0


def _gh_pr_create(head_branch_name: str, base_branch_name: str) -> None:
    subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base_branch_name,
            "--head",
            head_branch_name,
            "--fill-first",
        ],
        check=True,
    )


def _gh_pr_edit(head_branch_name: str, base_branch_name: str) -> None:
    subprocess.run(
        [
            "gh",
            "pr",
            "edit",
            "--base",
            base_branch_name,
            head_branch_name,
        ],
        check=True,
    )


@app.command()
def submit() -> None:
    stack_branches = _git_stack_branches()


def main():
    typer.run(app)
