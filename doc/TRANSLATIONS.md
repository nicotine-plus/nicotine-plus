# Translations

For a list of translators, see [TRANSLATORS.md](../TRANSLATORS.md)

If your name is missing, please contact us.

## For Translators

### How To Translate

##### To create a new language:

1. Create a directory `languages/$(your_lang)/LC_MESSAGES/` for your translation.

2. Copy the `nicotine.pot` to that subdirectory and rename it to `nicotine.po`.

3. Edit this file.

4. **PLEASE** make sure that you are using UNIX style line ending and UTF-8 encoding.

##### To update the language you are working on:

1. To update your translated .po file from the template you have two choices:

    * Go to the directory of the translation and run:

    `msgmerge -U nicotine.po ../../nicotine.pot`

    * Or if using poedit use `Catalog -> Update from POT file` menu.

2. Edit your translation.

3. **PLEASE** make sure that you are using UNIX style line ending and UTF-8 encoding.

### How To Test Translations

When finished editing the .po file you must compile the language file to a .mo file.

You can do this either by:

* Running `msgfmt nicotine.po -o nicotine.mo` from the command line.

* Using poedit `File -> Compile to MO` menu.

When restarting Nicotine+ you should see the fruit of your labor :)

## For Developers

##### To update the .pot file (template):

* Run the `update_pot.py` script from the `languages` directory.

##### To update all languages .po files:

* Run the `merge_all` script from the `languages` directory.

* Then, each `nicotine.po` will need to be updated by translators.

##### To compile all languages .po files:

* Run the `msgfmtall.py` script from the `languages` directory.

## More On Translation

Nicotine+ will try to autodetect your language based on what locale you're using.

For testing purposes Nicotine+ can be forced to use a specific language. You can do it by setting your locale before starting Nicotine+ ex:

    * English: `LC_ALL=en_US.UTF-8 python nicotine`
    * French: `LC_ALL=fr_FR.UTF-8 python nicotine`
    * ...

Nicotine+ will first try to find your translation files in your project directory.
It's particularly useful for testing translations from the git source tree or if your are using python virtualenv framework.

Your translation file should be located in:
`$(your_git_clone_path)/languages/$(lang)/LC_MESSAGES/nicotine.{mo,po}`.

If Nicotine+ don't find the translation files in your project directory it will fall back to searching in your system locale path which is OS specific. A GNU/Linux distribution package will put them in the system locale path.

* On GNU/Linux: `/usr/share/locale/$(lang)/LC_MESSAGES/nicotine.{mo,po}`.

* On Windows: `%PYTHONHOME%\share\locale\$(lang)\LC_MESSAGES`.
