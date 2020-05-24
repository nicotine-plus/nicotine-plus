# Continuous Integration Testing

It is important that all patches pass unit testing. Unfortunately developers make all kinds of changes to their local development environment that can have unintended consequences. This means sometimes tests on the developer's computer pass when they should not, and other times failing when they should not have. 

To properly validate that things are working, continuous integration (CI) is required. This means compiling, performing local in-tree unit tests, installing through the system package manager, and finally testing the actually installed build artifacts to ensure they do what the user expects them to do.

The key thing to remember is that in order to do this properly, this all needs to be done within a realistic end user system that hasn't been unintentionally modified by a developer. This might mean a chroot container with the help of QEMU and KVM to verify that everything is working as expected. The hermetically sealed test environment validates that the developer's expected steps for compilation, linking, unit testing, and post installation testing are actually replicable.

There are [different ways](https://wiki.debian.org/qa.debian.org#Other_distributions) of performing CI on different distros. The most common one is via the international [DEP-8](https://dep-team.pages.debian.net/deps/dep8/) standard as used by hundreds of different operating systems.

## Autopkgtest
On Debian based distributions, `autopkgtest` implements the DEP-8 standard. To create and use a build image environment for Ubuntu, follow these steps. First install the autopkgtest(1) tools:
```
$ sudo apt install autopkgtest
```

Next create the test image, substituting `focal` or `amd64` for other releases or architectures:
```
$ autopkgtest-buildvm-ubuntu-cloud -r focal -a amd64
```

Generate a Nicotine+ source package in the parent directory of `nicotine_source`:
```
$ cd nicotine_source
$ sudo apt build-dep nicotine
$ ./debian/rules get-orig-source
$ debuild -S -sa
```

Test the source package on the host architecture in QEMU with KVM support and 8GB of RAM and four CPUs:
```
$ autopkgtest --shell-fail --apt-upgrade ../nicotine_(...).dsc -- \
      qemu --ram-size=8192 --cpus=4 --show-boot path_to_build_image.img \
      --qemu-options='-enable-kvm'
```