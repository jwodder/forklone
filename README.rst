|repostatus| |ci-status| |license|

.. |repostatus| image:: https://www.repostatus.org/badges/latest/concept.svg
    :target: https://www.repostatus.org/#concept
    :alt: Project Status: Concept – Minimal or no implementation has been done
          yet, or the repository is only intended to be a limited example,
          demo, or proof-of-concept.

.. |ci-status| image:: https://github.com/jwodder/forklone/actions/workflows/test.yml/badge.svg
    :target: https://github.com/jwodder/forklone/actions/workflows/test.yml
    :alt: CI Status

.. |license| image:: https://img.shields.io/github/license/jwodder/forklone.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/forklone>`_
| `Issues <https://github.com/jwodder/forklone/issues>`_

The ``forklone`` command clones a given GitHub repository — unless you don't
have push permission on the repository, in which case ``forklone`` forks it and
clones the fork instead so you get something you can push to.


Installation
============
``forklone`` requires Python 3.10 or higher.  Just use `pip
<https://pip.pypa.io>`_ for Python 3 (You have pip, right?) to install it::

    python3 -m pip install git+https://github.com/jwodder/forklone.git


Usage
=====

::

    forklone [<options>] <github-repo> [<directory>]

Clones the given GitHub repository to the given directory; if no directory is
specified, the repository is cloned to a directory with the same name as the
repository.  If the authenticated user does not have push permission on the
repository, then the repository is forked (or a pre-existing fork is used), and
the fork is cloned instead.

The GitHub repository can be specified in the form ``OWNER/NAME`` (or, when
``OWNER`` is the authenticated user, just ``NAME``) or as a GitHub repository
URL.

If the cloned repository ends up being a fork (either because ``forklone``
forked the specified repository or because the repository was already a fork),
then the clone's upstream remote is set to point to the fork's parent
repository.


Options
-------

--clone-opts OPTIONS        Pass the given options to the ``git clone``
                            command.

                            Example: ``--clone-opts="--depth 1 --quiet"``

--org ORGANIZATION          Create the fork within the given organization

-U, --upstream-remote NAME  Use the given name for the remote for the parent
                            repository [default value: "upstream"]


Authentication
--------------

``forklone`` requires a GitHub access token with appropriate permissions in
order to run.  Specify the token via the ``GH_TOKEN`` or ``GITHUB_TOKEN``
environment variable (possibly in an ``.env`` file), by storing a token with
the ``gh`` or ``hub`` command, or by setting the ``hub.oauthtoken`` Git config
option in your ``~/.gitconfig`` file.
