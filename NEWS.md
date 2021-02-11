News
====

As per GCS § 6.7, this file contains a list of user-visible, noteworthy changes. Note that this is not the same as a changelog.

Version 3.0.0 (February 12, 2021)
-----------------------------

Changes

 * Introduced a new design utilizing header bars (to use the old design, uncheck Menu -> View -> Use Header Bar)
 * Improved UI responsiveness when scanning shares
 * Improved UI performance when multiple tabs are open
 * Added transfer statitics dialog
 * Added help window for keyboard shortcuts
 * Added an option to set a global font
 * Added support for text completion when typing in the search entry
 * Added a "Browse Folder" option for search results
 * Search results can now be filtered by file type
 * Added an option to clear search and filter history
 * Columns can now be reordered by dragging them to the desired location
 * Context menus for tabs now include an option to close all tabs
 * Added context menu items for viewing and deleting logs (chatrooms, private chat, log pane)
 * Added a keyboard shortcut to close tabs (Ctrl+W / Alt+F4)
 * Context menus can now be opened by long-pressing on a touch screen
 * Context menus can now be opened with the keyboard (Menu Key / Shift+F10)
 * The number of selected files is now visible in context menus
 * Added an option to copy the file path of a selected file using Ctrl+C
 * Added file properties dialog for user browse
 * Improved the default color scheme
 * Several other minor improvements

Corrections

 * Fixed an issue where upload speed limits were not applied on startup
 * Fixed an issue where UPnP portforwarding did not succeed with certain routers
 * Fixed an issue where enabling the geographical paranoia option would prevent search results from being delivered to others
 * Fixed issues where certain uploads would be stuck in a "Cancelled" state
 * Fixed a Windows-specific issue where the config file did not always save
 * Fixed an macOS-specific issue where opening a folder did not work
 * Fixed an issue where custom commands registered in plugins did not work
 * Several other minor corrections

