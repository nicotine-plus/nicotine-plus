<!--
  SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
  SPDX-License-Identifier: GPL-3.0-or-later
-->

# Development

This document contains important information about Nicotine+ design decisions
and development procedures for maintainers, developers and code contributors
alike.


## Sections

 - [Language and Toolkit](#language-and-toolkit)
 - [Dependencies](#dependencies)
 - [Design](#design)
 - [Performance](#performance)
 - [Debug Logging](#debug-logging)
 - [Soulseek Protocol](#soulseek-protocol)
 - [Continuous Integration Testing](#continuous-integration-testing)
 - [Translations](#translations)
 - [Releases](#releases)


## Language and Toolkit

### Python

Nicotine+ is Python application, originally based on backend code from the
PySoulSeek project started in 2001. We only use Python in our codebase, as this
allows for running Nicotine+ on almost any system without compiling anything.
Developing in a single language is also easier for everyone involved in the
project.

We aim to support the oldest [Python version](https://devguide.python.org/versions/)
still receiving security updates, up to the latest. There is no rush to bump the
minimum version requirement, since LTS distributions may use older Python
versions, but a smaller range of versions is easier to test.

### GTK

Nicotine+ and its predecessors PySoulSeek and Nicotine were originally
developed with GNU/Linux in mind, at a time when the official Soulseek client
only supported Windows. The Nicotine project opted to use GTK as the GUI
toolkit, as opposed to wxPython previously used by PySoulSeek. This decision
was made due to various issues encountered in wxPython at the time, such as
large memory overhead and long compile/build times.

GTK fits our needs, and we have no plans of switching to another toolkit.


## Dependencies

Nicotine+ aims to be as portable as possible, providing access to the Soulseek
network for people who cannot run the official Soulseek client. Nicotine+ runs
on almost any architecture and system available, and has active users on a
plethora of different systems. This also means that the introduction of an
external software dependency can be an inconvenience for both packagers and
users.

Modules included in the Python Standard Library should be preferred whenever
possible. Avoid introducing "convenient" and "new hotness" dependencies, if the
standard library already includes the required functionality to some degree. If
a new dependency is necessary, think about the following points:

 - Prefer pure-Python dependencies, as these are easier to install and more
   likely to work on less common systems and architectures.
 - Attempt to find small, self-contained dependencies that can be bundled with
   the Nicotine+ source code (and give proper attribution). Use common sense
   though; do not bundle security-critical dependencies, rapidly changing APIs
   etc.

The current dependencies for Nicotine+ are described in [DEPENDENCIES.md](DEPENDENCIES.md).


## Design

Keep it simple. Many applications fall in the trap of adding endless options
without thinking about the bigger picture. Nicotine+ is feature-rich, but
attempts to provide well-designed, well-integrated features that work out of
the box.

The same principle applies when writing code. Try to simplify code as much as
possible. Avoid overengineering. We want to write code that is maintainable
and readable by humans.


## Performance

Profiling code changes from time to time is important, to ensure that Nicotine+
performs well and uses fewer system resources. Our goal is to develop a
lightweight client that runs well on older hardware, as well as small servers.

Due to Python's interpreted nature, addressing performance issues can be a
challenge. There is no straightforward way of solving every performance issue,
but these points generally help:

 - Use different data structures and algorithms, e.g. dictionaries and sets for
   faster membership checks (*O(1)*) compared to lists (*O(n)*).
 - Use existing functionality in the Python Standard Library when available.
   Parts of the standard library are written in C, and perform better than
   pure-Python counterparts, especially in hot code paths.
 - Look for alternative ways of accomplishing a task, and measure the
   performance. Search engines help a lot here.

[py-spy](https://github.com/benfred/py-spy) is an excellent tool for profiling
in real time while [running Nicotine+ directly from a local Git folder](TESTING.md#git)
and starting with:

```sh
py-spy top ./nicotine
```

The console will continuously display a top like view of functions consuming
CPU. Press `L` to aggregate by line number, and `R` to reset the view.


## Debug Logging

Verbose logging can be enabled to ease debugging. The following log categories
are available:

 - Connections – Logging related to networking ([slskproto.py](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/pynicotine/slskproto.py))
 - Messages – Incoming and outgoing protocol messages ([slskmessages.py](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/pynicotine/slskmessages.py))
 - Transfers – Logging related to file transfers ([transfers.py](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/pynicotine/transfers.py))
 - Miscellaneous – General debug log messages

In order to enable debug logging:

 - Click the ellipsis icon in the bottom right corner of the main window to
   show the log pane
 - Right-click the log pane to show the context menu. Enable the log categories
   you need in the `Log Categories` submenu.

If you want to log debug messages to file, `Menu -> Preferences -> Logging ->
Log debug messages to file`. Remember to disable debug logging when you no
longer need it, since it impacts performance.


## Soulseek Protocol

The Soulseek network uses its own protocol for interoperability between
clients. The protocol is proprietary, and no official documentation is
available. Nicotine+'s protocol implementation is developed by observing the
behavior of the official Soulseek NS and SoulseekQt clients.

[SLSKPROTOCOL.md](SLSKPROTOCOL.md) contains unofficial documentation maintained
by the Nicotine+ team.


## Continuous Integration Testing

It is important that all changes pass unit and integration testing. To properly
validate that things are working, continuous integration (CI) is implemented
using GitHub Actions workflows, which run tests on various platforms for each
commit.

### Creating Tests

Tests are defined in the [pynicotine/tests/](https://github.com/nicotine-plus/nicotine-plus/tree/HEAD/pynicotine/tests/)
folder, and should be expanded to cover larger parts of the client when
possible.

### Running Tests

Although GitHub Actions runs tests automatically when pushing changes to the
repository, it is also possible to run them locally. This can be helpful to
quickly test smaller changes, but local testing should not be relied upon for
changes that affect packaging or are likely to break on other platforms.

To run unit and integration tests using Python's unittest module:
```sh
python3 -m unittest
```

To check the code style using pycodestyle:
```sh
python3 -m pycodestyle
```

To perform code linting using Pylint:
```sh
python3 -m pylint --recursive=y .
```

To test building the application:
```sh
python3 -m build
```


## Translations

Translations are largely handled by [Weblate](https://weblate.org/), but
certain manual operations need to be performed at times.

### Adding a Language

When Nicotine+ is translated into a new language, the following should be done:

 - Update the copyright header of the `XX.po` file:

   ```
   # SPDX-FileCopyrightText: 20XX Nicotine+ Translators
   # SPDX-License-Identifier: GPL-3.0-or-later
   ```

 - Remove the `PACKAGE VERSION` value of `Project-Id-Version` in the `XX.po`
   file:

   ```
   "Project-Id-Version: \n"
   ```

 - Add the language code to the [po/LINGUAS](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/po/LINGUAS)
   and [pynicotine/i18n.py](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/pynicotine/i18n.py)
   files once the translation is close to completion

### Updating Translation Template

The translation template file [po/nicotine.pot](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/po/nicotine.pot)
should be updated after modifying strings in the codebase. To update the
template, run the following command:

```sh
python3 data/scripts/update_translation_template.py
```

### Merging Translation Updates

When translations are modified, Weblate creates a pull request with the changes
within 24 hours. In order to preserve author information for commits, use the
`Create a merge commit` option when merging the pull request.


## Releases

Nicotine+ uses the following versioning scheme: `A.B.C`, e.g. `3.3.8`

  - `A` is incremented when major changes are made to the user interface that
    significantly change the workflow of the application. In practice, this is
    unlikely to happen.
  - `B` is incremented when significant features or new dependencies are added,
    version requirements are increased, or in the case of major changes to
    existing code that are deemed too intrusive for a smaller release. The
    previous feature branch (e.g. `3.3.x`) is created in case any critical bugs
    are discovered while the next planned release is still in development.
  - `C` is incremented when bug fixes, performance improvements or smaller
    tweaks to existing functionality are made. Low-risk functionality that does
    not affect translatable strings can also be added.

Release dates are not set in stone, as Nicotine+ development is done by
volunteers in their spare time. However, keep the following points in mind:

 - Taking too long to release a new Nicotine+ version (e.g. years) will likely
   result in Nicotine+ no longer functioning due to technological advancements,
   or being removed from distributions. This previously occurred when support
   for Python 2 ended in 2020.
 - We have no means of delivering updates to all users at the same time.
   Packagers for numerous distributions have to package and test new Nicotine+
   releases before they can be delivered to users.
 - Releasing large updates can make it more difficult to pinpoint eventual
   issues that were introduced since the previous release.
 - The final bug fix release (`C`) of each feature branch (`B`) has to be very
   stable before any dependency requirements are bumped, because legacy users
   might end up needing to use an old version for a long time.

### Creating a Nicotine+ Release

The following is a step-by-step guide detailing what a Nicotine+ maintainer
should do when releasing a new version of Nicotine+.

 1. Ensure that Nicotine+ launches and works well on at least these operating
    systems:
    - Windows
    - macOS
    - Ubuntu 18.04 (oldest supported GTK 3 and Python 3 versions)
    - Ubuntu 22.04 (oldest supported GTK 4 version)
    - Latest Ubuntu/Fedora release

 2. Update the translation template by running
 
    ```sh
    python3 data/scripts/update_translation_template.py
    ```

 3. Ensure that the source distribution (sdist) includes all necessary files to
    run Nicotine+. A source distribution can be generated by running

    ```sh
    python3 -m build --sdist
    ```

 4. Add a new release note entry to NEWS.md. Release notes should contain a
    user-readable list of noteworthy changes since the last release (not a list
    of commits), as well as a list of closed issues on GitHub.

 5. Increase the Nicotine+ version number / add new version entries in the
    master branch.
    The following files need to be modified:
    - [NEWS.md](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/NEWS.md)
    - [README.md](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/README.md)
    - [data/org.nicotine_plus.Nicotine.appdata.xml.in](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/data/org.nicotine_plus.Nicotine.appdata.xml.in)
    - [debian/changelog](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/debian/changelog)
    - [pynicotine/\_\_init\_\_.py](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/pynicotine/__init__.py)

 6. Ensure that the Windows and macOS packages generated by [GitHub Actions](https://github.com/nicotine-plus/nicotine-plus/actions)
    still work.

 7. Create a new GitHub release.
    - Both the release tag and title should use the format `x.x.x`,
      e.g. `3.2.1`.
    - Include the release notes from NEWS.md as the description.
    - Download the Windows and macOS packages previously generated by GitHub
      Actions to `build-aux/release/` and run
    ```sh
    python3 build-aux/release/generate_sha256_checksums.py
    ```
    - Attach the resulting files to the new release.
    - Once the release is published, verify that GitHub Actions successfully
      uploads it to [PyPI](https://pypi.org/project/nicotine-plus/).

 8. Generate a stable PPA release for Ubuntu / Debian. First, ensure that the
    [repository mirror](https://code.launchpad.net/~nicotine-team/nicotine+/+git/nicotine+)
    on Launchpad is up to date. Once it is, update the contents of the
    [stable build recipe](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-stable),
    replacing the previous commit hash with the one used for the release you
    tagged on GitHub. Then, generate stable builds by pressing
    *Request build(s)*.

 9. Create a new release on [Flathub](https://github.com/flathub/org.nicotine_plus.Nicotine).

 10. Create a new release on the [Snap Store](https://snapcraft.io/nicotine-plus).
