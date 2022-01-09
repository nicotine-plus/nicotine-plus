# Developing

This document contains important information about Nicotine+ design decisions and development procedures for maintainers, developers and code contributors alike.

## Sections

 * [Language and Toolkit](#language-and-toolkit)
 * [Dependencies](#dependencies)
 * [Profiling](#profiling)
 * [Continuous Integration Testing](#continuous-integration-testing)
 * [Releases](#releases)

# Language and Toolkit

## Python

Nicotine+ is Python application, built on backend code from the PySoulSeek project started in 2001. We only allow Python code in the main client, as this makes it easy to distribute and run Nicotine+ on virtually any system. In turn, we are able to devote more time towards implementing bug fixes and additional functionality.

We aim to support the oldest minor Python 3 version still used by supported releases of distributions and operating systems. The minimum version Nicotine+ currently supports is 3.5.

## GTK

Nicotine+ and its predecessors PySoulSeek and Nicotine were originally developed with GNU/Linux in mind, at a time when the official Soulseek client only supported Windows. The Nicotine project opted to use GTK as the GUI toolkit, as opposed to wxPython previously used by PySoulSeek. This decision was made due to various issues encountered in wxPython at the time, such as large memory overhead and long compile/build times.

We are content with GTK, and have no plans of switching to another toolkit.

# Dependencies

Nicotine+ aims to be as portable as possible, providing access to the Soulseek network for people who cannot run the official Soulseek client. Nicotine+ runs on almost any architecture and system available, and has active users on a plethora of different systems. This also means that the introduction of an external software depencency can cause issues for both packagers and users.

Dependencies preinstalled on most systems, as well as modules included in the Python Standard Library, should be preferred whenever possible. Avoid introducing "convenient" and "new hotness" dependencies, if the standard library already includes the required functionality to some degree. If a new dependency is necessary, think about the following points:

 * Prefer pure-Python dependencies, as these are more likely to work well on less common systems and architectures.

 * Attempt to find small, maintainable dependencies that can be bundled with the Nicotine+ source code (and give proper attribution). External dependencies can behave surprisingly different on some systems, and be quite outdated on older systems. Use common sense though; do not bundle security-critical dependencies, rapidly changing APIs etc.

# Profiling

Profiling code changes from time to time is important, to ensure that Nicotine+ performs well and uses few resources. Our goal is to develop a lightweight client than runs well on older hardware, as well as servers, which can be quite constrained.

Due to Python's interpreted nature, addressing performance issues can be a challenge. There is no straightforward way of solving every performance issue, but these points generally help:

 * Use different data structures and algorithms.

 * Use functionality included in the Python Standard Library when possible, instead of reimplementing the wheel. This is especially important when it comes to algorithms.

 * Look for alterative ways of accomplishing a task. Search engines help a lot here. Certain modules in the standard library are written in C, and can perform better than pure-Python counterparts, especially in hot code paths.

[py-spy](https://github.com/benfred/py-spy) is an excellent tool for profiling Python applications in real time, and will save a lot of time in the long run.

# Continuous Integration Testing

It is important that all patches pass unit testing. Unfortunately developers make all kinds of changes to their local development environment that can have unintended consequences. This means sometimes tests on the developer's computer pass when they should not, and other times failing when they should not have.

To properly validate that things are working, continuous integration (CI) is required. This means compiling, performing local in-tree unit tests, installing through the system package manager, and finally testing the actually installed build artifacts to ensure they do what the user expects them to do.

The key thing to remember is that in order to do this properly, this all needs to be done within a realistic end user system that has not been unintentionally modified by a developer. This might mean a chroot container with the help of QEMU and KVM to verify that everything is working as expected. The hermetically sealed test environment validates that the developer's expected steps for, as an example in the case of a library, compilation, linking, unit testing, and post installation testing are actually replicable.

There are [different ways](https://wiki.debian.org/qa.debian.org#Other_distributions) of performing CI on different distros. The most common one is via the international [DEP-8](https://dep-team.pages.debian.net/deps/dep8/) standard as used by hundreds of different operating systems.

## Autopkgtest
On Debian based distributions, `autopkgtest` implements the DEP-8 standard. To create and use a build image environment for Ubuntu, follow these steps. First install the autopkgtest(1) tools:

```sh
sudo apt install autopkgtest
```

Next create the test image, substituting `hirsute` or `amd64` for other releases or architectures:

```sh
autopkgtest-buildvm-ubuntu-cloud -r hirsute -a amd64
```

Test your changes on the host architecture in QEMU with KVM support and 8GB of RAM and four CPUs:

```sh
autopkgtest --shell-fail --apt-upgrade . -- \
      qemu --ram-size=8192 --cpus=4 --show-boot path_to_build_image.img \
      --qemu-options='-enable-kvm'
```

## Creating tests

Tests are defined in the *test/* folder, and should be expanded to cover larger parts of the client when possible.

# Releases

Nicotine+ tries to follow [Semantic Versioning](https://semver.org/) when possible. As cited in the specification:

> Given a version number MAJOR.MINOR.PATCH, increment the:
>
>   MAJOR version when you make incompatible API changes,
>   MINOR version when you add functionality in a backwards compatible manner, and
>   PATCH version when you make backwards compatible bug fixes.
>
> Additional labels for pre-release and build metadata are available as extensions to the MAJOR.MINOR.PATCH format.

Release dates are not set in stone, as Nicotine+ development is done by volunteers in their spare time. However, keep the following points in mind:

 * Taking too long to release a new Nicotine+ version (e.g. years) will likely result in Nicotine+ no longer functioning due to technological advancements, or being removed from distributions. This previously occurred when support for Python 2 ended in 2020.

 * We have no means of delivering updates to all users at the same time. Packagers for numerous distributions have to package and test new Nicotine+ releases before they can be delivered to users.

 * Releasing large updates can make it more difficult to pinpoint eventual issues that were introduced since the previous release.

## Creating a new Nicotine+ release

The following is a step-by-step guide detailing what a Nicotine+ maintainer should do when releasing a new version of Nicotine+.

 1. Ensure that Nicotine+ works on at least these four systems: Windows, macOS, the oldest Ubuntu version we still support (18.04), as well as the newest Ubuntu release available.

 2. Update the translation template by running
```
python3 po/update_pot.py
```

 3. Ensure that the source distribution (sdist) includes all necessary files to run Nicotine+. A source distribution can be generated by running
```
python3 setup.py sdist
```

 4. Add a new release note entry to NEWS.md. Release notes should contain a user-readable list of noteworthy changes since the last release (not a list of commits), as well as a list of closed issues on GitHub.

 5. Increase the Nicotine+ version number / add new version entries in the master branch. Nicotine+ uses [Semantic Versioning](https://semver.org/). The following files need to be modified:
    * NEWS.md
    * README.md
    * data/org.nicotine_plus.Nicotine.metainfo.xml
    * debian/changelog
    * pynicotine/config.py

 6. Ensure that the Windows and macOS packages generated by GitHub Actions still work. They can be found [here](https://github.com/nicotine-plus/nicotine-plus/actions).

 7. Create a new GitHub release.
    * Both the release tag and title should use the format "x.x.x", e.g. *2.2.0*.
    * Include the release notes from NEWS.md as the description.
    * Download the Windows and macOS packages previously generated by GitHub Actions to `packaging/release/`, and run
    ```
    python3 packaging/release/generate_sha256_checksums.py
    ```

    * Attach the resulting files to the new release.

 8. Generate a stable PPA release for Ubuntu / Debian. First, ensure that the [repository mirror](https://code.launchpad.net/~nicotine-team/nicotine+/+git/nicotine+) on Launchpad is up to date. Once it is, update the contents of the [stable build recipe](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-stable), replacing the previous commit hash with the one used for the release you tagged on GitHub. Then, generate stable builds by pressing *Request build(s)*.

 9. Create a new release on [PyPI](https://pypi.org/) by running
```
python3 packaging/pypi/upload_pypi_release.py
```

 10. Create a new release on [Flathub](https://github.com/flathub/org.nicotine_plus.Nicotine).