Issues closed on GitHub

 * Nicotine will not login to server ([#904](https://github.com/Nicotine-Plus/nicotine-plus/issues/904))
 * File not shared ! ([#905](https://github.com/Nicotine-Plus/nicotine-plus/issues/905))
 * Backup of the slide position in the user browse tab ([#908](https://github.com/Nicotine-Plus/nicotine-plus/issues/908))
 * Save share list to disk => user tab ([#909](https://github.com/Nicotine-Plus/nicotine-plus/issues/909))
 * Double-clicking on shares ([#917](https://github.com/Nicotine-Plus/nicotine-plus/issues/917))
 * Fix viewing of shared files ([#919](https://github.com/Nicotine-Plus/nicotine-plus/issues/919))
 * WinError 3, "the system cannot find the path specified" ([#920](https://github.com/Nicotine-Plus/nicotine-plus/issues/920))
 * Replace usage of GtkComboBox with GtkComboBoxText ([#921](https://github.com/Nicotine-Plus/nicotine-plus/issues/921))
 * nicotine-plus.org certificate expired ([#922](https://github.com/Nicotine-Plus/nicotine-plus/issues/922))
 * Cyrillic characters don't display correctly in chat rooms (Unicode issue?) ([#925](https://github.com/Nicotine-Plus/nicotine-plus/issues/925))
 * Log windows scroll back to begin after any new entry. ([#926](https://github.com/Nicotine-Plus/nicotine-plus/issues/926))
 * Config resetting when quitting and opening again ([#934](https://github.com/Nicotine-Plus/nicotine-plus/issues/934))
 * nicotine.po ([#936](https://github.com/Nicotine-Plus/nicotine-plus/issues/936))
 * Bug: Browsing your own shares with "Share only to buddies" enabled isn't possible via User browse ([#940](https://github.com/Nicotine-Plus/nicotine-plus/issues/940))
 * Bug: Displayed shared files count in Chat rooms / User info inconsistent ([#941](https://github.com/Nicotine-Plus/nicotine-plus/issues/941))
 * Feature Request: Clear filters button ([#944](https://github.com/Nicotine-Plus/nicotine-plus/issues/944))
 * Feature Request: Allow regular expressions in Country field of Search Filters ([#946](https://github.com/Nicotine-Plus/nicotine-plus/issues/946))
 * Config Bug: WinError 32 + WinError 2: Can't rename config file, error & The system cannot find the file specified ([#949](https://github.com/Nicotine-Plus/nicotine-plus/issues/949))
 * Feature Request: Clear Search Result Filter History ([#950](https://github.com/Nicotine-Plus/nicotine-plus/issues/950))
 * Feature Request: A method to quit via Tray Icon ([#951](https://github.com/Nicotine-Plus/nicotine-plus/issues/951))
 * Windows Bug: Can't bring Nicotine+ to the foreground if one of its popup windows are open ([#953](https://github.com/Nicotine-Plus/nicotine-plus/issues/953))
 * Windows Bug: Preferences popup window is slow to open on occasion ([#954](https://github.com/Nicotine-Plus/nicotine-plus/issues/954))
 * Now Playing ([#957](https://github.com/Nicotine-Plus/nicotine-plus/issues/957))
 * Filtering by "10m" gives files >=10MiB, but filtering "10MiB" gives files >=9.54MiB ([#961](https://github.com/Nicotine-Plus/nicotine-plus/issues/961))
 * Setting Plugin /commands ([#962](https://github.com/Nicotine-Plus/nicotine-plus/issues/962))
 * Feature Request: Search Wishlist: Change "Select All" Button to "Clear All" ([#963](https://github.com/Nicotine-Plus/nicotine-plus/issues/963))
 * Feature Request: Indication that a search tab was opened automatically by the wishlist ([#964](https://github.com/Nicotine-Plus/nicotine-plus/issues/964))
 * Feature Request: Option to choose the search result filter's tab bar position ([#965](https://github.com/Nicotine-Plus/nicotine-plus/issues/965))
 * Bug: Clearing all active filters requires double-Enter for next filter attempt ([#966](https://github.com/Nicotine-Plus/nicotine-plus/issues/966))
 * MacOS 11.1 Open folder fails ([#970](https://github.com/Nicotine-Plus/nicotine-plus/issues/970))
 * MacOS 11.1, open folder opens the wrong directory ([#971](https://github.com/Nicotine-Plus/nicotine-plus/issues/971))
 * MacOS 11.1, wrong flag in buddy list ([#972](https://github.com/Nicotine-Plus/nicotine-plus/issues/972))
 * New bundled UPnP is not working ([#973](https://github.com/Nicotine-Plus/nicotine-plus/issues/973))
 * Replace GtkFileChooserButton with a custom button widget ([#975](https://github.com/Nicotine-Plus/nicotine-plus/issues/975))
 * Windows: Toggle show / minimize app on taskbar icon click ([#976](https://github.com/Nicotine-Plus/nicotine-plus/issues/976))
 * Feature Request: Enable tooltips for long strings that are cut off by another column ([#977](https://github.com/Nicotine-Plus/nicotine-plus/issues/977))
 * What is causing the log "Filtered out inexact or incorrect search result ... from user X"? ([#979](https://github.com/Nicotine-Plus/nicotine-plus/issues/979))
 * Bug: Private chat tabs closed/discarded without manually doing so ([#983](https://github.com/Nicotine-Plus/nicotine-plus/issues/983))
 * Bug: Unable to reliably close search tabs via middle mouse button click ([#984](https://github.com/Nicotine-Plus/nicotine-plus/issues/984))
 * Feature Request: Log Viewer / Context menu items to browse logs in system text editor ([#986](https://github.com/Nicotine-Plus/nicotine-plus/issues/986))
 * Failure to report buddy shares ([#988](https://github.com/Nicotine-Plus/nicotine-plus/issues/988))

Version 2.2.2 (December 15, 2020)
-----------------------------

Changes

 * Fixed an issue where the list of queued downloads would not be restored on startup

Version 2.2.1 (December 14, 2020)
-----------------------------

Changes

 * Fixed an issue where the file scanner wouldn't scan a folder completely if a hidden subfolder was detected
 * Fixed an issue where invalid audio metadata in shared files could cause stability issues while running Nicotine+
 * Fixed a crash when trying to start Nicotine+ on a non-English Windows system
 * Fixed an issue where a "File not shared" status was sent when attempting to upload certain files
 * Geo block feature is functional again
 * Translations for the menu bar now show up in the UI again

Issues closed on GitHub

 * No icons in FreeBSD ([#889](https://github.com/Nicotine-Plus/nicotine-plus/issues/889))
 * GeoBlock Not Blocking ([#891](https://github.com/Nicotine-Plus/nicotine-plus/issues/891))
 * Nicotine v2.2.0 immediately crashes on startup on Windows 10 v19042.630 ([#893](https://github.com/Nicotine-Plus/nicotine-plus/issues/893))

Version 2.2.0 (December 4, 2020)
-----------------------------

Changes

 * Modernized the default icon theme and several parts of the UI
 * Searching for file names containing special characters returns more search results than previously
 * Reduced the number of connectivity issues when transferring files from and to other users
 * Downloading folders recursively works properly again
 * Updated keyboard shortcuts, since the old ones conflicted with accelerator keys
 * Tray icons are properly detected in more cases
 * User browse and user info tabs now open immediately when requesting info for users
 * Show info message if user shares can't be loaded
 * Minor performance improvements when uploading a lot of files
 * Slightly improved startup times
 * Improved UI responsiveness when browsing your own shares
 * Added option to minimize Nicotine+ to tray on startup
 * Added "Now Playing Search" plugin for searching files based on data from songs playing in your media player
 * Added "Now Playing Sender" plugin for automatically sending names of songs playing to select chat rooms 
 * Builtin plugins load properly on Windows again
 * Modified config backup behavior to not back up the config if "Cancel" is pressed in the file chooser
 * Shares lists saved in older versions of Nicotine+ can now be loaded again
 * Peer-to-peer (direct) private messaging works properly again
 * Fixed a crash when checking for stuck downloads (regression in Nicotine+ 2.1.2)
 * General usability improvements to macOS builds
 * Removed option to stop responding to search requests for certain time periods
 * Removed dbus-python, libnotify, miniupnpc, pytaglib and xdg-utils dependencies, as functionality is now handled by Nicotine+
 * Multiple under-the-hood code improvements and code style changes, as well as smaller bug fixes

Issues closed on GitHub

 * Brew OSX Install ([#58](https://github.com/Nicotine-Plus/nicotine-plus/issues/58))
 * a separate program for database scanning ([#443](https://github.com/Nicotine-Plus/nicotine-plus/issues/443))
 * Failed to map the external WAN port: Invalid Args ([#597](https://github.com/Nicotine-Plus/nicotine-plus/issues/597))
 * After requesting user info put that user's info tab on top. ([#651](https://github.com/Nicotine-Plus/nicotine-plus/issues/651))
 * Feature request: share and/or cache message connections to remote clients ([#663](https://github.com/Nicotine-Plus/nicotine-plus/issues/663))
 * Search Now playing ([#664](https://github.com/Nicotine-Plus/nicotine-plus/issues/664))
 * Compile pytaglib for Python 2 or 3? - Error Trying To Run 2.1.1 ([#726](https://github.com/Nicotine-Plus/nicotine-plus/issues/726))
 * Follow X Session Management Protocol ([#729](https://github.com/Nicotine-Plus/nicotine-plus/issues/729))
 * sometimes, nicotine eats all memory ([#750](https://github.com/Nicotine-Plus/nicotine-plus/issues/750))
 * provided extentions doesn't load ([#761](https://github.com/Nicotine-Plus/nicotine-plus/issues/761))
 * Enabled plugins are no more activated at startup ([#762](https://github.com/Nicotine-Plus/nicotine-plus/issues/762))
 * Plugin properties aren't editable ([#763](https://github.com/Nicotine-Plus/nicotine-plus/issues/763))
 * some users aren't browsable ([#766](https://github.com/Nicotine-Plus/nicotine-plus/issues/766))
 * tray icon problem ([#767](https://github.com/Nicotine-Plus/nicotine-plus/issues/767))
 * Connection issue ([#768](https://github.com/Nicotine-Plus/nicotine-plus/issues/768))
 * Uploads Cancelled ([#784](https://github.com/Nicotine-Plus/nicotine-plus/issues/784))
 * Download recursive ([#790](https://github.com/Nicotine-Plus/nicotine-plus/issues/790))
 * not sure if this is a bug or something else ([#791](https://github.com/Nicotine-Plus/nicotine-plus/issues/791))
 * Can't scan any songs ([#798](https://github.com/Nicotine-Plus/nicotine-plus/issues/798))
 * Search problem? ([#822](https://github.com/Nicotine-Plus/nicotine-plus/issues/822))
 * windows unstable build can't rebuild shares ([#829](https://github.com/Nicotine-Plus/nicotine-plus/issues/829))
 * Nicotine 2.1.2 fails to launch in FreeBSD due to missing pytaglib ([#843](https://github.com/Nicotine-Plus/nicotine-plus/issues/843))
 * Download Recursive ([#844](https://github.com/Nicotine-Plus/nicotine-plus/issues/844))
 * Option to start application hidden when tray icon enabled ([#864](https://github.com/Nicotine-Plus/nicotine-plus/issues/864))
 * Missing application icon from window list ([#879](https://github.com/Nicotine-Plus/nicotine-plus/issues/879))
 * Python 3.8 Crashes ([#882](https://github.com/Nicotine-Plus/nicotine-plus/issues/882))

Version 2.1.2 (12 October 2020)
-----------------------------

Changes

 * Contents of a shared folder are now properly sent to other users
 * Improved performance and memory usage when scanning shares
 * Large memory usage reductions when many rooms and private chats are open
 * Sharing downloaded files now works properly
 * Private messages sent while the user was offline are shown separately from new messages
 * Added transfer speeds and shortcuts to downloads/uploads in the tray
 * Multiple under-the-hood code improvements and code style changes

Issues closed on GitHub

 * Improve code style/consistency ([#377](https://github.com/Nicotine-Plus/nicotine-plus/issues/377))
 * debian packages ([#530](https://github.com/Nicotine-Plus/nicotine-plus/issues/530))
 * running from source - missing reqs ([#531](https://github.com/Nicotine-Plus/nicotine-plus/issues/531))
 * SIGABRT when scanning corrupt/empty FLAC file ([#730](https://github.com/Nicotine-Plus/nicotine-plus/issues/730))

Version 2.1.1 (26 September 2020)
-----------------------------

Changes

 * Improved speed limit calculations for file transfers
 * Added option to enable dark mode theme
 * Added option to copy a previous search term when right-clicking a search tab
 * Replaced text search dialog with search bar
 * If mutiple file transfers are in progress, the UI now updates properly
 * Auto-joining the public chat room now works properly
 * Copying text with Ctrl-C now works properly again
 * Added option to log debug messages to file
 * Several minor bug fixes

Issues closed on GitHub

 * Please put whole search string after/before "results: x/y" ([#383](https://github.com/Nicotine-Plus/nicotine-plus/issues/383))
 * replace log search function with search/filter thingybob, send logs to logfile. ([#387](https://github.com/Nicotine-Plus/nicotine-plus/issues/387))
 * Transfer connection initiation following an unallowed (queued) transfer response ([#653](https://github.com/Nicotine-Plus/nicotine-plus/issues/653))
 * Minor issues to fix for 2.1.1 ([#659](https://github.com/Nicotine-Plus/nicotine-plus/issues/659))
 * Windows 10 dark theme support ([#661](https://github.com/Nicotine-Plus/nicotine-plus/issues/661))
 * Wrap filters into one line ([#669](https://github.com/Nicotine-Plus/nicotine-plus/issues/669))
 * Public room cannot be auto-joined ([#672](https://github.com/Nicotine-Plus/nicotine-plus/issues/672))

Version 2.1.0 (12 September 2020)
-----------------------------

Changes

 * Major performance improvements when rescanning shared files and sending user browse responses to others
 * Several performance and stability improvements related to connections and file transfers
 * Several Windows fixes regarding memory leaks, unresponsiveness and issues when starting Nicotine+
 * Reduced memory usage while rescanning shared files
 * Consistent startup times no matter the number of shared files.
   On large file shares, this cuts down startup times from tens of seconds to 1-2 seconds, depending on your hardware.
 * Numbers are now appended to the file names of duplicate downloads
 * Your personal upload speed is no longer reported as 0 B/s
 * In folder/user grouping mode, selecting a user or folder now allows you to retry/cancel all downloads under them
 * Added quick-access checkbox for enabling/disabling private room invitations
 * Replaced ticker banner with room wall, which displays individual messages from room users
 * "Send to player"-feature is functional again
 * Queue position of downloads is now asked automatically
 * The wishlist feature now works as intended, sending one search at a time instead of three. Wishlist items can also be renamed.
 * Improved notification settings
 * Improved readability in search results and transfer views
 * Several other UI fixes and improvements
 * A rare issue where all tabs were hidden on startup has been fixed
 * Using non-Latin characters in the Windows client now works properly again
 * The Windows installer size was reduced from ~40 MB to ~25 MB
 * The Windows installer now removes old Nicotine+ system files before updating installations
 * Removed support for detachable tabs due to low usage and bugs
 * Replaced Mutagen with pytaglib for audio file metadata scanning due to performance issues

Issues closed on GitHub

 * Brew OSX Install ([#58](https://github.com/Nicotine-Plus/nicotine-plus/issues/58))
 * Flatpak build ([#102](https://github.com/Nicotine-Plus/nicotine-plus/issues/102))
 * Fix remaining GTK warnings ([#290](https://github.com/Nicotine-Plus/nicotine-plus/issues/290))
 * right click user implicitly selects all files downloading from that user. ([#308](https://github.com/Nicotine-Plus/nicotine-plus/issues/308))
 * two cds saved in the same folder ([#313](https://github.com/Nicotine-Plus/nicotine-plus/issues/313))
 * Fatal error detected" when trying to run Nicotine on Windows 10 ([#413](https://github.com/Nicotine-Plus/nicotine-plus/issues/413))
 * RAM usage ([#416](https://github.com/Nicotine-Plus/nicotine-plus/issues/416))
 * if no close button on tabs it's not possible to close User search file notebook ([#428](https://github.com/Nicotine-Plus/nicotine-plus/issues/428))
 * Question; what diff between scanning and rebuilding share ? ([#430](https://github.com/Nicotine-Plus/nicotine-plus/issues/430))
 * notify sharelist is empty ([#434](https://github.com/Nicotine-Plus/nicotine-plus/issues/434))
 * double click is received on selection despite being performed on blank space ([#437](https://github.com/Nicotine-Plus/nicotine-plus/issues/437))
 * align columns text to left, right or center ([#438](https://github.com/Nicotine-Plus/nicotine-plus/issues/438))
 * url catching stop to work since update of 2 days ago ([#457](https://github.com/Nicotine-Plus/nicotine-plus/issues/457))
 * Font worrie > ([#458](https://github.com/Nicotine-Plus/nicotine-plus/issues/458))
 * progress bar stuck at 100% ([#454](https://github.com/Nicotine-Plus/nicotine-plus/issues/454))
 * Question : how to auto-join a room ? ([#464](https://github.com/Nicotine-Plus/nicotine-plus/issues/464))
 * Every you can right click a user, but not in the chat, there it's left click. ([#466](https://github.com/Nicotine-Plus/nicotine-plus/issues/466))
 * Tree view expand/collapse is not respected on new transfer ([#473](https://github.com/Nicotine-Plus/nicotine-plus/issues/473))
 * application content is not diplayed properly with tabs set to side ([#474](https://github.com/Nicotine-Plus/nicotine-plus/issues/474))
 * Completed downloads are re-Queued ([#477](https://github.com/Nicotine-Plus/nicotine-plus/issues/477))
 * search tab "close thistab" missing if 3 tabs are open ([#481](https://github.com/Nicotine-Plus/nicotine-plus/issues/481))
 * close button in About Nicotine+ doesn't work ([#485](https://github.com/Nicotine-Plus/nicotine-plus/issues/485))
 * Wishlist has issues with chinese characters ([#498](https://github.com/Nicotine-Plus/nicotine-plus/issues/498))
 * Wishlist - Ability to rename wishlist searches ([#499](https://github.com/Nicotine-Plus/nicotine-plus/issues/499))
 * Certain searches don't stop even after closing the tab, restarting the program, and/or disconnecting and reconnecting to Soulseek ([#520](https://github.com/Nicotine-Plus/nicotine-plus/issues/520))
 * stacktrace: struct.error: required argument is not an integer ([#527](https://github.com/Nicotine-Plus/nicotine-plus/issues/527))
 * something goes wrong .... ([#529](https://github.com/Nicotine-Plus/nicotine-plus/issues/529))
 * Warning: unknown object type 'bool' in message 'pynicotine.slskmessages.FileSearchResult' ([#535](https://github.com/Nicotine-Plus/nicotine-plus/issues/535))
 * regression on open files on OpenBSD ([#536](https://github.com/Nicotine-Plus/nicotine-plus/issues/536))
 * Chat messages went nowhere and I got this trace. ([#545](https://github.com/Nicotine-Plus/nicotine-plus/issues/545))
 * filter out unspecific searches ([#551](https://github.com/Nicotine-Plus/nicotine-plus/issues/551))
 * Mouse cursor does not indicate draggable borders ([#552](https://github.com/Nicotine-Plus/nicotine-plus/issues/552))
 * Network share issue ([#559](https://github.com/Nicotine-Plus/nicotine-plus/issues/559))
 * possibly worrie with upload stuck in connecting state if folder uploaded ([#564](https://github.com/Nicotine-Plus/nicotine-plus/issues/564))
 * Let user choose for International flag ([#569](https://github.com/Nicotine-Plus/nicotine-plus/issues/569))
 * Search -> Right Click -> Download folder(s) does nothing ([#574](https://github.com/Nicotine-Plus/nicotine-plus/issues/574))
 * Some weird characters prevents download of file ([#578](https://github.com/Nicotine-Plus/nicotine-plus/issues/578))
 * some margin lines are missing (possible qt/gtk issue) ([#593](https://github.com/Nicotine-Plus/nicotine-plus/issues/593))
 * arrows are missing from the tree view collapse/expand ([#594](https://github.com/Nicotine-Plus/nicotine-plus/issues/594))
 * Nicotine Freezes With Too Many Transfers ([#609](https://github.com/Nicotine-Plus/nicotine-plus/issues/609))

Version 2.0.1 (16 July 2020)
-----------------------------

Changes

 * Fixed an issue where search requests from others weren't processed
 * The update checker now shows the latest version properly

Version 2.0.0 (14 July 2020)
-----------------------------

Changes

 * Ported from Python 2 to Python 3
 * Ported from GTK2 to GTK3 (PyGTK to PyGObject)
 * Support for HiDPI displays
 * Search results and transfers can now be grouped by folder
 * Support for transfers larger than 2 GB in size
 * Transfers and search results now support drag-select
 * Performance improvements in downloads, uploads and search views
 * Special characters (e.g. -, ') are now removed from search terms by default, to receive more search results.
   This behavior can be toggled in Settings -> Misc -> Searches.
 * Excluding search results by placing a - sign in front of a word now works properly
 * Search filters now check the directory path
 * Column widths are now remembered between sessions
 * Added option to open previous tab on startup
 * Added option to hide buddy list
 * Custom messages can now be sent to leechers in Settings -> Misc -> Plugins -> Leech detector
 * Plugins are now bundled with Nicotine+ installations by default
 * Nicotine+ now follows the XDG Base Directory Specification
 * Replaced deprecated dependencies with maintained ones
 * Added unit and DEP-8 continuous integration testing
 * Minor UI cleanups
 * General code cleanups, removed dead code
 * Replaced non-free sound effects

Bugs closed on GitHub

 * Columns Position Not Being Maintained ([#8](https://github.com/Nicotine-Plus/nicotine-plus/issues/8))
 * Add "Group by folder" option to search results ([#17](https://github.com/Nicotine-Plus/nicotine-plus/issues/17))
 * Downloads tab hanging when adding a lot of files ([#34](https://github.com/Nicotine-Plus/nicotine-plus/issues/34))
 * NTFS support on linux ([#49](https://github.com/Nicotine-Plus/nicotine-plus/issues/49))
 * Show network drives when adding a shared directory. ([#52](https://github.com/Nicotine-Plus/nicotine-plus/issues/52))
 * send to player does not work. ([#53](https://github.com/Nicotine-Plus/nicotine-plus/issues/53))
 * CPU usage spikes and remains high after period of usage ([#54](https://github.com/Nicotine-Plus/nicotine-plus/issues/54))
 * Segfault When Getting User Info ([#57](https://github.com/Nicotine-Plus/nicotine-plus/issues/57))
 * Segmentation fault on Ubuntu Gnome 17.04 ([#60](https://github.com/Nicotine-Plus/nicotine-plus/issues/60))
 * filenames with ? in them get stuck on uploads list ([#61](https://github.com/Nicotine-Plus/nicotine-plus/issues/61))
 * Nicotine+ Windows 8.1 (64-bit) mutagen attempts to handle non-video files ([#62](https://github.com/Nicotine-Plus/nicotine-plus/issues/62))
 * Nicotine+ 1.4.1, windows 8.1 (64-bit) errors when using UPNP ([#63](https://github.com/Nicotine-Plus/nicotine-plus/issues/63))
 * Nicotine+ 1.4.1, windows 8.1 (64-bit) Spurious error messages ([#64](https://github.com/Nicotine-Plus/nicotine-plus/issues/64))
 * Nicotine + 1.4.1, windows 8.1 (64-bit) buttons not working ([#65](https://github.com/Nicotine-Plus/nicotine-plus/issues/65))
 * Downloads directory is not shared ([#66](https://github.com/Nicotine-Plus/nicotine-plus/issues/66))
 * Can't share directories ([#68](https://github.com/Nicotine-Plus/nicotine-plus/issues/68))
 * Question: Is Development Dead? ([#73](https://github.com/Nicotine-Plus/nicotine-plus/issues/73))
 * select ValueError: filedescriptor out of range in select() ([#77](https://github.com/Nicotine-Plus/nicotine-plus/issues/77))
 * blurry tray icon in kde plasma ([#81](https://github.com/Nicotine-Plus/nicotine-plus/issues/81))
 * Problems sharing files ([#83](https://github.com/Nicotine-Plus/nicotine-plus/issues/83))
 * Choosing "Download containing folder(s)" from search results does nothing ([#84](https://github.com/Nicotine-Plus/nicotine-plus/issues/84))
 * Uploads not working ([#85](https://github.com/Nicotine-Plus/nicotine-plus/issues/85))
 * UI very condensed on high-dpi linux. ([#88](https://github.com/Nicotine-Plus/nicotine-plus/issues/88))
 * Wishlist returns empty results for foreign characters ([#89](https://github.com/Nicotine-Plus/nicotine-plus/issues/89))
 * New Commits - Is Development Back? ([#90](https://github.com/Nicotine-Plus/nicotine-plus/issues/90))
 * Filter doesn't include directory path ([#91](https://github.com/Nicotine-Plus/nicotine-plus/issues/91))
 * XDG Base Directory Support ([#94](https://github.com/Nicotine-Plus/nicotine-plus/issues/94))
 * Port to python3 ([#99](https://github.com/Nicotine-Plus/nicotine-plus/issues/99))
 * Nicotine+ 1.4.2, Debian 9 (64-bit) Downloading file size >2GB appears as negative numbers, files near 4GB download 0 byte. ([#100](https://github.com/Nicotine-Plus/nicotine-plus/issues/100))
 * Nicotine+ 1.4.1 don't handle invalid characters in Windows ([#101](https://github.com/Nicotine-Plus/nicotine-plus/issues/101))
 * Random crash on Raspbian ([#103](https://github.com/Nicotine-Plus/nicotine-plus/issues/103))
 * Bitrate not shown for most music in search results ([#104](https://github.com/Nicotine-Plus/nicotine-plus/issues/104))
 * Nicotine+ 1.4.2, Debian 9 (64 bit) : Can't get shared files + current downloads disappeared : since the last but one update, from branch master ([#107](https://github.com/Nicotine-Plus/nicotine-plus/issues/107))
 * Website is badly out of date ([#109](https://github.com/Nicotine-Plus/nicotine-plus/issues/109))
 * images seem to be integrated from the launch directory if they have special names ([#113](https://github.com/Nicotine-Plus/nicotine-plus/issues/113))
 * Not working on Ubuntu 20.04 Focal Fossa ([#115](https://github.com/Nicotine-Plus/nicotine-plus/issues/115))
 * Please update Nicotine to work on the latest Ubuntu (20.04) ([#123](https://github.com/Nicotine-Plus/nicotine-plus/issues/123))
 * Compiled 'Master Branch' - Nicotine is Black Blank Screen? ([#140](https://github.com/Nicotine-Plus/nicotine-plus/issues/140))
 * Question: 1.4.3 - Columns Hiding? ([#143](https://github.com/Nicotine-Plus/nicotine-plus/issues/143))
 * info user correct extra typo ([#144](https://github.com/Nicotine-Plus/nicotine-plus/issues/144))
 * select user transfert does not select anything ([#145](https://github.com/Nicotine-Plus/nicotine-plus/issues/145))
 * clicking hyperlinks does not open browser ([#146](https://github.com/Nicotine-Plus/nicotine-plus/issues/146))
 * left click does not work on users nickname in rooms ([#147](https://github.com/Nicotine-Plus/nicotine-plus/issues/147))
 * Interest tab : text zone too small ([#148](https://github.com/Nicotine-Plus/nicotine-plus/issues/148))
 * request : adding file chooser preview widget in info user picture setting ([#149](https://github.com/Nicotine-Plus/nicotine-plus/issues/149))
 * menu separator does not follow gtk+ rules ([#151](https://github.com/Nicotine-Plus/nicotine-plus/issues/151))
 * 1.4.3 Linux - Hidding Tabs - Always Opens Now Under Buddy List ([#154](https://github.com/Nicotine-Plus/nicotine-plus/issues/154))
 * strace shows weird file access syscalls ([#155](https://github.com/Nicotine-Plus/nicotine-plus/issues/155))
 * (world) flags missing at startup / and buddy list ([#161](https://github.com/Nicotine-Plus/nicotine-plus/issues/161))
 * setup.py: DistutilsFileError ([#164](https://github.com/Nicotine-Plus/nicotine-plus/issues/164))
 * warnings causes by userlist resizing columns ([#165](https://github.com/Nicotine-Plus/nicotine-plus/issues/165))
 * Question: No more charsets selection ? ([#180](https://github.com/Nicotine-Plus/nicotine-plus/issues/180))
 * my gtk3 theme gives checkbuttons looks bigger ([#181](https://github.com/Nicotine-Plus/nicotine-plus/issues/181))
 * Question - Bug? - Log Window Issue ([#186](https://github.com/Nicotine-Plus/nicotine-plus/issues/186))
 * wait a minute, only spellchecker is missing ? ([#190](https://github.com/Nicotine-Plus/nicotine-plus/issues/190))
 * userlist for myself does not display files number ([#192](https://github.com/Nicotine-Plus/nicotine-plus/issues/192))
 * AttributeError in changecolour(): PrivateChat object has no attribute 'tag_log' ([#194](https://github.com/Nicotine-Plus/nicotine-plus/issues/194))
 * Add support for >2GB downloads ([#201](https://github.com/Nicotine-Plus/nicotine-plus/issues/201))
 * IndexError at start on Debian Buster ([#202](https://github.com/Nicotine-Plus/nicotine-plus/issues/202))
 * Speed up program startup times ([#215](https://github.com/Nicotine-Plus/nicotine-plus/issues/215))
 * custom tray icons not respected ([#239](https://github.com/Nicotine-Plus/nicotine-plus/issues/239))
 * Request: Modes Tab Placement? ([#242](https://github.com/Nicotine-Plus/nicotine-plus/issues/242))
 * text in log aera in chat rooms lag to display from entry ([#253](https://github.com/Nicotine-Plus/nicotine-plus/issues/253))
 * /now playing does not work after nic+ restart ([#255](https://github.com/Nicotine-Plus/nicotine-plus/issues/255))
 * add grouping by path ([#269](https://github.com/Nicotine-Plus/nicotine-plus/issues/269))
 * on kde LMB on tray icon brings menu, not app ([#270](https://github.com/Nicotine-Plus/nicotine-plus/issues/270))
 * lower on an int? ([#278](https://github.com/Nicotine-Plus/nicotine-plus/issues/278))
 * right-clicking file that user 2 downloads points to user 1 ([#297](https://github.com/Nicotine-Plus/nicotine-plus/issues/297))
 * Private Chat tab does not get notified on receiving a message ([#299](https://github.com/Nicotine-Plus/nicotine-plus/issues/299))
 * RMB doesn't select what's underneath it ([#300](https://github.com/Nicotine-Plus/nicotine-plus/issues/300))
 * unable to download to created folder ([#301](https://github.com/Nicotine-Plus/nicotine-plus/issues/301))
 * status never reach 100% becasue of filtered files ([#302](https://github.com/Nicotine-Plus/nicotine-plus/issues/302))
 * twice downloaded same folder, aborted duplicate files, remove aborted does not remove ([#305](https://github.com/Nicotine-Plus/nicotine-plus/issues/305))
 * downloading folder from user browse doesn't work ([#311](https://github.com/Nicotine-Plus/nicotine-plus/issues/311))
 * cannot connect ([#312](https://github.com/Nicotine-Plus/nicotine-plus/issues/312))
 * In download page, pressing Delete key removes 2 files instead of 1 ([#314](https://github.com/Nicotine-Plus/nicotine-plus/issues/314))
 * invalid path ([#318](https://github.com/Nicotine-Plus/nicotine-plus/issues/318))
 * Distrib message type 93 unknown ([#322](https://github.com/Nicotine-Plus/nicotine-plus/issues/322))
 * Connection issues after search ([#329](https://github.com/Nicotine-Plus/nicotine-plus/issues/329))
 * Window decorator close button doesn't work ([#330](https://github.com/Nicotine-Plus/nicotine-plus/issues/330))
 * Question: group by folders vs group by users ([#335](https://github.com/Nicotine-Plus/nicotine-plus/issues/335))
 * [#312](https://github.com/Nicotine-Plus/nicotine-plus/issues/312) continued, cannot connect ([#336](https://github.com/Nicotine-Plus/nicotine-plus/issues/336))
 * Can't find anything from Wu-tang ([#343](https://github.com/Nicotine-Plus/nicotine-plus/issues/343))
 * download stuck in a weird way ([#344](https://github.com/Nicotine-Plus/nicotine-plus/issues/344))
 * Peer messages causing socket error ([#346](https://github.com/Nicotine-Plus/nicotine-plus/issues/346))
 * expand/collapse all missing in upload tab ([#354](https://github.com/Nicotine-Plus/nicotine-plus/issues/354))
 * AttributeError: 'Uploads' object has no attribute 'transfers' ([#360](https://github.com/Nicotine-Plus/nicotine-plus/issues/360))
 * remove filtered files when autoremoving ([#374](https://github.com/Nicotine-Plus/nicotine-plus/issues/374))
 * wishlist searches should notify on finding a result, not on attempting to find something ([#380](https://github.com/Nicotine-Plus/nicotine-plus/issues/380))
 * Search log window case insensitive. ([#384](https://github.com/Nicotine-Plus/nicotine-plus/issues/384))
 * Gentoo upnp errors, failed to map the external wan port. ([#385](https://github.com/Nicotine-Plus/nicotine-plus/issues/385))

Version 1.4.3 (unstable)
-----------------------------

* Rolling development release in preparation for 2.0.0

Version 1.4.2 (17 February 2018)
-----------------------------

Bugs closed on Github

 * Bitrate - Length - Speed ([#45](https://github.com/Nicotine-Plus/nicotine-plus/issues/45))
 * bug or feature ? ([#47](https://github.com/Nicotine-Plus/nicotine-plus/issues/47))

Version 1.4.1 (12 February 2017)
-----------------------------

Bugs closed on Github

 * 1.4.0 /usr/bin empty ([#38](https://github.com/Nicotine-Plus/nicotine-plus/issues/38))
 * Configure - Directories Page 4 of 5 ([#39](https://github.com/Nicotine-Plus/nicotine-plus/issues/39))
 * Configure - Username ([#40](https://github.com/Nicotine-Plus/nicotine-plus/issues/40))
 * 1.4.0 Text Off Set Under Columns ([#41](https://github.com/Nicotine-Plus/nicotine-plus/issues/41))
 * Make nicotine work with FreeBSD (PR [#44](https://github.com/Nicotine-Plus/nicotine-plus/issues/44))

Version 1.4.0 (31th January 2017)
-----------------------------

Miscellaneous bugs fixed

 * Some files were not shown in shares due to broken metadata of these files.
 * Fix a bug preventing the offline help to open.

Features

 * Windows installer refreshed.

Bugs closed on Github

 * Make proper release ([#26](https://github.com/Nicotine-Plus/nicotine-plus/issues/26))

Bug closed on Trac (readonly)

 * File Manager / "Open Directory" function in Windows (#717)
 * Open Directory not working (#945)

Version 1.3.2 unstable (14th January 2017)
-----------------------------

Bugs closed on Github

 * Uploads stop working after a while ([#35](https://github.com/Nicotine-Plus/nicotine-plus/issues/35))
 * Can't download from certain users ([#37](https://github.com/Nicotine-Plus/nicotine-plus/issues/37))

Bug closed on Trac (readonly)

 * shared files appear not shared to some peers (#744)
 * Stops Downloading After About 15 Minutes (#759)
 * Browse Files from Friemds (#762)
 * Download issue.... (#903)

Version 1.3.1 unstable (10th January 2017)
-----------------------------

Behavior

 * Displaying results of searches should now be faster and not blocking the UI.
 * Send a private message to users who queue a directory has been removed.
 * Hidden directories on Windows are not shared provided you have the pypiwin32 module installed.
 * Tray icons have been modified to be easier to distribute under debian (DFSG compliant).
 * New versions are now checked against the Github releases page.
 * NowPlaying: MPRIS should now be used for Rhythmbox.
 * The MacOS port has been dropped since nobody will step up and maintain it.
 * The pseudo transparency (translux) feature has been removed.
 * Blinking of the trayicon is not recommended and has been removed.
 * Menu icons have been dropped since they are deprecated by GTK.

Features

 * Translations works on Windows.
 * UPnP support out of the box on Windows.
 * Refreshed icon and GTK2 theme on Windows.
 * Gives user the option to load more than 1000 previous chat lines when they rejoin a chat room.
 * Virtual share system implemented.
 * You can now browse your buddy shares via the Share menu.
 * You can now rename your buddy virtual shares via the settings window for shares.
 * Plugins: can now be toggled on/off.
 * Plugins: a reddit plugin has been added.
 * NowPlaying: XMMS Infopipe support has been removed in favor of xmms2.
 * NowPlaying: BMPx support has been removed.
 * NowPlaying: Lastfm support has been updated and require an API key.
 * NowPlaying: Banshee support has been updated.
 * NowPlaying: Foobar support has been updated.

Bugs closed on Github

 * Question - Nicotine Still Being Developed? ([#1](https://github.com/Nicotine-Plus/nicotine-plus/issues/1))
 * bug in userbrowse.py ([#2](https://github.com/Nicotine-Plus/nicotine-plus/issues/2))
 * Remove max length on settings password field ([#5](https://github.com/Nicotine-Plus/nicotine-plus/issues/5), [#7](https://github.com/Nicotine-Plus/nicotine-plus/issues/7))
 * Randomly kill connections on select() out of range failure ([#6](https://github.com/Nicotine-Plus/nicotine-plus/issues/6))
 * Fix shares build / crashes caused by bogus metadata ([#10](https://github.com/Nicotine-Plus/nicotine-plus/issues/10))
 * UPnP Port Mapping piles up in the router ([#11](https://github.com/Nicotine-Plus/nicotine-plus/issues/11))
 * Currently broken on windows ([#18](https://github.com/Nicotine-Plus/nicotine-plus/issues/18))
 * File transfers are failing ([#19](https://github.com/Nicotine-Plus/nicotine-plus/issues/19))
 * Fix variable bitrate detection for MP3 files ([#20](https://github.com/Nicotine-Plus/nicotine-plus/issues/20))
 * Information On nicotine-plus.org ([#21](https://github.com/Nicotine-Plus/nicotine-plus/issues/21))
 * Build fails on archlinux, can't copy mo file... ([#22](https://github.com/Nicotine-Plus/nicotine-plus/issues/22))
 * Hidden directory files now showing up in file shares (Windows) ([#23](https://github.com/Nicotine-Plus/nicotine-plus/issues/23))
 * upnp functionality is used despite being config'd as False ([#24](https://github.com/Nicotine-Plus/nicotine-plus/issues/24))
 * userbrowse coredump on GTK 2.24.30+ ([#25](https://github.com/Nicotine-Plus/nicotine-plus/issues/25))
 * "invalid operation on closed shelf" error on every download ([#27](https://github.com/Nicotine-Plus/nicotine-plus/issues/27))
 * Unable to save settings ([#32](https://github.com/Nicotine-Plus/nicotine-plus/issues/32))
 * Clear Finished/Aborted button problem ([#33](https://github.com/Nicotine-Plus/nicotine-plus/issues/33))
 * Settings window slow to open ([#36](https://github.com/Nicotine-Plus/nicotine-plus/issues/36))

Bug closed on Trac (readonly)

 * "Abort & Delete" button is mislabeled (#194)
 * No icon found in nicotine.exe (#512)
 * French translation and non-translatable strings (#524)
 * Limiting number of upload slots doesn't work all the time (#651)
 * Add option to override locale dir (#495)
 * File and Fast-Configure keyboard shortcuts are the same (#658)
 * Rescanning shares stalls/fails in some cases (#671)
 * Distressingly, /al is not working in private chat (#678)
 * tab completion of user name does not work in private chat (#679)
 * slskmessages.py:69:__init__:Exception: Programming bug (#697)
 * upload queue size limits can't be set to "unlimited" (#706)
 * Impossible to install nicotine without a mouse (#712)
 * Tray icon is lost after explorer is terminated, doesn't return after explorer is restarted (#715)
 * nicotine crashed with TypeError in PopulateFilters(): value is of wrong type for this column (#726)
 * Dont draw eventbox background for tab labels (#727)
 * Rythmbox Now Playing Error (#750) (#935)
 * Realpath / filename error (#776)
 * Connection limit (#802)
 * Disabled UPnP support due to errors Message (Can We Silence?) (#803)
 * English text refactorizationillisms (#828)
 * Cannot download from soulseekqt users (#912)
 * Corrected Hungarian translation for 1.2.16 (#923)
 * Nicotine+ 1.2.16 on win7SP164bit - German language (#998)

 A bunch of outdated bug reports have been closed on Trac.


Version 1.2.16 (31th October 2010)
----------------------------------

Behaviour

 * Updated most country flags (#599)
 * All messages should now be properly timestamped in the log (#602)
 * Saving user pictures now appends a timestamp so pictures aren't overwritten

Features

 * Foobar support for NowPlaying (#644)

Bugs

 * Division-by-zero errors broke transfers (#561)
 * Some packets were packed incorrectly (#570)
 * Recursive downloads didn't work (#571)
 * Search results were improperly formatted (#594)
 * Copying folder URLS didn't work (#574)
 * Mid sentence tab completion destroyed input (#562)
 * Portmapping with MiniUPnPc (the binary) didn't work (#593)
 * Deprecated raise statements using strings (#613)
 * Transparency wasn't saved properly (#615)
 * Shares didn't work properly with out-of-ASCII characters (#623, #345)
 * Fileshare counter increased on refreshing a filelist (#617)
 * Program failed to start with a corrupt transfer file (#628)
 * Network loop crashed on invalid DistribSearch packets
 * Private rooms often didn't show up in the room list (#641)
 * nicotine.desktop was missing P2P and Network sub categories (#660)


Version 1.2.15 (16th February 2010)
-----------------------------------

Behaviour

 * Changed the description for our .exe files so it shows up as Nicotine+ in
   firewalls (ticket #498)
 * When using an upload slot limit, uploads that don't start within 30 seconds
   are no longer counted as a used slot. This stops a single faulty user from
   preventing other connections
 * The clear button in the upload view now clears erred transfers too
 * Unhide user info tab when a new userinfo is received
 * Transfer views update less frequently reducing the amount of CPU needed.
 * xdg-open is now used by default to open folders and play music

Features

 * Now-Playing support for Amarok2 (Ticket #423)
 * FastConfigure dialog for new users (Ticket #482)
 * Country flags now have tooltips (Ticket #521)
 * Now-Playing support for Banshee

Bugs

 * Collapse mode in upload/download didn't work for newly added files, wasn't
   remembered with restart (ticket #205)
 * The packing/unpacking of network messages has been made more explicit. This
   should make Nicotine+ less likely to fail on different processor types and
   operating systems (Tickets #486 #493 #518 #540 #548)
 * Double quotation marks weren't filtered from filenames on Windows systems
 * Ban list got unintentionally deleted sometimes (Ticket #519)
 * "Show IP" didn't not work on the userinfo page (Ticket #522)
 * Wishlist searches would stop working if the setting "Reopen search tabs" was
   disabled and the user closed the search tab (Ticket #552)
 * Incoming RoomSearch raised exceptions

Translations

 * ><((((*> updated the French translation
 * djbaloo updated the Hungarian translation


Version 1.2.14 (4th October 2009)
---------------------------------

Behaviour

 * A corrupt configuration file will no longer make Nicotine+ fail on startup (ticket #483)
 * Multiple shares can now be loaded from the harddrive at the same time

Features

 * Support for UPnP through MiniUPnPc (ticket #230)

Bugs

 * Search failed to work on certain combinations of OS and processor (ticket #486)
 * Implemented our own filelist iterator, dramatically reducing the amount of
   CPU cycles needed to open filelists. Thanks goes to Nick Voronin (ticket #480)
 * Bitrates for Musepack audio were scanned incorrectly
 * Saving file lists from users with slashes in the name didn't work
 * Filesize was incorrect for files around 2 gigabytes and up in userbrowse.


Version 1.2.13 (22 Sept 2009)
-----------------------------

Behaviour

 * Download queue is stored independently from the normal configuration file (ticket #467)
 * Non-working connections are cleaned up more aggressively (ticket #473)

Features

 * Themes can now use a range of image types, including SVG
 * Ownership of private rooms is now displayed
 * Search chatroom logs by pressing F3
 * ASF Support in case Mutagen is used
 * The location of Nicotine+ is restored on startup
 * Rudimentary download rate limiter
 * The NowPlaying code for Audacious now supports audtool2 as well

Bugs

 * Notifications failed when a user had <> in the name
 * Highlight icon kept on blinking with detached windows
 * Fixed links in the Help menu that didn't work (ticket #459)
 * A few different GUI related bugs that should make Nicotine+ much more
   responsive and use less CPU: Startup time reduced when there is a queue,
   queueing many items at a timer, pressing buttons like "Clear Finished" and
   "Abort User's Upload(s)"
 * ...and lots of tiny bugs

Translations

 * Žygimantas updated Lithuanian translation
 * Kenny updated Dutch translation
 * Nils updated Hungarian translation


Version 1.2.12 (26 May 2009)
----------------------------

Behaviour

 * RGBA mode is no longer on by default, to use it pass the --enable-rgba flag when starting Nicotine+
 * On Windows, configuration files are now stored in the user's Application Data folder instead of the installation folder (bug #330)
 * The configuration screen for shares has been rearranged in order to make it more logical (bug #341)
 * Support for Mutagen has been added. This will result in more accurate information about bitrates and lengths (bug #259)
 * Icons have been replaced, the alt-tab icon is increased.
 * Most external calls now support pipes
 * Improved German (bug #394) and French translation (thanks goes to ><((((*>)
 * The dependency for PyVorbis has been removed in favour of Mutagen (bug #409)
 * Notification popups will no longer stack but a single popup will be updated

Features

 * Built-in Webbrowser (MozEmbed)
 * Ignore by IP
 * Windows components have been improved
 * The language selection now uses normal names instead of abbreviations (bug #332)
 * When switching languages GTK will be translated as well
 * Hash checking to eliminate duplicates. When a file name conflict arises after a download finishes both files are hashed
   to make sure the new file is not identical to the old one.
 * Public Room support has been added
 * The amount of tracked and displayed search results is now limited, which should allow nicotine+ to cope better with overly
   generic search terms. Internally a maximum of 1500 are recorded, of which a maximum of 500 are shown. The other 1000 can be
   retrieved by using the filters. (bug #284)
 * Notebook tabs can be reordered and hidden, and these settings will be remembered.
 * Search results are now limited. There are two different limits:
   1) The show limit. This is the amount of results shown in the search tabs
   2) The store limit. This is the amount of results stored internally. This is useful when using search filters
   These limits are configurable from the configuration screen. (bug #284)
 * Nicotine tries to rename itself from 'python' to 'nicotine' for programs like 'ps' (requires procname module) and 'pkill' (bug #355)
 * 'Remember choice' option in the quit confirmation dialogue
 * It is possible to ignore people based on their IP address
 * Import warnings are now shows in the log window as well as in the console (bug #381)
 * New logging functionality, which means no more messages should get lost in the console
 * You can change your password now (bug #424)
 * Misc. improvements to transfer handling
 * Tab completion can be done by in-line replacement instead of dropdown list
 * Transfer views now have a 'Place in line' column

Bugs

 * The Danish translation is now stored under 'da'
 * Fixed sorting of percentage (bug #322)
 * A number of typographical errors have been corrected (bug #334 and #335)
 * When disabling sound this setting will be loaded correctly now (bug #285)
 * Repaired sayprivate function from the pluginsystem
 * The Windows versions now comes with jpeg62.dll (bug #342)
 * The word '-' is now filtered from search queries (bug #367)
 * Handling of word wrapping of extremely long words is improved
 * Tray icon menu on OSX
 * Private Room handling has improved (bug #432)


Version 1.2.10 (30 December 2008)
---------------------------------

Features

 * Added support for RGBA, enabling Murrine users to use transparency and round menus
 * Tabs can be reorderen and can be hidden

Bugs

 * Fixed bug #177, notification popups are now split into file and directory notifications
 * Fixed bug #274, cancelling and disowning private rooms bug (fr3shpr1nc3)
 * Fixed bug #226, file size dropdown in search filters are more readable now
 * Fixed bug #310, activity icon no longer activates on our own typing
 * Timestamps in private messages now are displayed correctly
 * Room searches work again (was broken in 1.2.10alpha)


Version 1.2.10 alpha (9 November 2008)
--------------------------------------

Features

 * Added last.fm to the now-player (gallows)
 * Added first version of the plugin system
 * Tabs can be closed using the middle mouse button
 * Usernames can be copied from the channel list (right click, select the
   username from the menu)
 * Added a popup that will inform users in case a local port cannot be bound
 * Connections will be dropped when the maximum is approached, decreasing the
   chance for "IOError" messages

Bugs

 * 'Send to player' failed because of missing quotes for finished downloads
 * Fixed a bug with tuple error message causing a traceback
 * Fixed a translation bug, caused by tabs positions top, left, etc that caused
   settings dialog to not work properly
 * Fixed rhytmbox support with "Now Playing" (gallows)
 * Fixed Audacious support with "Now Playing" (gallows)
 * Fixed sending out the wrong username with search results
 * Updated all server references to the new server
 * A inverted port range no longer causes connection failures
 * Removed deprecated GTK calls

Buddylist

 * Radio buttons now allow the buddylist to be toggled as always visible, in own
   tab, or in the chatroom tab.

General Changes

 * The Edit menu has been broken into Edit, View and Shares menus
   (similar to Enr1X's patch http://nicotine-plus.org/ticket/231 )
   Also fixed the duplicate Alt-B hotkey (hide flags is now Alt-G).
 * Committed QuinoX's patch for case-insensitive nick completion (#252)

Chat Rooms

 * Added Server Message 141, enables Private Chat Room Invitations and thus
   allows those you invite to get past the annoying server message that warning
   when a user you've invited 'hasn't enabled private room add'.
 * Blocking a user's IP address is now easier with the addition of a chatroom
   popup menu item
 * Private Rooms: You can now create private rooms via the roomslist popup menu
   and add users to your private rooms via any chatroom user popup-menu. You can
   also drop ownership of a private room and drop membership of another person's
   private room. This feature is currently available on the testing server only.

Search

 * Country flags are shown in search results, metadata dialogs

Settings

 * Upload and Download transfer lists now have customizable double-click options
   in Transfers->Events.
 * A Backup config menu item was added to the Edit menu. This will backup your
   Nicotine+ config and config.alias (if it exists) into a BZ2 archive. If you
   cancel the backup filename saving process, an archive with the format
   'config backup YYYY-MM-DD HH:MM:SS.tar.bz2' will be created.
 * Visible colors have been added to the Colour settings (for those who don't
   read hexadecimal).
 * Separate fonts for Search, Transfers, Browse and a font for all other lists
   can now be set.


Translations

 * Slovak Translation Updated (Jozef)


Version 1.2.9 Release (22 September 2007)
-----------------------------------------

Licensing

 * Relicensed all code under GPLv3 and LGPLv3

General Changes

 * Config menu items that were in the File menu moved to the new Edit menu
 * Added credits and license note to About Nicotine dialog.
 * Disable many widgets (entries, buttons, lists) when disconnected from server
 * User tabs have right-click popup-menus in private, userinfo and userbrowse.
 * libnotify support added (patch by infinito ticket #176 )
   notification-daemon, libnotify and python-notify required
 * Added a 10 second cooldown between responding to Userinfo and Usershares
   requests from the same user (to mitigate damage from DOS attacks and simple
   accidents)
 * Notification text on tabs can be colored
 * Notification icons on tabs can be disabled
 * Close buttons on tabs no longer forced to 18x18px
 * Close buttons are dynamically added and removed when toggled in settings
 * Added global unrecommendations list
 * Merged Amun-Ra's 'Country flag column in Chatroom userlists' (this is a new
   feature on the testing server) but works with manual IP lookups with GeoIP.
   This requires the 242 flag images. Additions to several server messages are
   used instead of GeoIP if they are available.
 * Simplified GeoIP module loading

Userinfo

 * Added popups to user's interests lists (search, add and remove interests)
 * Added a zoom and save popup menu to the Userinfo image.

Shares

 * Shares are precompressed, before they're sent (Nicotine will recover faster
   from many shares requests)
 * Unicode filenames on Win32 are now read and shared properly (should be)

Settings

 * Tooltips can be disabled
 * Settings widgets will now be colored red if their values are invalid.
 * Your client port and server-reported IP address are shown in Server Settings
 * Added an option to Shares for the Upload directory path (needs to be set)
   The upload directory is where your buddies 'uploads' will be saved.
 * Default colours and clear colours buttons added
 * All Notebook Tabs can be repositioned and the labels can be rotated 90⁰
   under Settings->Interface->Notebook Tabs
 * Added Exaile to NowPlaying
 * Added a config option for overriding the default language
 * URL handlers settings rearranged slightly, combo items in the handlers column
 * Rearranged the Settings tree and removed some descriptive panes
 * Added IP blocking and range blocking with * character
 * Some Entry widgets in settings replaced with SpinBoxes
 * Userinfo settings now have size data for image
 * New options to to determine what happens when destroying the main window
   (show a dialog, close to tray, or quit)

Search

 * Search is now a genuine TreeView that supports group-by-user and
   has a expand/collapse all toggle when grouping is enabled.
 * Added a Clear results button
 * Added 'Download containing folder(s) to..' to the search results popup
 * Open a new socket for every outgoing search result to avoid problems with
   shared sockets getting closed.
 * Only close sockets of incoming search results if input/output buffers are
   empty. (this may still result in the transmitting sockets)
 * Added Search and Open Directory items to the uploads popup menu
 * Search results encoding improved (user's encoding, falls back to global)
 * Search results turn red when a user goes offline (configurable)
 * Added a 'multiple users' submenu to search results popup

Transfers

 * Show total time elapsed and remaining in user's parent row instead of the
   current transfer's time elapsed and time remaining.
 * Added a maximum files-per-user limit to the upload queue
 * Added a 'Clear Failed' item to the uploads menu
 * Added 'Clear Filtered' and 'Clear Paused' to the downloads menu
 * Fixed pausing of aborted downloads after reconnecting to the server.
 * Added an 'Auto-retry Failed' checkbox to downloads (3 minute timer)
 * Added an 'Autoclear Finished' checkbox to uploads
 * Notify popups for completed files and completed directories (toggleable)
 * Added a 'multiple users' submenus

Chat

 * Whitespace is now limited to two spaces
 * Show icon, sound, speech and title notifications for "current" chat tab
   if the window is hidden.
 * Notify popups for buddies with "notify" enabled :)
 * Read chatroom logs (and attempt to parse them) when rejoining a room.
   Parsing will not work if the logs do not use the default timestamp format.
   Chat room and Private chat logs are in seperate sub-directories, now.
 * Threaded /aliases and /now commands (GUI no longer freezes)
 * Use the /detach and /attach chatroom commands to pop chatrooms and private
   chats into their own windows.
 * Text-To-Speech support added (configurable under Settings->Misc->Sounds)
   individual chat rooms can be disabled with the text-to-speech toggle button.
   Chat messages are read out, and nick mentions are announced. By default,
   there are commands for flite ( http://www.speech.cs.cmu.edu/flite/ )
   and festival ( http://www.cstr.ed.ac.uk/projects/festival/ ).
 * URL text color is configurable (doesn't effect old links after changing)
 * Timestamps are now configurable, disableable (under Settings->Chat->Logging)
 * Log files' timestamps are also configurable. Default is "%Y-%m-%d %H:%M:%S"
 * Added a help button for chatroom commands
 * Added hide/show buttons in chatrooms for userlist and status log. These
   buttons can be hidden by Edit->Hide chat room log and list toggles
 * Username away color-status in chat can be toggled off
 * Added Auto-Replace list (applies to all outgoing chat message text)
 * Added Censor list (applies to all chat message text)
 * A popup dialog appears after closing the last chat room while the roomlist
   is hidden.
 * URL's are now converted back to plain text by the URL catcher
   (before only %20 were converted to spaces)
 * Usernames in chat logs and private, userinfo and userbrowse tab labels are
   marked offline when disconnected from server
 * Ticker moved to the top-left of the chat room frame;
 * Added settings for tab completion and dropdown completion list
 * Added a completion dropdown list (gtk.EntryCompletion) to chat entries

Bug Fixes

 * Renabled the 'if i.size is None' check which should fix some upload issues
 * Fixed a error message printed after aborting an upload directory popup
 * Fixed a major slowdown in needConfig function (was reading shares data)
 * Pressing enter in Search Filter entry boxes now works again
 * Readded "/" to pasted folder slsk:// URLs
 * Reading slsk.exe's cfg files should now work on Windows


Version 1.2.8 Release (1st June 2007)
-------------------------------------

GENERAL CHANGES

 * Support for Spell Checking in chat added (libsexy and python-sexy required)
 * Other users Interests are now shown in the User Info tab, with expanders
 * Send Message added to trayicon
 * Popup Menus in Private, Chatrooms, and User Browse reorganized
 * The user-entry boxes are now buddy-list combobox entries
 * Users with PyGTK >= 2.10 will use the gtk.StatusIcon instead of
   the old trayicon.so module.
 * Added a filemanager popup item to the self-browse menu; configurable
   under Settings->Advanced->Events
 * Gstreamer-Python support for sound effects added
 * Added Soulseek testing server (port 2242) to the server combobox.
 * Changed the URL Catcher's syntax. The ampersand "&" is no longer needed
   at the end of URL Handlers. The handler entry is now a combobox and
   includes a bunch of webbrowser commands.
 * Userlist Columns are hidable and hidden status is saved.


TRANSFERS

 * Added a "Group by users" check box
 * Added Expand/Collapse all toggle button to transfers
 * Added a popup dialog to the "Clear Queued" transfers buttons

PRIVATE CHAT

 * Added gallows' patch for including your username in the private chat log.
   (ticket #161)
 * Direct private messages (currently only supported by Nicotine+ >= 1.2.7.1)

SEARCH

 * Search now has combo boxes, per-room searching and per-user searching.
 * Added Wishlist and changed remembered search tabs to only display
   when new search results arrive
 * Switch to newly started search tab (ticket #157)

USERINFO

 * gallows added userinfo image zooming via the scrollwheel (ticket #160)

SETTINGS

 * Changed Audio Player Syntax it now uses "$" as the filename
 * Exit dialog can be disabled in Settings->UI
 * When a config option is detected as unset, print it in the log window.
 * Move Icon theme and trayicon settings to a seperate frame
 * Move sound effect and audio player settings to a seperate frame
 * Reopen Settings dialog, if a setting is not set.

NETWORKING

 * On Win32, hyriand's multithreaded socket selector is used. This will allow
   a larger number of sockets to be used, thus increasing stability.
 * Added Server Message 57 (User Interests)
 * Send \r\n with userinfo description instead of just \n

BUGFIXES

 * Uploads to other Nicotine+ users work better
 * Userinfo Description does not scroll to the bottom of the window
 * Fixed a few bugs with the trayicon
 * Fixed server reconnection not actually trying to reconnect (and giving up
   on the first try)

TRANSLATIONS

 * Lithuanian translation updated
 * Euskara translation updated


Version 1.2.7.1 Release (6th March 2007)
----------------------------------------

GENERAL CHANGES

 * The About Nicotine+ dialog now shows the versions of Python, PyGTK and GTK+
 * Copy was added to the right-click menus in chat status and
   debug logs.

BUGFIXES

 * The shares scanning progress bar now disappears after scanning shares a
   little more frequently.
 * Fixed a bug in the way total transfer slots were calculated
 * Improved Remote-Uploading somewhat (was quite buggy with two Nicotine+ clients)
 * Fix directory name cropping in 'upload directory to' in User Browse
 * Attempted to fix the 'interrupted system call' (which sometimes are caused
   by gtk+ file dialogs) from stopping the networking loop.
 * Username hotspots for users who are offline or have left the room aren't
   disabled anymore.

TRANSFERS

 * Downloads have a metadata popup dialog with bitrate / length
 * Right-clicking when nothing is selected will select a row
 * In parent row, display the current transfer's time elapsed and time left.
 * Transfer popups work better on parent rows

TRANSLATIONS

 * Silvio Orta updated the Spanish translation
 * ><((((*> and ManWell updated the French translation
 * nince78 updated the Dutch translation
 * Nicola updated the Italian translation
 * Žygimantas updated the Lithuanian translation


Version 1.2.7 Release (25th February 2007)
------------------------------------------

GENERAL CHANGES

 * Window size is restored on startup
 * Background color of entry boxes, text views and list views is now changeable
   and all lists foreground color changes with the 'list text' option.
 * Added some padding around various widgets
 * Tabs can be reordered on the fly, now (Requires PyGTK 2.10) Also, Chat Room
   tab positions are saved in their reordered position.
 * Per-file identation consistancy was drastically improved. transfers.py,
   slskproto.py and a few others were really bad.

SETTINGS

 * Added an Import Config frame to Settings, which duplicates the functionality
   of nicotine-import-winconfig. User can now easily import config options
   from the official Windows Soulseek client's config directory. Support for importing
   the ignore list was also added to nicotine-import-winconfig.
 * Translux (pseudo-transparent TextViews) is an old easter egg that is now
   customizable in UI Settings.
 * Transfer settings was rearranged and organized with expanders
 * Transfer settings has a new combo box for selecting which users are allowed
   to initiate uploading files to you. Trusted users are set in the buddy list.
 * Added several tooltips to Settings' transfer widgets in hopes of providing
   better explanations of some of the more complex functionality.

USERLIST

 * Comments in Buddy List can now be edited in-list by clicking twice on the
   comment column, not by double-clicking (which would open Private Chat).
 * Trusted checkbox column added to the buddy list. Trusted users are an
   optional selection of users to whom remote uploads can be limited.

CHAT

 * Usernames in the chat room log now have hotspots associated with them,
   meaning they can be left-clicked on to load the same popup as you have in
   the users list.
 * Usernames are also colored based on Online, Away and Offline/In-Room status.
   This option can be disabled in UI Settings.
 * "User is away/online/offline" messages removed from Private Chat


TRANSFERS

 * Transfers are now sub-items in a one-step tree with the user as a parent
 * QuinoX's patch, a download filter: ( http://qtea.nl/tmp/nicotine+ ) was
   reworked a little and given a nice listview to add the Regular Expressions
   (filters) to. This feature will allow you to blacklist certain types of
   files, which may save you from the pointless downloading and cleanup of
   unwanted files.
 * Downloads and Uploads popup menus have a new item under the user submenu,
   "Select User's Transfers".
 * Uploads can be retried
 * The Size column now has the current file position and the total file size
 * Remotely-Initiated-Uploads will no longer be accepted if an Upload Queue
   Notification message has not been sent, first. This means versions of
   Nicotine+ earlier than 1.2.5 will not be able to initiate sending you files,
   no matter what your allowed uploaders is set to.

USER INFO

 * Stats were rearrange and the status of who is allowed to initiate uploads to
   the user was added.

USER BROWSE

 * The browsetreemodels functions were disabled, and file and folder treeviews
   were reimplemented with code from the PyGTK2 museek client, Murmur.
 * Search now works slightly different. Queries match all files in a directory,
   and switch between matching directories each time.
 * Tree lines and a 'Directories' sorting header were added to the Folder Treeview
 * Upload Directories Recursive was added to Folders' Popup
 * An expand / collapse all directories button was added
 * Recursive downloads in User Browse now checks from > 100 files and displays
   a Warning dialog that gives you a chance to cancel downloading.

SEARCH

 * Search has a new popup window for displaying the metadata of search results.
   This popup is accessible after selecting 1 or more files and clicking on the
   "View Metadata of File(s)" popup menu item. From this window, you can also
   download file(s) or initiate browsing of the current file's user's shares.

NETWORKING

 * Handle all peer message unpacking with an exception handler. Should make us
   safer from malformed data sent by users.
 * Close peer connection when userinfo's or browse's close buttons are pressed.
   (This is to save bandwidth)

TRANSLATIONS

 * ><((((*> updated the French translation
 * (._.) and Meokater updated the German translation
 * nince78 updated the Dutch translation
 * Nicola updated the Italian Translation
 * Added Finnish translation by Kalevi
 * Added Lithuanian Translation by Žygimantas
 * Added Euskara (Basque) translation by Julen of librezale.org

BUGFIXES

 * Various minor bugs killed
 * Userlist selection bug fixed
 * Fixed search results from last session being placed in search result tabs in
   new session that match their tickets by using random tickets instead
   starting from 0.
 * Fixed Big memory leak with PixbufLoader in Userinfo (call garbage collector)
 * Fixed large-file (>4GB) file scanning and shares browsing issue


Version 1.2.6
-------------

INTERFACE CHANGES

 * Added a GUI for new built-in NowPlaying scripts and new /now command to use
   them. Supported players: Amarok, Rhythmbox, BMPx, XMMS/Infopipe, MPD/mpc.
   An 'other' player option also exists.
 * Added /buddy, /rem, unbuddy commands to Private Chat and Chat Rooms.
 * The Userinfo Picture file chooser now displays a preview of the image
 * Private Chat does not allow you to send messages while offline. New
   disconnected and reconnected messages appear in the chat log. Another new
   message is displayed if you were sent messages while offline.
 * Users' Shares lists can be saved to disk and then reloaded them, for ease
   and speed. On *nix, these files will be stored in ~/.nicotine/usershares/
 * Display shares-scanning errors in the Log Window
 * Added Titlebar messages on Private Chat and nick mention in Chat Rooms
 * Disabled: Urgency Hint on highlight (Titlebar flashes, or WM tries to get
   your attention) Doesn't work very well, disabled for now.
 * Popup a warning message if the Guide cannot be found
 * Added 'Copy all' menu item to Room Status logs and the debug log
 * Also added icons to the Clear log and the Remove Dislike menu items
 * Enlarged number entry boxes in Transfer Settings
 * Added thread protection to File/Directory Chooser (was getting freezes)

SEARCH

 * Search's Close button also "ignores" the search, like the X button the tab.
 * Fixed bug in "Download file(s) to..." causing the path to be corrupted.

CONFIG

 * Use a safer method to save the config file. Create 'config.new', move old
   'config' to 'config.old', rename 'config.new' to 'config' (from 1.1.0pre1)

PACKAGING

 * Added 4 nicotine-plus-??px.png icons 16px, 32px, 64px and 96px.
 * nicotine.desktop and nicotine-plus-32px.png are installed to
   $PREFIX/share/applications and $PREFIX/share/pixmaps

WINDOWS

 * Added elaborate Unicode filename-reading hack. This should allow
   non-latin files/directories to be added to the shares. (Since this feature
   breaks in Linux, Windows detection is used throughout the filescanner
   converting strings to unicode and back.
 * Always load dbhash module on Windows

NETWORKING

 * Re-enable Server Ping (120 sec) and Timeout for Connection Close (120 sec)
 * Spoof warning now includes the IP and port of the user sending the message.

TRAY ICON

 * Hacked apart Systraywin32 from Gajim to work with Nicotine+ on Windows
   requires pywin32 which you can download from here:
   http://sourceforge.net/project/showfiles.php?group_id=78018
 * Fixed a bug with the Trayicon intially being icon-less

TRANSLATIONS

 * Hungarian translation updated (djbaloo)
 * Portuguese-Brazilian translation finished (SuicideSolution)
 * Slovak Translation Updated (Jozef)

1.2.5.1 September 18th 2006
---------------------------

Bugfix Release

 * Made TrayIcon not attempt to load on 'win32' operating systems
 * Fixed trayicon bug that caused error messages everytime the Settings
   window's Apply or Okay button was pressed when the trayicon isn't loaded.
   (reported by renu_mulitiplus)
 * Fixed displaying your own Userinfo image on Windows.
 * Replace the characters ?, ", :, >, <, |, and * with an underscore _ on
   Windows, to avoid filesystem errors. (Reported by theorem21)
 * Made the Directory Chooser start with the predefined directory set.


Version 1.2.5 September 17th 2006
---------------------------------

GENERAL CHANGES

 * Made columns reorderable (temporarily, they return to the default order
   after a restart)
 * Made the encodings Comboboxes give location or language details in a
   separate column.
 * Made all the popup menus have GTK stock icons.
 * Made most of the Main Menu items have icons.
 * Added three new menu options under help: Offline Nicotine Plus Guide, the
   Nicotine-Plus Trac and the Nicotine Plus Sourceforge Project websites.
 * Added the NicotinePlusGuide to setup.py, so it will be installed
 * Set Firefox as the default http:// URL handler
 * Replaced "pure text" percent column with a CellRendererProgress column in
   the Downloads and Uploads transfer lists.
 * Added option to UI Settings to show/hide the transfer buttons.
 * Added expander to glade2py, so it can now be used.
 * Rearranged the new user entry/buttons to the top left of their tabs, added
   spacing inside tabs.
 * Added more stock GTK icons to Settings and Userinfo, among other places.
 * Added confirmation exit popup dialog when quitting with the window manager.
 * Made the main window's minimum size to be 500x500 px

BUGFIXES

 * Fixed a typo in transferlist.py that caused some transfers to get stuck
   in the Initializing state, even though transfers still work.
 * Fixed the Chatrooms tab hilite bug (reported by Offhand, xrc)

TRAY ICON

 * Made the Tray Icon's popup menu disable menu options based on connection
   status. Also simplified its code to match the way Nicotine normally
   creates menus.
 * Made Trayicon toggleable while running from the UI settings or at startup
   with --enable-trayicon, -t  and --disable-trayicon, -d

SEARCH

 * Made /search commands modify the search history
 * Added 'clear search history' button to search
 * Shortened Search tab length and added a label containing the full query
   next to the "Enable filters" checkbox.

AUDIO

 * Notifications: Now testing 'flite' support, a text-to-speech engine.
   This may or may not be removed. The option is 'speechenabled'
 * Moved Icon theme and Sound theme settings inside separate expanders.
 * Notifications: Added a sound effect, room_nick.ogg, for nick-mention in
   chatrooms (when not in that room) and a separate sound effect, private.ogg,
   for when a private message arrives, and you are not in that tab. Sound
   options are found in the UI settings, and separate sound theme directories
   and audio players can be selected, as well. Ogg files are installed into
   $PREFIX/share/nicotine/$THEMEDIR/

NETWORKING

 * Added support for sending and receiving Soulseek peer message 52, Upload
   Queue Notification, which allows users to notify upload recipients that
   they are attempting to send a file. Also, a log message is printed when a
   user attempts to send you file(s) and an automatic is sent if they aren't
   allowed to.
 * Add a Bool to the GetUserStatus message received from the server, for
   privileges. If 1, add user to list of privileged users.
 * Added SendUploadSpeed (121) message which replaced SendSpeed (34) a long
   time ago. Thanks to sierracat for the info, and to slack---line for testing.
 * Modified CheckVersion function to allow for milli ( X.X.X.X  ) versioning.


Version 1.2.4.1 August 18th 2006
--------------------------------

Bugfix Release

 * Disabled use of 'pwd' module on windows
 * Fixed bug with Buddylist tab not appearing on startup.
 * Fixed bug with double-clicking on a user in the Buddy not switching to the
   correct private chat tab.


Version 1.2.4 August 17th 2006
------------------------------

 * Added new translations for Hungarian (djbaloo) and Slovak (Josef Riha)
 * Made Buddylist toggleable between its own tab and pane on the right side
   of chatrooms
 * Rearranged tabs to the top of the window
 * Rearranged Browse Share's progress bar as in Ziabice's patch
 * Added a Font selector for chat messages under Settings->UI->Interface
   (47th_Ronin's request)
 * Made Nicotine's shares builder ignore ALL dot-files and dot-directories
   (such as the ~/.nicotine/ directory) for security reasons. (Izaak's idea)
 * Warn if home directory is being shared. (Izaak's idea)
 * Added the First in, First out queue from jat's evil cocaine patch (without
   any of the other features)
 * Added gtk stock icons to many buttons
 * Added user entry boxes in Private Chat, User info, and User browse
 * Added new birdy icons which replace the little people icons
 * Added a theme selector to Settings->UI->Interface->Icon Theme Directory
   If any of the theme icons exist in this directory, they'll be used instead
   of the built-in images.
 * Made Copy URL popup menu options use the ctrl-c/ctrl-v clipboard, as well as
the middle-click one
 * Split big Download/Upload Popup menus into submenus
 * Fixed an problem with upload percentages not working properly


Version 1.2.3 July 7th 2006
---------------------------

 * Added abort, retry, ban, clear queued, and clear finished/aborted buttons
   to transfers.
 * Made lists' rows to use the alternating color pattern.
 * Changed all the icons. Most of the new icons are modified from
   Mark James' Silk icon set: http://www.famfamfam.com/lab/icons/silk/
 * Fixed other users sending PM cause the tab to be switched to their message.
 * Fixed erroneously translated internal strings that caused queued downloads
   to fail.


Version 1.2.2 June 15th 2006
----------------------------

 * Renamed "User list" to "Buddy list"
 * Added Double-clicking on a user starts a private message in the chatrooms,
   the userlist, and similar users.
 * Added TrayIcon from unreleased Nicotine 1.1.0pre1, and added a menu to it.
   This is a module and needs to be compiled.
 * Added Speed, Files and Dirs to userinfo
 * Made more strings translatable
 * Added Buddy-only shares


Version 1.2.1 June 10th 2006
----------------------------

 * Added a bunch of hotkeys to the popup menus and normal menus.
 * Added a new menu for Modes (Chat Rooms, Private Chat, etc)
 * Starting a Private message via the Popup menu will now switch you Private
   Chat tab, so you can immediately start typing.
 * Fixed a segfault in User Browse, if you clicked on the folder expanders while
   shares were loading. This was done making the folder pane be disabled while
   refreshing.
 * Updated translations to work with hotkey menu and other changes
 * French translation: systry corrected typos and translated more strings.
 * Added a Send to Player popup menu item, which allows you to send downloading,
   uploading or files in your own shares to an external program, such as a media
   player.


Version 1.2.0b May 11th 2006
----------------------------

 * Added a "Send to Player" popup menu item for downloads and personal shares


Version 1.2.0 May 10th 2006
---------------------------

 * Added New Room and User search messages, and use them instead of sending out
   direct peer searches
 * Fixed all those depreciated Combo() functions, updated all of them to
   PyGTK 2.6 compatible functions.
 * Fixed the CRITICAL pygtk_generic_tree_model warning that has been plaguing
   Nicotine since GTK2.4 came out. The problem was fixed by adding:
   "if not node: node = self.tree"  to the on_iter_nth_child() function.
 * Moved the upload popup-menu item so that it isn't incorrectly disabled from
   sending multiple files.
 * Added two new debugging messages for when someone browses you or gets your
   userinfo, you can see their username. ( Idea/code stolen from "Airn Here",
   pointed out by heni (thanks to both of you) )
 * Fixed a little bug in a popup menu that caused a traceback
 * Added an optional client version message, which is similar to the CTCP
   VERSION message on IRC. It sends your client's version via Private Message to
   a remote  user. You can disable automatic responding of it in the
   Settings->Server.  So far, it works only with this version of Nicotine and
   Museek's Curses client, Mucous. Send it via the popup menu in Private chat,
   or with the command: /ctcpversion


Version 1.0.8-e March 25 2006
-----------------------------

 * Made password to be starred like ***** via cravings' patch
 * Added a Give Privileges popup menu item (taken from the development 1.1.0pre1
   version of nicotine that hyriand never released.)
 * Changed the Upload Files dialog from a textentry to a scrollbox


Version 1.0.8-d Aug 17 2004
---------------------------

 * 1.0.8-d is a combo of 1.0.8z and some new stuff, listing it all here.
 * Added GTK2-Fileselector (Works nicely for Win32)
 * Added many changes to wording of the settings dialogs
 * Added Remote Uploads (Browse yourself, right click on files, upload, type in
   username)
 * Added Remote Downloads (Added Checkbox in Settings->Transfers)
 * Fixed some of the many PyGTK warning messages
 * Removed the PING-OF-BAN

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Forked
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Version 1.0.8rc1 May 1 2004
---------------------------

 * Added the missing handler for server-pushed searches
 * Allow users to have negative speed-ratings
 * Double click downloads in searches and browsers, join room in room list


Version 1.0.7 Jan 11 2004
-------------------------

 * Changed hate-list to be network-driven instead of being a filter
 * Updated translations
 * When available, Nicotine will use PyGNOME to launch protocols that
   haven't been configured


Version 1.0.7rc2 Jan 07 2004
----------------------------

 * Moved encoding dropdown-list out of the scrolled area in userinfo tabs
 * Transfer logs (enable in settings->logging)
 * Last 7 lines of a private message log are shown
 * Config file now backed up (to <filename>.old)
 * Check privileges shows days, hours, minutes, seconds
 * Changed default server to server.slsknet.org
   (mail.slsknet.org will be automatically changed)
 * Anti-frumin ticker update (replace newlines with spaces)
 * Added country-code filter to the search filters
 * Added a "Hide tickers" menu entry which hides all tickers
 * Added option to not show the close buttons on the tabs
 * Added option to not lock incoming files
 * Fixed /tick


Version 1.0.7rc1 Jan 02 2004
----------------------------

 * Added room ticker support
 * Alt-A fixed


Version 1.0.6 - Dec 05 2003
---------------------------

 * Probable fix for GUI freeze (thanks stillbirth)
 * Bye bye total queue limit
 * Translations updated


Version 1.0.6rc1 - Nov 18 2003
------------------------------

 * Files that are downloaded should now be encoded
 * Possible fix for a threading race condition
 * Possible fix for listport not defined problem and a million little things
 * Possible fix for yet-another-corrupted-shares-database problem
 * Translation caching
 * Whacked some tracebacks
 * Implemented recommendations system
 * Translation updates
 * Added polish translation (thanks owczi)
 * Fixed bug that made "Queue limits do not apply to friends" not work
 * Fix for the version checking bug


Version 1.0.5 - Nov 7 2003
--------------------------

 * Quickfix for protocol change


Version 1.0.4.1 - Sep 26 2003
-----------------------------

 * Changed default server
 * Fix for online notify
 * Added french translation (thanks flashfr)


Version 1.0.4 - Sep 17 2003
---------------------------

 ---> Can you find the EASTER EGG? <---

 * Show IP address now shows country name instead of code (when GeoIP is
   installed)
 * Fixed sorting in transferlists
 * Clear (room) log window popup menu
 * Room and user encodings (for chats, browse, userinfoetc)
 * Close buttons on sub-tabs
 * Translatable (see the languages/nicotine.pot file)
 * Window icon (normally blue, yellow when highlight)
 * MacOSX OSError / IOError fixups
 * Fix for minimum window size
 * Desktop shortcut (files/nicotine.desktop), not installed by default
 * Possible fix for the "ServerConnection doesn't have fileupl" problem
 * Userinfo is now properly network encoded
 * Bundled a custom version of the ConfigParser that doesn't have problem
   with semi-colons
 * Download to.. for searches now defaults to downloaddir
 * Close tab-button for searches closes and ignores
 * UTF8 log window fixes
 * Fix for invalid server traceback (in settings window)


Version 1.0.3 - Aug 28 2003
---------------------------

 * PyGTK version check (Nicotine requires 1.99.16 or higher)
 * Hide room list menu option (is remembered between sessions)
 * Control-C doesn't kill nicotine anymore (silently ignored)
 * Fix for deprecation warning (PyGTK 1.99.18)
 * Bug-reporting assistant (based on work by
   Gustavo J. A. M. Carneiro)
 * Reduced the sensitivity of the auto-scroller a bit
 * Workaround for missing-menu-labels in tab popup menus
 * Changed PyVorbis warning
 * Check latest (checks if you're using the newest version)
 * Autocompletion of / commands
 * Some small psyco fixes
 * Browse yourself without even being connected
 * Default filter settings
 * Fixed searches for special characters and limit history to 15 entries
 * Long overdue enter-activates-OK in input dialog
 * Make folder button in directory chooser dialog
 * Change %20 in slsk:// urls to spaces (blame Wretched)
 * Copy file and folder URLs in transfer lists and searches
 * Fixed Hide log window on startup
 * Improved the move-from-incomplete-to-download-folder function so that it
   can move across partitions / drives / whatever.
 * Now really included Carlos Laviola's debian control files


Version 1.0.2 - Aug 23 2003
---------------------------

 * Possible fix for freezes
 * Fix for GTK-Critical at startup with hidden log
 * Fixed URL catcher regular expression a bit
 * Added debian control files (by Aubin Paul)
 * Hopefully fixed the missing "2 chars search result directory" thing
 * Fixed roomslist popup menu
 * More UTF8 cleanups (and dumped the need for most of the localencodings
   in the process), should really work on MacOSX again
 * Fixed alt 1-8 / left,right,up,down to work with numlock / scrolllock on
 * Checkboxified all the "Add to user list", "Ban this user" and "Ignore
   this user" context-menu items
 * Fixed small bug in config loader (concerning importing pyslsk-1.2.3 userlist)
 * Fixed small bug in the browse file model
 * Fixed some selection issues
 * Fixed rooms list being sorted A-Za-z instead of Aa-Zz
 * Fixed column-sizes being weird when resizing
 * Removed talkback handler
 * Added handler for slsk:// meta-protocol and the ability to copy slsk://
   urls in browse ("Copy URL").
 * Should work on OSX again
 * Threading issue with rescanning fixed
 * Focus chat line input widget on tab change (chat rooms and private chat)
 * <insert stuff I forgot to add to changelog here>


Version 1.0.1 - Aug 19 2003
---------------------------

 * UTF8 fixes for settings window
 * UTF8 fixes for directory dialog
 * UTF8 fix for private chats in some locales (fr_FR for example)


Version 1.0.0 - Aug 18 2003 (INITIAL PUBLIC RELEASE)
----------------------------------------------------

 * Changed URL to the Nicotine homepage to http://nicotine.thegraveyard.org/
 * Added Alt-H accelerator to hide log


Version 1.0.0rc8 - Aug 18 2003
------------------------------

 * New MP3 header engine (shouldn't crash anymore, and should be faster)
 * Made the default handler for the http protocol more compatible (added
   quotes)


Version 1.0.0rc7 - Aug 17 2003
------------------------------

 * Fixed check privileges (thanks hednod)
 * Userlist context menu issues fixed
 * Several win32 fixups / custom-hacks made for upcoming win32 release


Version 1.0.0rc6 - Aug 16 2003
------------------------------

 * Merged PySoulSeek 1.2.4 core changes
  * Privileged users in userlist
  * Online notify


Version 1.0.0rc5 - Aug 16 2003
------------------------------

 * pytgtk-1.99.16 compatibility fix (thanks alexbk)


Version 1.0.0rc4 - Aug 16 2003
------------------------------

 * Fixed private-chat-shows-status-change-a-million-times
 * Fixed bug concerning GeoIP not being able to look up country code
 * Fixed email address in nicotine "binary"


Version 1.0.0rc3 - Aug 16 2003
------------------------------

 * Geographical blocking works for search results too
 * Geographical blocking settings now automatically uppercased
 * py2exe.bat bundled (used to create a "frozen" .exe on win32)
 * setup.iss bundled (used to create an installer using InnoSetup)
 * Tab menus now show page title instead of Page n
 * More win32 fixups
 * URLs now only respond to left click
 * User-info description field in settings now wraps
 * User-info image no longer writes temporary image file
 * Image data now encapsulated in imagedata.py


Version 1.0.0rc2 - Aug 13 2003
------------------------------

 * Fixed typo


Version 1.0.0rc1 - Aug 13 2003
------------------------------

 * Nasty Bug(tm) fixed
 * URL catcher fixup
 * Server banner is now shown
 * Hide log window menu item
 * Win32 fixups


Version 0.5.1 - Ayg 13 2003
---------------------------

 * URL catching
 * Bugfix: /ip no longer shows None
 * Bugfix: CheckUser would fuck up when disconnected
 * Fixed date for 0.5.0


Version 0.5.0 - Aug 13 2003
---------------------------

 * Geographical blocking using GeoIP (optional)
 * Userlist only sharing
 * Userlist values are reset after disconnect
 * Small bugfixes and typos
 * Instead of printing certain bugreports to the console,
   it now sends a private message to hyriand instead


Version 0.4.9 - Aug 11 2003
---------------------------

 * Python 2,2,0 compatibility
 * Python 2.3 deprecation warning fixed
 * Minor bugfixes (mainly in transfer lists, I hope they work)
 * Fixed the setup.py to install images
 * Added browse files to search results context menu
 * Added abort & remove file to downloads context menu
 * KB/GB/MB is now done at 1000 instead of 1024 (producing 0.99 MB instead
   of 1000 KB)


Version 0.4.8 - Aug 10 2003
---------------------------

 * Minor bugfixes and de-glitchifications


Version 0.4.7 - Aug 9 2003
--------------------------

 * New logo and icon (thanks (va)*10^3)
 * Generate profiler log when using nicotine --profile
   (profiler log will be saved as <configfile>.profile)


Version 0.4.6 - Aug 8 2003
--------------------------

 * Room user lists are filled again when reconnected
 * User is offline/away/online in private chats
 * Right-click on tab shows tab list
 * Auto-reply implemented
 * Added *1000 factor for auto-search interval *oops*


Version 0.4.5 - Aug 7 2003
--------------------------

 * Page Up / Down scrolls chats
 * // at the start of a chat line will "escape" the / used by commands
 * Evil typos corrected (tnx SmackleFunky)
 * Bugfixes
 * Search filter history


Version 0.4.4 - Aug 7 2003
--------------------------

 * Bugfixes
 * About dialogs


Version 0.4.3 - Aug 5 2003
--------------------------

 * Small bugfixes (sorting, UpdateColours, ChooseDir)


Version 0.4.2 - Aug 5 2003
--------------------------

 * First changelog entry.. Basically everything implemented :)
