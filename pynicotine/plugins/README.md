# README Concerning plugins for N+

## FOR DEVELOPERS

In order to load your own plugins you need to copy them to
~/.local/share/nicotine/plugins, creating this directory if it doesn't exist
yet. Plugins will be loaded upon startup, and can be reloaded with /reload.
This reload command does not always completely reload the plugins due to the
way Python works, in some cases a restart of N+ is needed to get new versions
working.

There are two kinds of actions you can hook into:

- Events: gives the plugin the ability to alter things. These are time
  critical, plugins should finish their execution as fast as possible. Let me
  repeat that: every ms you linger around processing the user will be looking
  at a frozen N+. 
- Notifications: gives the plugin the ability to respond to things, without
  being able to alter them. The plugin can take as long as it wants. This is
  the preferred action to hook into, only use Events if you really have to.

For more help examine the pluginsystem.py and the example plugins. There is no
documentation except for the example plugins.
