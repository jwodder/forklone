"""
Fork & clone a GitHub repository

The ``forklone`` command clones a given GitHub repository — unless you don't
have push permission on the repository, in which case ``forklone`` forks it and
clones the fork instead so you get something you can push to.

Visit <https://github.com/jwodder/forklone> or run ``forklone --help`` for more
information.
"""

from __future__ import annotations
from pathlib import Path
from shlex import split
import subprocess
import sys
import time
import click
from ghrepo import GHRepo
from ghtoken import GHTokenNotFound, get_ghtoken
from github import Auth, Github, GithubException

__version__ = "0.1.0.dev1"
__author__ = "John Thorvald Wodder II"
__author_email__ = "forklone@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/forklone"

FORK_SLEEP = 0.1


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    __version__,
    "-V",
    "--version",
    message="%(prog)s %(version)s",
)
@click.option(
    "--clone-opts",
    help=(
        "Pass the given options to the `git clone` command."
        '  Example: --clone-opts="--depth 1 --quiet"'
    ),
    metavar="OPTIONS",
)
@click.option(
    "--org",
    help="Create the fork within the given organization",
    metavar="ORGANIZATION",
)
@click.option(
    "-U",
    "--upstream-remote",
    default="upstream",
    help="Use the given name for the remote for the parent repository",
    metavar="NAME",
    show_default=True,
)
@click.argument("repository")
@click.argument(
    "directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
def main(
    repository: str,
    directory: Path | None,
    clone_opts: str | None,
    org: str | None,
    upstream_remote: str,
) -> None:
    """
    Fork & clone a GitHub repository

    Clones the given GitHub repository to the given directory; if no directory
    is specified, the repository is cloned to a directory with the same name as
    the repository.  If the authenticated user does not have push permission
    on the repository, then the repository is forked (or a pre-existing fork is
    used), and the fork is cloned instead.

    The GitHub repository can be specified in the form `OWNER/NAME` (or, when
    `OWNER` is the authenticated user, just `NAME`) or as a GitHub repository
    URL.

    If the cloned repository ends up being a fork (either because `forklone`
    forked the specified repository or because the repository was already a
    fork), then the clone's upstream remote is set to point to the fork's
    parent repository.

    `forklone` requires a GitHub access token with appropriate permissions in
    order to run.  Specify the token via the `GH_TOKEN` or `GITHUB_TOKEN`
    environment variable (possibly in an `.env` file), by storing a token with
    the `gh` or `hub` command, or by setting the `hub.oauthtoken` Git config
    option in your `~/.gitconfig` file.
    """
    try:
        token = get_ghtoken()
    except GHTokenNotFound:
        raise click.UsageError(
            "GitHub token not found.  Set via GH_TOKEN, GITHUB_TOKEN, gh, hub,"
            " or hub.oauthtoken."
        )
    gh = Github(auth=Auth.Token(token))
    r = GHRepo.parse(repository, default_owner=lambda: gh.get_user().login)
    repo = gh.get_repo(str(r))
    if repo.permissions.push:
        loginfo(f"User has push permissions to {repo.full_name}; not forking")
        clonee = repo
        upstream = repo.parent  # None if not a fork
    else:
        loginfo(f"Forking {repo.full_name} ...")
        if org is None:
            # create_fork() doesn't accept `organization=None`.
            clonee = repo.create_fork()
        else:
            clonee = repo.create_fork(organization=org)
        # If the user/org already has a fork, create_fork() returns that fork.
        while True:
            try:
                # Test readiness of fork by querying for default branch
                clonee.get_branch(repo.default_branch)
            except GithubException as e:
                if e.status == 404:
                    time.sleep(FORK_SLEEP)
                else:
                    raise
            else:
                break
        upstream = repo
    clone_cmd = ["git", "clone"]
    if clone_opts:
        clone_cmd.extend(split(clone_opts))
    clone_cmd.append(clonee.ssh_url)
    if directory is not None:
        clone_cmd.append(str(directory))
        loginfo(f"Cloning {clonee.full_name} to {directory} ...")
    else:
        directory = Path(clonee.name)
        loginfo(f"Cloning {clonee.full_name} ...")
    subprocess.run(clone_cmd, check=True)
    if upstream is not None:
        loginfo(f"Pointing {upstream_remote!r} remote to parent repo ...")
        if upstream_remote == "origin":
            runcmd("git", "remote", "rm", "origin", cwd=directory)
        runcmd(
            "git",
            "remote",
            "add",
            "-f",
            upstream_remote,
            upstream.clone_url,
            cwd=directory,
        )


def runcmd(*args: str, cwd: Path) -> None:
    # click.echo('+' + ' '.join(args), err=True)
    r = subprocess.run(args, cwd=cwd)
    if r.returncode != 0:
        # Don't clutter the output with a stack trace.
        sys.exit(r.returncode)


def loginfo(msg: str) -> None:
    click.secho(msg, err=True, bold=True)


if __name__ == "__main__":
    main()
