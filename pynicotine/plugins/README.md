# Nicotine+ Plugins

This folder contains the Nicotine+ core plugins that are available for all users.

In order to load your own custom plugins, you need to:

1. Copy your plugin into ~/.local/share/nicotine/plugins (create this directory if it doesn't exist yet).
2. Enable it in Preferences -> Plugins (there is no need to restart Nicotine+).

## FOR DEVELOPERS

There are two kinds of actions you can hook into:

- Events: gives the plugin the ability to alter things. These are time critical, plugins should finish their execution as fast as possible. Only use Events if you really have to, because every ms you linger around processing the user will be looking at a frozen Nicotine+.

- Notifications: gives the plugin the ability to respond to things, without being able to alter them. The plugin can take as long as it wants. This is the preferred action to hook into.

For more help, examine [pluginsystem.py](../pluginsystem.py) and the [example plugins](./examplars/). There is no documentation except for existing plugins.
