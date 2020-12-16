# Run Nicotine+ from git
For those of us who like living on the bleeding edge and want to help testing the latest changes and bug-fixes, you can run Nicotine+ directly from the git repository.
This is not particularly hard, but it may come with some additional required skills, like installing dependencies and managing changes in the database and the config files.

## Clone the repository and run Nicotine+
This is great if you're the only Nicotine+ user on your system and you want to test the latest version. Using a Python virtual environment (venv) is recommended, as this ensures Nicotine+ will run as intended.

```console
git clone https://github.com/Nicotine-Plus/nicotine-plus.git
cd nicotine-plus
python3 -m venv .env
.env/bin/pip install .
.env/bin/nicotine
```

For Windows, follow the instructions in [PACKAGING.md](PACKAGING.md#windows) instead.

## Updating your cloned Nicotine+
If you want to update to the latest version of Nicotine+, proceed like this:

```console
cd nicotine-plus
git pull
.env/bin/pip install .
.env/bin/nicotine
```
