import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import cast

import github
import typer
from github import Github
from github.PullRequest import PullRequest
from loguru import logger

from git_steak.logging import setup_loguru_logging_interceptor

app = typer.Typer()


def _git_stack_branches() -> list[str]:
    result = subprocess.run(
        ["git", "branchless", "query", "--branches", "main() | stack() & branches()"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip().split()


def _git_main_branch() -> str:
    result = subprocess.run(
        ["git", "branchless", "query", "--branches", "main()"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def _git_force_push(revs: list[str]) -> None:
    main_branch = _git_main_branch()
    revs = [x for x in revs if x != main_branch]
    subprocess.run(
        ["git", "push", "--force", "origin", *revs],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )


@dataclass
class GitCommitInfo:
    commit_title: str
    commit_body: str


def _git_first_commit_info_between_two_revs(
    base_rev: str, head_rev: str
) -> GitCommitInfo:
    rev_list_result = subprocess.run(
        [
            "git",
            "rev-list",
            "--reverse",
            f"{base_rev}..{head_rev}",
        ],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    shas = rev_list_result.stdout.strip().split()

    if not shas:
        return GitCommitInfo(commit_title="", commit_body="\n")

    first_sha = shas[0]

    log_result = subprocess.run(
        [
            "git",
            "log",
            "--pretty=format:%s%n%b",
            "-n",
            "1",
            first_sha,
        ],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    output = log_result.stdout.strip()
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
    gh_pr: PullRequest | None = None


def _run_pull_request_workflow(
    gh: Github,
    wf: PullRequestWorkflow,
    stack: list[PullRequestWorkflow],
) -> None:
    logger.info(
        f"{wf.head_rev}: Syncing PR, base={wf.base_rev}, title={wf.first_commit.commit_title}, pr={wf.gh_pr}"
    )

    gh_repo = gh.get_repo(_git_get_github_repo_name())

    if not wf.gh_pr:
        # WTF, GitHub, need to juggle the name to add to the branch name!?
        repo_namespace = gh_repo.full_name.split("/")[0]
        head_query = f"{repo_namespace}:{wf.head_rev}"
        wf.gh_pr = next(iter(gh_repo.get_pulls(head=head_query, state="open")), None)

    pr_title = wf.first_commit.commit_title
    pr_description = wf.first_commit.commit_body
    if len(stack) > 1:
        if m := re.match(r"\[\d+/\d+\]\s*(.*)$", pr_title):
            pr_title = m.group(1)

        pr_title = f"[{wf.index}/{len(stack)}] {pr_title}"

        stack_description_lines: list[str] = []
        for stack_wf in stack:
            if stack_wf.gh_pr:
                stack_description_lines.append(f"- #{stack_wf.gh_pr.number}\n")
        pr_description = (
            "".join(stack_description_lines) + "\n\n---\n\n" + pr_description
        )

    if wf.gh_pr:
        logger.debug(f"{wf.head_rev}: Found existing PR #{wf.gh_pr}")
        expected_data = (
            pr_title,
            pr_description,
            wf.base_rev,
        )
        actual_data = (
            wf.gh_pr.title,
            wf.gh_pr.body,
            wf.gh_pr.base.ref,
        )
        if expected_data != actual_data:
            logger.info(f"{wf.head_rev}: Updating existing PR #{wf.gh_pr.number}")
            wf.gh_pr.edit(
                title=pr_title,
                body=pr_description,
                base=wf.base_rev,
            )
    else:
        logger.info(f"{wf.head_rev}: Creating new PR")
        workflow_pr = gh_repo.create_pull(
            title=pr_title,
            body=pr_description,
            head=wf.head_rev,
            base=wf.base_rev,
        )
        wf.gh_pr = workflow_pr


def _generate_workflows(
    stack_branches: list[str],
) -> list[PullRequestWorkflow]:
    workflows: list[PullRequestWorkflow] = []
    for index, (base_rev, head_rev) in enumerate(
        zip(stack_branches[:-1], stack_branches[1:]), start=1
    ):
        commit_info = _git_first_commit_info_between_two_revs(base_rev, head_rev)
        workflow = PullRequestWorkflow(
            index=index,
            base_rev=base_rev,
            head_rev=head_rev,
            first_commit=commit_info,
        )
        workflows.append(workflow)
    return workflows


@app.command()
def submit() -> None:
    main_branch = _git_main_branch()
    stack_branches = _git_stack_branches()

    branches_to_push = [x for x in stack_branches if x != main_branch]
    logger.info(f"Git pushing: {', '.join(branches_to_push)}")
    _git_force_push(branches_to_push)

    gh = Github(auth=github.Auth.Token(_gh_get_token()))
    workflows = _generate_workflows(stack_branches)
    with ThreadPoolExecutor() as executor:
        for _ in executor.map(
            _run_pull_request_workflow,
            [gh] * len(workflows),
            workflows,
            [cast(list[PullRequestWorkflow], [])] * len(workflows),
        ):
            pass

        if len(workflows) > 1:
            for _ in executor.map(
                _run_pull_request_workflow,
                [gh] * len(workflows),
                workflows,
                [workflows] * len(workflows),
            ):
                pass
    for wf in workflows:
        if wf.gh_pr:
            logger.info(f"PR: {wf.gh_pr.html_url} for {wf.head_rev}")


def main():
    setup_loguru_logging_interceptor()
    logger.remove()
    logger.add(
        sys.stderr,
        filter={
            "urllib3": "INFO",
        },
    )
    app()
