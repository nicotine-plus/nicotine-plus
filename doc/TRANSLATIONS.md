# Translations

## How to Translate

You can help improving our translations at [Hosted Weblate](https://hosted.weblate.org/engage/nicotine-plus). You don't even need an account.

We regularly import the improved translations into the Nicotine+ GitHub repository, especially before a new Nicotine+ release.

## Testing Updated Translations

Nicotine+ will first try to find your translation files in your project folder, which is particularly useful for testing translations from the git source tree or if your are using the Python virtualenv framework.

In order to use the updated translations when running Nicotine+ from your project folder, you need to generate `.mo` files by running:

```console
python3 setup.py build
```

The newly generated files will end up in the `mo/` folder.

If Nicotine+ doesn't find the `.mo` files in your project folder, it will fall back to searching in your system locale path, which is OS specific. A GNU/Linux distribution package will install the files in the system locale path.

## Testing Different Languages

Nicotine+ will try to autodetect your language based on what locale you are using. For testing purposes Nicotine+ can be forced to use another language. You can do this by specifying a locale before starting Nicotine+, e.g.:

* English: `LANGUAGE=en_US.UTF-8 python3 nicotine`
* French: `LANGUAGE=fr_FR.UTF-8 python3 nicotine`
* ...

## Updating Translation Template

The translation template file `po/nicotine.pot` should be updated after modifying strings in the codebase. To update the template, run the following command:

```console
python3 po/update_pot.py
```


## Adding Yourself to Translators

If you want you can add yourself to `TRANSLATORS.md` and the credits list in Help → About: `pynicotine/gtkgui/ui/dialogs/about.ui`. Add yourself to the top of matching section and then create a PR (pull request).
