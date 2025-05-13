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
    # This should grab the first commit between two revs and return its title and body. AI!



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
