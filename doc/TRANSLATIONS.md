# Translations

For a list of translators, see [TRANSLATORS.md](../TRANSLATORS.md). If your name is missing, please contact us.

## For Translators

### How to translate

Translations are handled on the [Launchpad translations page](https://translations.launchpad.net/nicotine+).

To get started:

- [Register a Launchpad account](https://login.launchpad.net/+new_account)

- [Specify your preferred languages](https://translations.launchpad.net/+editmylanguages)

- Start suggesting translation changes

Once your translations have been approved, they will be merged into Nicotine+'s GitHub repository, at the very latest before a new Nicotine+ release.

## For Developers and Maintainers

### To update the translation template

As strings change in the Nicotine+ source code, the translation template file should also be updated regularly.

To update the template (.pot) file:

- Enter the `po` folder by running `cd po`

- Run the following command:

```console
intltool-update -p -g nicotine
```

A developer part of the [Nicotine+ Launchpad team](https://launchpad.net/~nicotine-team) should then [upload the updated .pot file](https://translations.launchpad.net/nicotine+/trunk/+translations-upload) to Launchpad, and [approve it](https://translations.launchpad.net/nicotine+/+imports).

### To import translations to GitHub

Translations should be imported to the GitHub repository regularly, at the very latest before a new Nicotine+ release is tagged.

To do this:

- [Export all translations](https://translations.launchpad.net/nicotine+/trunk/+export) in PO format

- Add the updated files to the `po` folder

- Commit the files

Also remember to add new translators to the list of translators, located in TRANSLATORS.md and `pynicotine/gtkgui/ui/about/about.ui`.

## More On Translation

Nicotine+ will try to autodetect your language based on what locale you're using.

For testing purposes Nicotine+ can be forced to use a specific language. You can do it by setting your locale before starting Nicotine+ ex:

* English: `LC_ALL=en_US.UTF-8 python nicotine`
* French: `LC_ALL=fr_FR.UTF-8 python nicotine`
* ...

Nicotine+ will first try to find your translation files in your project folder.
It's particularly useful for testing translations from the git source tree or if your are using Python virtualenv framework.

To use translations when running Nicotine+ from your project folder, you need to generate .mo files by running

```console
python3 setup.py build
```

The files will be located in the `mo` folder.

If Nicotine+ doesn't find the .mo files in your project folder, it will fall back to searching in your system locale path which is OS specific. A GNU/Linux distribution package will put them in the system locale path.

* On GNU/Linux: `/usr/share/locale/$(lang)/LC_MESSAGES`.

* On Windows: `%PYTHONHOME%\share\locale\$(lang)\LC_MESSAGES`.
