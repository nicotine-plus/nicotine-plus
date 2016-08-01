# Nicotine+ TRANSLATIONS

For a list of translators see [TRANSLATORS](TRANSLATORS.md)

# HowTo translate

##### To update the .pot file (template):
* Run the `languages/tr_gen.py` script from the languages/ directory.

##### To create a new language:
* Create a subdirectory under `languages/` for your translation.
* Copy the `nicotine.pot` to that subdirectory and rename it to `nicotine.po`.
* Edit this file with poedit or the editor of your choice.

##### To update all language .po files:
* Run the `languages/mergeall` script from the  `languages/` directory.
* Run the `languages/msgfmtall.py` script from the `languages/` directory.
* Then, each `nicotine.po` will need to be updated with the new translations.

##### To update just the language .po file you are working on:
* Change to the directory of the translation and run `msgmerge -U nicotine.po ../nicotine.pot`
* When finished editing the .po, in the language's subdirectory, do the following command: `msgfmt nicotine.po -o nicotine.mo`
* After nicotine has been installed, the new .mo files will be in `/usr/share/locale/$LANGUAGE/LC_MESSAGES/`
* For testing, you can copy them there, yourself (if you have permissions)

# USERS

For Nicotine to know you want a certain translation, your locale needs to be set to that language.

If your operating system doesn't have it set already, starting with these commands will force an operating system to load.

##### ENGLISH
LC_ALL=en_US.UTF-8 nicotine

##### DANISH
LC_ALL=dk_DK.UTF-8 nicotine

##### DUTCH
LC_ALL=nl_NL.UTF-8 nicotine

##### Euskara (Basque)
LC_ALL=eu.UTF-8 nicotine

##### FRENCH
LC_ALL=fr_FR.UTF-8 nicotine

##### GERMAN
LC_ALL=de_DE.UTF-8 nicotine

##### HUNGARIAN
LC_ALL=hu_HU.UTF-8 nicotine

##### ITALIAN
LC_ALL=it_IT.UTF-8 nicotine

##### Lithuanian
LC_ALL=lt_LT.UTF-8 nicotine

##### POLISH
LC_ALL=pl_PL.UTF-8 nicotine

##### Portuguese Brazilian
LC_ALL=pt_BR.UTF-8 nicotine

##### SLOVAK:
LC_ALL=sk_SK.UTF-8 nicotine

##### SPANISH
LC_ALL=es_ES.UTF-8 nicotine

##### SWEDISH
LC_ALL=sv_SE.UTF-8 nicotine
