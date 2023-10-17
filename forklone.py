#!/usr/bin/env python3
# The MIT License (MIT)
#
# Copyright (c) 2020-2021, 2023 John Thorvald Wodder II
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
forklone.py — Fork & clone a GitHub repository
==============================================

::

    forklone.py [<options>] <github-repo> [<directory>]

If the user has push permissions to the given GitHub repository, the repo is
cloned normally.  If the repository is a fork, the clone's upstream remote is
set to point to the parent repository.

If the user does not have push permissions, then the repository is forked (or a
pre-existing fork is used), the fork is cloned, and the clone's upstream remote
is set to point to the parent repository.

A GitHub repository can be specified using the following formats::

    https://github.com/$OWNER/$NAME
    $OWNER/$NAME
    $NAME  [for a repository owned by the authenticating user]

Options
-------

--clone-opts OPTIONS        Pass the given options to the `git clone` command.
                            Example: --clone-opts="--depth 1 --quiet"

--org ORGANIZATION          Fork the repository within the given organization

-U, --upstream-remote NAME  Use the given name for the remote for the parent
                            repository [default value: "upstream"]

Authentication
--------------

This script requires a GitHub access token in order to run.  Specify the token
via the ``GH_TOKEN`` or ``GITHUB_TOKEN`` environment variable (possibly in an
``.env`` file), by storing a token with the ``gh`` or ``hub`` command, or by
setting the ``hub.oauthtoken`` Git config option.
"""

__requires__ = [
    "click >= 7.0",
    "ghrepo ~= 0.1",
    "ghtoken ~= 0.1",
    "PyGithub ~= 1.53",
]

__requires_python__ = ">= 3.6"

__author__       = 'John Thorvald Wodder II'
__author_email__ = 'forklone@varonathe.org'
__license__      = 'MIT'
__url__          = 'https://gist.github.com/cee837802578a4fc8854df60529af98c'

import os
from   shlex  import split
import subprocess
import sys
import time
import click
from   ghrepo import GHRepo
from   ghtoken import GHTokenNotFound, get_ghtoken
from   github import Github, GithubException

FORK_SLEEP = 0.1

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    '--clone-opts',
    help='Pass the given options to the `git clone` command.'
         '  Example: --clone-opts="--depth 1 --quiet"',
    metavar='OPTIONS',
)
@click.option(
    '--org',
    help='Fork the repository within the given organization',
    metavar='ORGANIZATION',
)
@click.option(
    '-U', '--upstream-remote',
    default='upstream',
    help='Use the given name for the remote for the parent repository',
    metavar='NAME',
    show_default=True,
)
@click.argument('repository')
@click.argument('directory', required=False)
@click.pass_context
def main(ctx, repository, directory, clone_opts, org, upstream_remote):
    """
    forklone.py — Fork & clone a GitHub repository

    If the user has push permissions to the given GitHub repository, the repo
    is cloned normally.  If the repository is a fork, the clone's upstream
    remote is set to point to the parent repository.

    If the user does not have push permissions, then the repository is forked
    (or a pre-existing fork is used), the fork is cloned, and the clone's
    upstream remote is set to point to the parent repository.

    A GitHub repository can be specified using the following formats:

    \b
        https://github.com/$OWNER/$NAME
        $OWNER/$NAME
        $NAME  [for a repository owned by the authenticating user]

    This script requires a GitHub access token in order to run.  Specify the
    token via the ``GH_TOKEN`` or ``GITHUB_TOKEN`` environment variable
    (possibly in an ``.env`` file), by storing a token with the ``gh`` or
    ``hub`` command, or by setting the ``hub.oauthtoken`` Git config option.
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
            runcmd('git', '-C', directory, 'remote', 'rm', 'origin')
        runcmd(
            'git', '-C', directory,
            'remote', 'add', '-f', upstream_remote, upstream.clone_url,
        )

def runcmd(*args, **kwargs):
    #click.echo('+' + ' '.join(args), err=True)
    r = subprocess.run(args, **kwargs)
    if r.returncode != 0:
        # Don't clutter the output with a stack trace.
        sys.exit(r.returncode)

def loginfo(msg):
    click.secho(msg, err=True, bold=True)

if __name__ == '__main__':
    main()
