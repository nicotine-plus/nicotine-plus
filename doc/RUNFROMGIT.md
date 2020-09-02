# Run Nicotine+ from git
For those of us who like living on the bleeding edge and want to help testing the latest changes and bug-fixes, you can run Nicotine+ directly from the git repository.
This is not particularly hard, but it may come with some additional required skills, like installing dependencies and managing changes in the database and the config files.

## Installing the dependencies
To run Nicotine+ from git, you first have to install all required dependencies. You may also want to install the optional dependencies.
See [DEPENDENCIES.md](DEPENDENCIES.md)

## Clone the repository and run Nicotine+
This is great if you're the only Nicotine+ user on your system and you want to test the latest version.
```
$ git clone https://github.com/Nicotine-Plus/nicotine-plus.git
$ cd nicotine-plus
$ python3 nicotine
```

To use translations, you need to generate .mo files by running `python3 setup.py build`. The files will be located in the `mo` folder.

## Updating your cloned Nicotine+
If you want to update to the latest version of Nicotine+, proceed like this:
```
$ cd nicotine-plus
$ git pull
$ python3 nicotine
```

## Installing Nicotine+ from the git repository
This is useful if you want to share your Nicotine+ installation with other users.
```
$ cd nicotine-plus
$ sudo python3 setup.py install
```

After that, you should be able to run `nicotine` like a normal command.
