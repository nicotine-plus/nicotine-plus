# Translations

## How to Translate

You can help improving our translations at [Hosted Weblate](https://hosted.weblate.org/engage/nicotine-plus). You don't even need an account.

We regularly import the improved translations into the Nicotine+ GitHub repository, especially before a new Nicotine+ release.

Look around in the Weblate interface, there are quite a few very practical options.


### Automatic Translations

This will translate all strings that haven't been edited yet.

In the menu "Tools → Automatic translations", select "Automatic translation mode → Add as needing edit", "Search filter → Not translated strings" and "Machine translations → Google Translate"

After letting it run for a while, say 20 minutes, it should have finished and added a halfway decent translation for your language.

Now you can continue with translating by pressing a fitting item in the "String Status".


### Automatic Suggestions

Whilst translating in normal mode, you can select "Automatic Suggestions," this is great to see the proposed translations from various translation services. Google Translate works very well, but you might find other translations that are more to the point.


### Zen Mode

In Zen mode you can check and improve all items you have selected.


### Search and Replace

Using consistent terms for the same things makes the translation easier to understand. You may also find that some words are mistranslated by the engines, for example "shares" is often translated as "shares from the stockmarket" and not as in "sharing files and directories".

You can use the "Search and Replace" tool to help you with that.

### Underscores(_) in the strings
In case you are wondering what to do with the underscores, the Alt-shortcuts (called mnemonics in GTK) provide quick access to a visible UI element (button, menu item etc), so it doesn't really matter what they are. So you can translate "_Quit" to "_Cerrar". If in the same menu the "C" is already in use, simply put the underscore in front of another letter. 

## Testing Updated Translations

After translating, you can test your translation by running Nicotine+ with the new translations.

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


## Adding Yourself to Translators

If you want you can add yourself to [TRANSLATORS.md](https://github.com/nicotine-plus/nicotine-plus/blob/master/TRANSLATORS.md) and the credits list in Help → About: [pynicotine/gtkgui/ui/dialogs/about.ui](https://github.com/nicotine-plus/nicotine-plus/blob/master/pynicotine/gtkgui/ui/dialogs/about.ui). Add yourself to the top of matching section and then create a PR (pull request).


## Updating Translation Template

This part is relevant for developers.

The translation template file `po/nicotine.pot` should be updated after modifying strings in the codebase. To update the template, run the following command:

```console
python3 po/update_pot.py
```
