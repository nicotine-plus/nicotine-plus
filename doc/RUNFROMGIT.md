# Run Nicotine+ from Git
For those of us who like living on the bleeding edge and want to help testing the latest changes and bug-fixes, you can run Nicotine+ directly from the Git repository.
This is not particularly hard, but it may come with some additional required skills, like installing dependencies and managing changes in the database and the config files.

## Run Nicotine+ from a folder
To run Nicotine+ directly from a folder, run the following:

```console
git clone https://github.com/nicotine-plus/nicotine-plus.git
cd nicotine-plus
./nicotine
```

To update to newer versions of Nicotine+, run the following:

```console
cd nicotine-plus
git pull
```

## Install Nicotine+ for the current user
To install Nicotine+ locally (no root required), run the following:

```console
pip install git+https://github.com/nicotine-plus/nicotine-plus.git
```

Nicotine+ will now be available in your list of programs.

To update to newer versions of Nicotine+, run the same command as previously:

```console
pip install git+https://github.com/nicotine-plus/nicotine-plus.git
```

To uninstall Nicotine+, run:
```console
pip uninstall nicotine-plus
```

## Windows
For Windows, follow the instructions in [PACKAGING.md](PACKAGING.md#windows) instead
