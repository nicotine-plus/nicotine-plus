# Run Nicotine+ from Git.
For those of us who like living on the bleeding edge and want to help testing the latest changes and bug-fixes, you can run Nicotine+ directly from the Git repository.
This is not particularly hard, but it may come with some additional required skills, like installing dependencies and managing changes in the database and the config files.

## Installing dependencies.
First make sure you have all dependencies installed: [DEPENDENCIES.md](doc/DEPENDENCIES.md), and you'll need to install git.

## Run Nicotine+ from a folder.
To run Nicotine+ directly from a folder, run the following:

```console
git clone https://github.com/nicotine-plus/nicotine-plus.git # Skip this if you have already cloned Nicotine+
cd nicotine-plus
./nicotine
```

## Using the latest stable version of Nicotine+.
To get the latest stable version of Nicotine+ with git, run:
```console
git clone https://github.com/nicotine-plus/nicotine-plus.git # Skip this if you have already cloned Nicotine+
cd nicotine-plus
git pull
git checkout $(git describe --tags --abbrev=0)
./nicotine
```
