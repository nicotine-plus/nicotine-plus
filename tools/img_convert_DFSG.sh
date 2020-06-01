#!/usr/bin/bash
#
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Script based on the work of Josselin Mouette <joss@debian.org>.
# You should have imagemagick and gnome-icon-theme installed to make it work.

COMPOSE='composite -gravity NorthEast -compose src-over'

# Base Nicotine+ icon
convert -background none -resize 32x32 files/icons/scalable/nicotine-plus.svg img/base.png

# Default icon in the notification area
$COMPOSE /usr/share/icons/Adwaita/16x16/legacy/emblem-default.png img/base.png img/trayicon_connect.png

# Notification area icon when disconnected
$COMPOSE /usr/share/icons/Adwaita/16x16/legacy/process-stop.png img/base.png img/trayicon_disconnect.png

# Notification area icon when the user is away
$COMPOSE /usr/share/icons/Adwaita/16x16/legacy/appointment-soon.png img/base.png img/trayicon_away.png

# Notification area icon when you get a message
$COMPOSE /usr/share/icons/Adwaita/16x16/legacy/starred.png img/base.png img/trayicon_msg.png

rm -f img/base.png
