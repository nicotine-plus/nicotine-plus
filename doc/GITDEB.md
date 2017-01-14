# Follow git based repository for Debian Ubuntu

## To run Nicotine+ from git master:

* Add the following repository to /etc/apt/sources.list:

    `deb [trusted=yes target=Packages] http://buildbot.le-vert.net/pkgs/nicotine-plus/jessie/latest/ ./`

* Update APT metadata and install package

    `apt-get update`
    
    `apt-get install nicotine`

Everytime you upgrade your system now, nicotine will be updated to latest version available on git master branch.
