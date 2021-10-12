# Translations

## How to translate

You can help improving our translations at [Weblate](https://hosted.weblate.org/projects/nicotine-plus/nicotine-plus/). You don't even need an account.

We regularly import the improved translations into the Nicotine+ GitHub repository, especially before a new Nicotine+ release.

## Testing updated translations

Nicotine+ will first try to find your translation files in your project folder, which is particularly useful for testing translations from the git source tree or if your are using the Python virtualenv framework.

To be able to use the updated translations when running Nicotine+ from your project folder, you first need to generate `.mo` files by running:

```console
python3 setup.py build
```

The newly generated files will end up in the `mo/` folder.

If Nicotine+ doesn't find the `.mo` files in your project folder, it will fall back to searching in your system locale path which is OS specific. A GNU/Linux distribution package will put them in the system locale path.

* On GNU/Linux: `/usr/share/locale/$(lang)/LC_MESSAGES`.

* On Windows: `%PYTHONHOME%\share\locale\$(lang)\LC_MESSAGES`.

## Testing a different language

Nicotine+ will try to autodetect your language based on what locale you're using. For testing purposes Nicotine+ can be forced to use another language. You can do it by setting your locale before starting Nicotine+, e.g.:

* English: `LANGUAGE=en_US.UTF-8 python nicotine`
* French: `LANGUAGE=fr_FR.UTF-8 python nicotine`
* ...

## Updating the translation template

When strings change in the Nicotine+ source code, the translation template file `po/nicotine.pot` should also be updated. To update the template, run the following command:

```console
python3 po/update_pot.py
```


## Add yourself to the translators

If you added a lot of translations, you can add yourself to the TRANSLATORS.md list via a pull request(PR).
