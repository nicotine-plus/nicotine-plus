<!--
  SPDX-FileCopyrightText: 2008-2025 Nicotine+ Contributors
  SPDX-License-Identifier: GPL-3.0-or-later
-->

# Nicotine+ Plugins

This folder contains the Nicotine+ core plugins that are available for all
users, as well as example plugins developers may find helpful.


## Installing Plugins

Custom plugins can be installed in two ways: through the GUI (since Nicotine+
3.4.0), or by copying the plugin to the `plugins` folder.

In order to install a plugin through the GUI:

1. Compress your plugin folder containing a PLUGININFO file as a ZIP archive.
2. In Preferences -> Plugins, press `Install…`, and select the ZIP file
   to import and install.
3. Enable the plugin in the list.

In order to install a plugin through the file system:

1. Copy your plugin folder containing a PLUGININFO file into
   `%AppData%\Roaming\nicotine\plugins\` (Windows),
   `~/.local/share/nicotine/plugins/` (other OSes).
2. Close and reopen the Preferences dialog in case it is open.
3. (Re)enable the plugin in Preferences -> Plugins.

The process can be repeated later in order to update a plugin.


## For Developers

### Commands

There are three types of commands available:

- `chatroom`: Can be used in the message entry widget in chat rooms
- `private_chat`: Can be used in the message entry widget in private chats
- `cli`: Can be used while Nicotine+ is running in a terminal

By default, commands are grouped under the same name as your plugin.

Until this section is fully documented, see the [core_commands](https://github.com/nicotine-plus/nicotine-plus/tree/HEAD/pynicotine/plugins/core_commands/)
plugin for examples on how to add commands to your plugins.

### Events and Notifications

There are two ways plugins can react to activity in Nicotine+:

- Events: gives the plugin the ability to alter things. These are time
  critical, plugins should finish their execution as fast as possible.
  Only use events if you really have to, because every ms you linger around
  processing the user will be looking at a frozen Nicotine+.

- Notifications: gives the plugin the ability to respond to things, without
  being able to alter them. The plugin can take as long as it wants outside
  the main thread. When possible, use notifications instead of events.

### Other

For more help, examine [pluginsystem.py](https://github.com/nicotine-plus/nicotine-plus/blob/HEAD/pynicotine/pluginsystem.py)
and the [example plugins](https://github.com/nicotine-plus/nicotine-plus/tree/HEAD/pynicotine/plugins/examplars/).
There is no additional documentation except for existing plugins.
