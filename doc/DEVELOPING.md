# Developing

This document contains important information about Nicotine+ design decisions and development procedures for maintainers, developers and code contributors alike.

## Sections

 * [Python Versions](#python-versions)
 * [Dependencies](#dependencies)
 * [Profiling](#profiling)
 * [Continuous Integration Testing](#continuous-integration-testing)
 * [Translations](#translations)
 * [Releases](#releases)

# Python Versions

Nicotine+ aims to support Python 3 versions used by the oldest distributions still actively maintained. Once a Python version is no longer used and supported by any distribution, the minimum supported Python version should be changed in Nicotine+.

Currently, the minimum Python version Nicotine+ supports is 3.5. This version should be dropped once Ubuntu 16.04 reaches EOL in 2021.

# Dependencies

Nicotine+ aims to be as portable as possible, providing access to the Soulseek network for people who can't use the official Soulseek client. Nicotine+ runs on almost any architecture and system available, and has active users on a plethora of different systems. This also means that the introduction of an external software depencency can cause issues for both packagers and users.

Dependencies preinstalled on a majority of systems, as well as modules included in the Python Standard Library, should be used as much as possible. Avoid introducing "convenient" and "new hotness" dependencies, if the standard library already includes the required functionality to some degree. If a new dependency needs to be introduced, think about the following points:

 * Prefer pure-Python dependencies, as these can be used on any system and architecture.

 * Try to find small, maintainable dependencies that can be bundled with the Nicotine+ source code, and give proper attribution. External dependencies can behave surprisingly different on some systems, and be quite outdated on some older systems. Use common sense though; don't bundle security-critical dependencies, rapidly changing APIs etc.

# Profiling

Profiling code changes from time to time is important, to ensure that Nicotine+ performs well and doesn't use unnecessary resources. Our goal is to develop a lightweight client than runs well on older hardware and servers, and these can be quite constrained at times.

Addressing performance in Python can be a challenge at times, and there are no straightforward ways of solving all performance issues. These points generally help:

 * Use better data structures and algorithms for the intended purpose.

 * Use functions in the Python Standard Library when possible, instead of reimplementing algorithms yourself.

 * Look for alterative ways of accomplishing a task, search engines help a lot here. Certain modules in the standard library are written in C, and tend to perform better than pure-Python counterparts.

[py-spy](https://github.com/benfred/py-spy) is an excellent tool for profiling Python applications in real time, and will save you a lot of time.

# Continuous Integration Testing

It is important that all patches pass unit testing. Unfortunately developers make all kinds of changes to their local development environment that can have unintended consequences. This means sometimes tests on the developer's computer pass when they should not, and other times failing when they should not have. 

To properly validate that things are working, continuous integration (CI) is required. This means compiling, performing local in-tree unit tests, installing through the system package manager, and finally testing the actually installed build artifacts to ensure they do what the user expects them to do.

The key thing to remember is that in order to do this properly, this all needs to be done within a realistic end user system that hasn't been unintentionally modified by a developer. This might mean a chroot container with the help of QEMU and KVM to verify that everything is working as expected. The hermetically sealed test environment validates that the developer's expected steps for, as an example in the case of a library, compilation, linking, unit testing, and post installation testing are actually replicable.

There are [different ways](https://wiki.debian.org/qa.debian.org#Other_distributions) of performing CI on different distros. The most common one is via the international [DEP-8](https://dep-team.pages.debian.net/deps/dep8/) standard as used by hundreds of different operating systems.

## Autopkgtest
On Debian based distributions, `autopkgtest` implements the DEP-8 standard. To create and use a build image environment for Ubuntu, follow these steps. First install the autopkgtest(1) tools:

```sh
sudo apt install autopkgtest
```

Next create the test image, substituting `groovy` or `amd64` for other releases or architectures:

```sh
autopkgtest-buildvm-ubuntu-cloud -r groovy -a amd64
```

Generate a Nicotine+ source package in the parent directory of `nicotine_source`:

```sh
cd nicotine_source
sudo apt build-dep nicotine
./debian/rules get-orig-source
debuild -S -sa
```

Test the source package on the host architecture in QEMU with KVM support and 8GB of RAM and four CPUs:

```sh
autopkgtest --shell-fail --apt-upgrade ../nicotine_(...).dsc -- \
      qemu --ram-size=8192 --cpus=4 --show-boot path_to_build_image.img \
      --qemu-options='-enable-kvm'
```

## Creating tests

Tests are defined in the *test/* folder, and should be expanded to cover larger parts of the client when possible.

# Translations

## To update the translation template

As strings change in the Nicotine+ source code, the translation template file should also be updated regularly.

To update the template (.pot) file:

 * Enter the `po` folder by running `cd po`

 * Run the following command:

```console
intltool-update -p -g nicotine
```

A developer part of the [Nicotine+ Launchpad team](https://launchpad.net/~nicotine-team) should then [upload the updated .pot file](https://translations.launchpad.net/nicotine+/trunk/+translations-upload) to Launchpad, and [approve it](https://translations.launchpad.net/nicotine+/+imports).

## To import translations to GitHub

Translations should be imported to the GitHub repository regularly, at the very latest before a new Nicotine+ release is tagged.

To do this:

 * [Export all translations](https://translations.launchpad.net/nicotine+/trunk/+export) in PO format

 * Add the updated files to the `po` folder

 * Commit the files

Also remember to add new translators to the list of translators, located in TRANSLATORS.md and `pynicotine/gtkgui/ui/about/about.ui`.

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

 * Taking too long to release a new Nicotine+ version (e.g. years) will likely end up in Nicotine+ no longer working due to technological advancements, or being dropped from distributions. This already happened when support for Python 2 ended in 2019.

 * We have no way of delivering updates to all users at the same time. Packagers for various distributions need to package and test new Nicotine+ versions before users receive them. It would be preferable to avoid creating too many releases in a very short period of time.

 * Releasing large updates can make it harder to pinpoint eventual issues that have been introduced since the previous release.

## Creating a new Nicotine+ release

The following is a step-by-step guide on what a Nicotine+ maintainer should do when releasing a new version of Nicotine+.

 1. Ensure that Nicotine+ works on at least these four systems: Windows, macOS, the oldest Ubuntu version we still support (16.04), as well as the newest Ubuntu version available.

 2. Ensure that the source distribution (sdist) includes all necessary files to run Nicotine+. A source distribution can be generated by running
```
python3 setup.py sdist
```

 3. Add a new release note entry in NEWS.md. The release notes should contain a user-readable list of noteworthy changes since the last release (not a list of commits), as well as a list of closed bugs on GitHub.

 4. Increase the Nicotine+ version number / add new version entries in the master branch. Nicotine+ uses [Semantic Versioning](https://semver.org/). The following files need to be modified:
    * NEWS.md
    * README.md
    * debian/changelog
    * files/org.nicotine_plus.Nicotine.metainfo.xml
    * packaging/windows/nicotine.nsi
    * pynicotine/utils.py

 5. Ensure that the Windows and macOS packages generated by GitHub Actions still work. They can be found [here](https://github.com/Nicotine-Plus/nicotine-plus/actions).

 6. Create a new GitHub release.
    * Both the release tag and title should use the format "x.x.x", e.g. *2.2.0*. 
    * Include the release notes from NEWS.md as the description.
    * Attach the Windows and macOS packages you previously tested.

 7. Generate a stable PPA release for Ubuntu / Debian. First, ensure that the [repository mirror](https://code.launchpad.net/~nicotine-team/nicotine+/+git/nicotine+) on Launchpad is up to date. Once it is, update the contents of the [stable build recipe](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-stable), replacing the previous commit hash with the one used for the release you tagged on GitHub. Then, generate stable builds by pressing *Request build(s)*.

 8. Create a new release on [PyPI](https://pypi.org/) by running
```
packaging/pip/upload_pypi_release.sh
```

 9. Create a new release on [Flathub](https://github.com/flathub/org.nicotine_plus.Nicotine).
