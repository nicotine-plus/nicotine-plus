<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <object class="GtkBox" id="Main">
    <property name="visible">1</property>
    <property name="spacing">30</property>
    <property name="orientation">vertical</property>
    <child>
      <object class="GtkBox">
        <property name="visible">1</property>
        <property name="spacing">12</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkLabel">
            <property name="visible">1</property>
            <property name="halign">start</property>
            <property name="label" translatable="yes">User Interface</property>
            <attributes>
              <attribute name="weight" value="bold"/>
            </attributes>
          </object>
        </child>
        <child>
          <object class="GtkFlowBox">
            <property name="visible">1</property>
            <property name="homogeneous">1</property>
            <property name="column-spacing">12</property>
            <property name="row-spacing">12</property>
            <property name="min-children-per-line">1</property>
            <property name="max-children-per-line">3</property>
            <property name="selection-mode">none</property>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkCheckButton" id="DarkMode">
                    <property name="label" translatable="yes">Prefer dark mode</property>
                    <property name="visible">1</property>
                    <property name="tooltip_text" translatable="yes">Note that the operating system&apos;s theme may take precedence.</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox" id = "TraySettings">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="TrayiconCheck">
                        <property name="label" translatable="yes">Display tray icon</property>
                        <property name="visible">1</property>
                        <property name="use-underline">1</property>
                        <signal name="toggled" handler="on_toggle_tray" swapped="no"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <property name="label">    </property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkCheckButton" id="StartupHidden">
                        <property name="label" translatable="yes">Minimize to tray on startup</property>
                        <property name="visible">1</property>
                        <property name="use-underline">1</property>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkFlowBox">
            <property name="visible">1</property>
            <property name="homogeneous">1</property>
            <property name="column-spacing">24</property>
            <property name="row-spacing">12</property>
            <property name="max-children-per-line">2</property>
            <property name="selection-mode">none</property>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel">
                    <property name="visible">1</property>
                    <property name="label" translatable="yes">When closing Nicotine+:</property>
                    <property name="xalign">0</property>
                    <property name="mnemonic_widget">CloseAction</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkComboBoxText" id="CloseAction">
                    <property name="visible">1</property>
                    <items>
                      <item translatable="yes">Quit program</item>
                      <item translatable="yes">Show confirmation dialog</item>
                      <item translatable="yes">Run in the background</item>
                    </items>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
    <child>
      <object class="GtkBox">
        <property name="visible">1</property>
        <property name="spacing">18</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkBox">
            <property name="visible">1</property>
            <property name="spacing">12</property>
            <property name="orientation">vertical</property>
            <child>
              <object class="GtkLabel">
                <property name="visible">1</property>
                <property name="label" translatable="yes">Primary Tabs</property>
                <property name="xalign">0</property>
                <attributes>
                  <attribute name="weight" value="bold"/>
                </attributes>
              </object>
            </child>
            <child>
              <object class="GtkCheckButton" id="TabSelectPrevious">
                <property name="label" translatable="yes">Remember previous primary tab on startup</property>
                <property name="visible">1</property>
              </object>
            </child>
            <child>
              <object class="GtkFlowBox">
                <property name="visible">1</property>
                <property name="column-spacing">12</property>
                <property name="row-spacing">12</property>
                <property name="max-children-per-line">2</property>
                <property name="selection-mode">none</property>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkLabel" id="MainTabsLabel">
                        <property name="visible">1</property>
                        <property name="xalign">0</property>
                        <property name="label" translatable="yes">Tab bar position:</property>
                        <property name="mnemonic_widget">MainPosition</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkComboBoxText" id="MainPosition">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkBox">
            <property name="visible">1</property>
            <property name="spacing">18</property>
            <property name="orientation">vertical</property>
            <child>
              <object class="GtkLabel">
                <property name="visible">1</property>
                <property name="label" translatable="yes">Visible primary tabs:</property>
                <property name="xalign">0</property>
                <property name="mnemonic_widget">EnableSearchTab</property>
              </object>
            </child>
            <child>
              <object class="GtkFlowBox">
                <property name="visible">1</property>
                <property name="homogeneous">1</property>
                <property name="column-spacing">18</property>
                <property name="row-spacing">12</property>
                <property name="min-children-per-line">1</property>
                <property name="max-children-per-line">3</property>
                <property name="selection-mode">none</property>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="EnableSearchTab">
                        <property name="label" translatable="yes">Search Files</property>
                        <property name="visible">1</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="EnableDownloadsTab">
                        <property name="label" translatable="yes">Downloads</property>
                        <property name="visible">1</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="EnableUploadsTab">
                        <property name="label" translatable="yes">Uploads</property>
                        <property name="visible">1</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="EnableUserBrowseTab">
                        <property name="label" translatable="yes">Browse Shares</property>
                        <property name="visible">1</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="EnableUserInfoTab">
                        <property name="label" translatable="yes">User Info</property>
                        <property name="visible">1</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="EnablePrivateTab">
                        <property name="label" translatable="yes">Private Chat</property>
                        <property name="visible">1</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="EnableUserListTab">
                        <property name="label" translatable="yes">Buddies</property>
                        <property name="visible">1</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="EnableChatroomsTab">
                        <property name="label" translatable="yes">Chat Rooms</property>
                        <property name="visible">1</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkCheckButton" id="EnableInterestsTab">
                        <property name="label" translatable="yes">Interests</property>
                        <property name="visible">1</property>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
    <child>
      <object class="GtkBox">
        <property name="visible">1</property>
        <property name="spacing">30</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkBox">
            <property name="visible">1</property>
            <property name="spacing">12</property>
            <property name="orientation">vertical</property>
            <child>
              <object class="GtkLabel">
                <property name="visible">1</property>
                <property name="label" translatable="yes">Lists</property>
                <property name="xalign">0</property>
                <attributes>
                  <attribute name="weight" value="bold"/>
                </attributes>
              </object>
            </child>
            <child>
              <object class="GtkCheckButton" id="FilePathTooltips">
                <property name="label" translatable="yes">Show file path tooltips in file list views</property>
                <property name="visible">1</property>
                <property name="use-underline">1</property>
              </object>
            </child>
            <child>
              <object class="GtkCheckButton" id="ReverseFilePaths">
                <property name="label" translatable="yes">Show reverse file paths in search and transfer views (requires a restart)</property>
                <property name="visible">1</property>
                <property name="use-underline">1</property>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkFlowBox">
            <property name="visible">1</property>
            <property name="row-spacing">12</property>
            <property name="column-spacing">12</property>
            <property name="max-children-per-line">2</property>
            <property name="selection-mode">none</property>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel">
                    <property name="visible">1</property>
                    <property name="label" translatable="yes">Double-click action for downloads:</property>
                    <property name="xalign">0</property>
                    <property name="mnemonic_widget">DownloadDoubleClick</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkComboBoxText" id="DownloadDoubleClick">
                    <property name="visible">1</property>
                    <items>
                      <item>Nothing</item>
                      <item>Send to Player</item>
                      <item>Open in File Manager</item>
                      <item>Search</item>
                      <item>Pause</item>
                      <item>Clear</item>
                      <item>Resume</item>
                      <item>Browse Folder</item>
                    </items>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel">
                    <property name="visible">1</property>
                    <property name="label" translatable="yes">Double-click action for uploads:</property>
                    <property name="xalign">0</property>
                    <property name="mnemonic_widget">UploadDoubleClick</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkComboBoxText" id="UploadDoubleClick">
                    <property name="visible">1</property>
                    <items>
                      <item>Nothing</item>
                      <item>Send to Player</item>
                      <item>Open in File Manager</item>
                      <item>Search</item>
                      <item>Abort</item>
                      <item>Clear</item>
                      <item>Retry</item>
                      <item>Browse Folder</item>
                    </items>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkFlowBox">
            <property name="visible">1</property>
            <property name="homogeneous">1</property>
            <property name="column-spacing">12</property>
            <property name="row-spacing">12</property>
            <property name="min-children-per-line">1</property>
            <property name="max-children-per-line">2</property>
            <property name="selection-mode">none</property>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">List text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickImmediate</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickImmediate">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryImmediate">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultImmediate">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Queued search result text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickQueue</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickQueue">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryQueue">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultQueue">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
    <child>
      <object class="GtkBox">
        <property name="visible">1</property>
        <property name="spacing">30</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkBox">
            <property name="visible">1</property>
            <property name="spacing">12</property>
            <property name="orientation">vertical</property>
            <child>
              <object class="GtkLabel">
                <property name="visible">1</property>
                <property name="label" translatable="yes">Secondary Tabs</property>
                <property name="xalign">0</property>
                <attributes>
                  <attribute name="weight" value="bold"/>
                </attributes>
              </object>
            </child>
            <child>
              <object class="GtkCheckButton" id="TabClosers">
                <property name="label" translatable="yes">Close-buttons on secondary tabs</property>
                <property name="visible">1</property>
              </object>
            </child>
            <child>
              <object class="GtkCheckButton" id="TabStatusIcons">
                <property name="label" translatable="yes">Tabs show user status icons instead of status text</property>
                <property name="visible">1</property>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkFlowBox">
            <property name="visible">1</property>
            <property name="column-spacing">12</property>
            <property name="row-spacing">12</property>
            <property name="max-children-per-line">2</property>
            <property name="selection-mode">none</property>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel" id="ChatRoomsLabel">
                    <property name="visible">1</property>
                    <property name="xalign">0</property>
                    <property name="label" translatable="yes">Chat room tab bar position:</property>
                    <property name="mnemonic_widget">ChatRoomsPosition</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkComboBoxText" id="ChatRoomsPosition">
                    <property name="visible">1</property>
                    <property name="hexpand">1</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel" id="PrivateChatLabel">
                    <property name="visible">1</property>
                    <property name="xalign">0</property>
                    <property name="label" translatable="yes">Private chat tab bar position:</property>
                    <property name="mnemonic_widget">PrivateChatPosition</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkComboBoxText" id="PrivateChatPosition">
                    <property name="visible">1</property>
                    <property name="hexpand">1</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel" id="SearchLabel">
                    <property name="visible">1</property>
                    <property name="xalign">0</property>
                    <property name="label" translatable="yes">Search tab bar position:</property>
                    <property name="mnemonic_widget">SearchPosition</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkComboBoxText" id="SearchPosition">
                    <property name="visible">1</property>
                    <property name="hexpand">1</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel" id="UserInfoLabel">
                    <property name="visible">1</property>
                    <property name="xalign">0</property>
                    <property name="label" translatable="yes">User info tab bar position:</property>
                    <property name="mnemonic_widget">UserInfoPosition</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkComboBoxText" id="UserInfoPosition">
                    <property name="visible">1</property>
                    <property name="hexpand">1</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel" id="UserBrowseLabel">
                    <property name="visible">1</property>
                    <property name="xalign">0</property>
                    <property name="label" translatable="yes">User browse tab bar position:</property>
                    <property name="mnemonic_widget">UserBrowsePosition</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkComboBoxText" id="UserBrowsePosition">
                    <property name="visible">1</property>
                    <property name="hexpand">1</property>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
    <child>
      <object class="GtkBox">
        <property name="visible">1</property>
        <property name="spacing">30</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkBox">
            <property name="visible">1</property>
            <property name="spacing">12</property>
            <property name="orientation">vertical</property>
            <child>
              <object class="GtkLabel">
                <property name="visible">1</property>
                <property name="xalign">0</property>
                <property name="margin-top">12</property>
                <property name="label" translatable="yes">Chats</property>
                <property name="wrap">1</property>
                <attributes>
                  <attribute name="weight" value="bold"/>
                </attributes>
              </object>
            </child>
            <child>
              <object class="GtkCheckButton" id="UsernameHotspots">
                <property name="label" translatable="yes">Colored and clickable usernames</property>
                <property name="visible">1</property>
                <property name="use-underline">1</property>
                <signal name="toggled" handler="on_username_hotspots_toggled" swapped="no"/>
              </object>
            </child>
            <child>
              <object class="GtkFlowBox">
                <property name="visible">1</property>
                <property name="column-spacing">12</property>
                <property name="row-spacing">12</property>
                <property name="max-children-per-line">2</property>
                <property name="selection-mode">none</property>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Chat username appearance:</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">UsernameStyle</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkComboBoxText" id="UsernameStyle">
                        <property name="visible">1</property>
                        <signal name="changed" handler="on_colors_changed"/>
                        <items>
                          <item id="bold" translatable="yes">bold</item>
                          <item id="italic" translatable="yes">italic</item>
                          <item id="underline" translatable="yes">underline</item>
                          <item id="normal" translatable="yes">normal</item>
                        </items>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkFlowBox">
            <property name="visible">1</property>
            <property name="homogeneous">1</property>
            <property name="column-spacing">12</property>
            <property name="row-spacing">12</property>
            <property name="min-children-per-line">1</property>
            <property name="max-children-per-line">2</property>
            <property name="selection-mode">none</property>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Remote text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickRemote</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickRemote">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryRemote">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultRemote">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Local text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickLocal</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickLocal">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryLocal">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultLocal">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">/me action text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickMe</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickMe">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryMe">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultMe">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Highlighted text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickHighlight</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickHighlight">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryHighlight">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultHighlight">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">URL link text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickURL</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickURL">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryURL">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultURL">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Online text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickOnline</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickOnline">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryOnline">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultOnline">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Offline text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickOffline</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickOffline">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryOffline">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultOffline">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Away text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickAway</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickAway">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryAway">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultAway">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
    <child>
      <object class="GtkBox">
        <property name="visible">1</property>
        <property name="spacing">12</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkLabel">
            <property name="visible">1</property>
            <property name="xalign">0</property>
            <property name="label" translatable="yes">Text Entries</property>
            <property name="wrap">1</property>
            <attributes>
              <attribute name="weight" value="bold"/>
            </attributes>
          </object>
        </child>
        <child>
          <object class="GtkFlowBox">
            <property name="visible">1</property>
            <property name="homogeneous">1</property>
            <property name="column-spacing">12</property>
            <property name="row-spacing">12</property>
            <property name="min-children-per-line">1</property>
            <property name="max-children-per-line">2</property>
            <property name="selection-mode">none</property>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Text entry background color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickBackground</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickBackground">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryBackground">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultBackground">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Text entry text color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickInput</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickInput">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryInput">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultInput">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
    <child>
      <object class="GtkBox">
        <property name="visible">1</property>
        <property name="spacing">12</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkLabel">
            <property name="visible">1</property>
            <property name="label" translatable="yes">Tab Labels</property>
            <property name="xalign">0</property>
            <attributes>
              <attribute name="weight" value="bold"/>
            </attributes>
          </object>
        </child>
        <child>
          <object class="GtkCheckButton" id="NotificationTabColors">
            <property name="visible">1</property>
            <property name="label" translatable="yes">Notification changes the tab&apos;s text color</property>
            <signal name="toggled" handler="on_tab_notification_color_toggled" swapped="no"/>
          </object>
        </child>
        <child>
          <object class="GtkFlowBox">
            <property name="visible">1</property>
            <property name="homogeneous">1</property>
            <property name="column-spacing">12</property>
            <property name="row-spacing">12</property>
            <property name="min-children-per-line">1</property>
            <property name="max-children-per-line">2</property>
            <property name="selection-mode">none</property>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Regular tab label color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickRegularTab</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickRegularTab">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryRegularTab">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultRegularTab">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Changed tab label color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickChangedTab</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickChangedTab">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryChangedTab">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultChangedTab">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Highlighted tab label color:</property>
                        <property name="hexpand">1</property>
                        <property name="xalign">0</property>
                        <property name="wrap">1</property>
                        <property name="mnemonic_widget">PickHighlightTab</property>
                      </object>
                    </child>
                    <child>
                      <object class="GtkColorButton" id="PickHighlightTab">
                        <property name="visible">1</property>
                        <signal name="color-set" handler="on_color_set"/>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkEntry" id="EntryHighlightTab">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="width-chars">16</property>
                        <signal name="changed" handler="on_colors_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultHighlightTab">
                        <property name="visible">1</property>
                        <property name="halign">start</property>
                        <signal name="clicked" handler="on_default_color"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
    <child>
      <object class="GtkBox">
        <property name="visible">1</property>
        <property name="spacing">12</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkLabel">
            <property name="visible">1</property>
            <property name="halign">start</property>
            <property name="label" translatable="yes">Fonts</property>
            <attributes>
              <attribute name="weight" value="bold"/>
            </attributes>
          </object>
        </child>
        <child>
          <object class="GtkFlowBox">
            <property name="visible">1</property>
            <property name="column-spacing">12</property>
            <property name="row-spacing">12</property>
            <property name="max-children-per-line">2</property>
            <property name="selection-mode">none</property>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel">
                    <property name="visible">1</property>
                    <property name="label" translatable="yes">Global font:</property>
                    <property name="xalign">0</property>
                    <property name="wrap">1</property>
                    <property name="mnemonic_widget">SelectGlobalFont</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkFontButton" id="SelectGlobalFont">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="font">Sans 12</property>
                        <property name="width-request">250</property>
                        <signal name="font-set" handler="on_fonts_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultGlobalFont">
                        <property name="visible">1</property>
                        <signal name="clicked" handler="on_default_font"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel">
                    <property name="visible">1</property>
                    <property name="label" translatable="yes">Chat font:</property>
                    <property name="xalign">0</property>
                    <property name="wrap">1</property>
                    <property name="mnemonic_widget">SelectChatFont</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkFontButton" id="SelectChatFont">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="font">Sans 12</property>
                        <property name="width-request">250</property>
                        <signal name="font-set" handler="on_fonts_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultChatFont">
                        <property name="visible">1</property>
                        <signal name="clicked" handler="on_default_font"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel">
                    <property name="visible">1</property>
                    <property name="label" translatable="yes">List font:</property>
                    <property name="xalign">0</property>
                    <property name="wrap">1</property>
                    <property name="mnemonic_widget">SelectListFont</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkFontButton" id="SelectListFont">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="font">Sans 12</property>
                        <property name="width-request">250</property>
                        <signal name="font-set" handler="on_fonts_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultListFont">
                        <property name="visible">1</property>
                        <signal name="clicked" handler="on_default_font"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel">
                    <property name="visible">1</property>
                    <property name="label" translatable="yes">Transfers font:</property>
                    <property name="xalign">0</property>
                    <property name="wrap">1</property>
                    <property name="mnemonic_widget">SelectTransfersFont</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkFontButton" id="SelectTransfersFont">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="font">Sans 12</property>
                        <property name="width-request">250</property>
                        <signal name="font-set" handler="on_fonts_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultTransfersFont">
                        <property name="visible">1</property>
                        <signal name="clicked" handler="on_default_font"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel">
                    <property name="visible">1</property>
                    <property name="label" translatable="yes">Search font:</property>
                    <property name="xalign">0</property>
                    <property name="wrap">1</property>
                    <property name="mnemonic_widget">SelectSearchFont</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkFontButton" id="SelectSearchFont">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="font">Sans 12</property>
                        <property name="width-request">250</property>
                        <signal name="font-set" handler="on_fonts_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultSearchFont">
                        <property name="visible">1</property>
                        <signal name="clicked" handler="on_default_font"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkLabel">
                    <property name="visible">1</property>
                    <property name="label" translatable="yes">Browse font:</property>
                    <property name="xalign">0</property>
                    <property name="wrap">1</property>
                    <property name="mnemonic_widget">SelectBrowserFont</property>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFlowBoxChild">
                <property name="visible">1</property>
                <property name="focusable">0</property>
                <child>
                  <object class="GtkBox">
                    <property name="visible">1</property>
                    <property name="spacing">12</property>
                    <child>
                      <object class="GtkFontButton" id="SelectBrowserFont">
                        <property name="visible">1</property>
                        <property name="hexpand">1</property>
                        <property name="font">Sans 12</property>
                        <property name="width-request">250</property>
                        <signal name="font-set" handler="on_fonts_changed"/>
                      </object>
                    </child>
                    <child>
                      <object class="GtkButton" id="DefaultBrowserFont">
                        <property name="visible">1</property>
                        <signal name="clicked" handler="on_default_font"/>
                        <child>
                          <object class="GtkBox">
                            <property name="visible">1</property>
                            <property name="spacing">6</property>
                            <child>
                              <object class="GtkImage">
                                <property name="visible">1</property>
                                <property name="icon-name">view-refresh-symbolic</property>
                              </object>
                            </child>
                            <child>
                              <object class="GtkLabel">
                                <property name="visible">1</property>
                                <property name="label" translatable="yes">Default</property>
                                <property name="use-underline">1</property>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
    <child>
      <object class="GtkBox">
        <property name="visible">1</property>
        <property name="spacing">12</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkLabel">
            <property name="visible">1</property>
            <property name="label" translatable="yes">Icons</property>
            <property name="xalign">0</property>
            <attributes>
              <attribute name="weight" value="bold"/>
            </attributes>
          </object>
        </child>
        <child>
          <object class="GtkBox">
            <property name="visible">1</property>
            <property name="spacing">18</property>
            <property name="orientation">vertical</property>
            <child>
              <object class="GtkFlowBox">
                <property name="visible">1</property>
                <property name="homogeneous">1</property>
                <property name="column-spacing">12</property>
                <property name="row-spacing">12</property>
                <property name="max-children-per-line">2</property>
                <property name="selection-mode">none</property>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkLabel">
                        <property name="visible">1</property>
                        <property name="label" translatable="yes">Icon theme folder (requires restart):</property>
                        <property name="xalign">0</property>
                        <property name="mnemonic_widget">ThemeDir</property>
                      </object>
                    </child>
                  </object>
                </child>
                <child>
                  <object class="GtkFlowBoxChild">
                    <property name="visible">1</property>
                    <property name="focusable">0</property>
                    <child>
                      <object class="GtkBox">
                        <property name="visible">1</property>
                        <property name="spacing">12</property>
                        <child>
                          <object class="GtkButton" id="ThemeDir">
                            <property name="visible">1</property>
                            <property name="hexpand">1</property>
                            <property name="width-request">160</property>
                          </object>
                        </child>
                        <child>
                          <object class="GtkButton" id="DefaultTheme">
                            <property name="visible">1</property>
                            <signal name="clicked" handler="on_default_theme" swapped="no"/>
                            <child>
                              <object class="GtkBox">
                                <property name="visible">1</property>
                                <property name="spacing">6</property>
                                <child>
                                  <object class="GtkImage">
                                    <property name="visible">1</property>
                                    <property name="icon-name">edit-clear-symbolic</property>
                                  </object>
                                </child>
                                <child>
                                  <object class="GtkLabel">
                                    <property name="visible">1</property>
                                    <property name="label" translatable="yes">Clear</property>
                                    <property name="use-underline">1</property>
                                  </object>
                                </child>
                              </object>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                </child>
              </object>
            </child>
            <child>
              <object class="GtkFrame">
                <property name="visible">1</property>
                <child>
                  <object class="GtkFlowBox" id="IconView">
                    <property name="visible">1</property>
                    <property name="column-spacing">24</property>
                    <property name="row-spacing">24</property>
                    <property name="margin-start">24</property>
                    <property name="margin-end">24</property>
                    <property name="margin-top">24</property>
                    <property name="margin-bottom">24</property>
                    <property name="selection-mode">none</property>
                  </object>
                </child>
                <style>
                  <class name="view"/>
                </style>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>
