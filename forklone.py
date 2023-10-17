from shlex import split
import subprocess
import sys
import time
import click
from ghrepo import GHRepo
from ghtoken import GHTokenNotFound, get_ghtoken
from github import Github, GithubException

__author__ = "John Thorvald Wodder II"
__author_email__ = "forklone@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/forklone"

FORK_SLEEP = 0.1


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--clone-opts",
    help="Pass the given options to the `git clone` command."
    '  Example: --clone-opts="--depth 1 --quiet"',
    metavar="OPTIONS",
)
@click.option(
    "--org",
    help="Fork the repository within the given organization",
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
@click.argument("directory", required=False)
@click.pass_context
def main(ctx, repository, directory, clone_opts, org, upstream_remote):
    """
    Fork & clone a GitHub repository

    Clones the given GitHub repository to the given directory; if no directory
    is specified, the repository is cloned to a directory with the same name as
    the repository.  If the authenticating user does not have push permission
    on the repository, then the repository is forked (or a pre-existing fork is
    used), and the fork is cloned instead.

    The GitHub repository can be specified in the form `OWNER/NAME` (or, when
    `OWNER` is the authenticating user, just `NAME`) or as a GitHub repository
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
        ctx.fail(
            "GitHub token not found.  Set via GH_TOKEN, GITHUB_TOKEN, gh, hub,"
            " or hub.oauthtoken."
        )
    gh = Github(token)
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
    if directory:
        clone_cmd.append(directory)
        loginfo(f"Cloning {clonee.full_name} to {directory} ...")
    else:
        directory = clonee.name
        loginfo(f"Cloning {clonee.full_name} ...")
    subprocess.run(clone_cmd, check=True)
    if upstream is not None:
        loginfo(f"Pointing {upstream_remote!r} remote to parent repo ...")
        if upstream_remote == "origin":
            runcmd("git", "-C", directory, "remote", "rm", "origin")
        runcmd(
            "git",
            "-C",
            directory,
            "remote",
            "add",
            "-f",
            upstream_remote,
            upstream.clone_url,
        )


def runcmd(*args, **kwargs):
    # click.echo('+' + ' '.join(args), err=True)
    r = subprocess.run(args, **kwargs)
    if r.returncode != 0:
        # Don't clutter the output with a stack trace.
        sys.exit(r.returncode)


def loginfo(msg):
    click.secho(msg, err=True, bold=True)


if __name__ == "__main__":
    main()
