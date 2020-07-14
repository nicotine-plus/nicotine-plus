# Run Nicotine+ from git

## Installing the dependencies
To run nicotine from git you first have to install all required dependencies. You may also want to install the optional dependencies.
See [DEPENDENCIES.md](doc/DEPENDENCIES.md)

## Clone the repository and run nicotine
This is great if you're the only nicotine user on your system and you want to test the latest version.
```
$ git clone https://github.com/Nicotine-Plus/nicotine-plus.git
$ cd nicotine-plus
$ python3 nicotine
```

## Updating your cloned nicotine-plus
If you want to update to the latest version of nicotine-plus proceed like this:
```
$ cd nicotine-plus
$ git pull
$ python3 nicotine
```

## Installing nicotine from the git repository
This is useful if you want to share your nicotine-plus installation with other users.
```
$ cd nicotine-plus
$ sudo python3 setup.py install
```

And after that you should be able to run `nicotine`.
