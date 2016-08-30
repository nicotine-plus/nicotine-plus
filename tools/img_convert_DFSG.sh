#!/usr/bin/bash
#
# COPYRIGHT (c) 2016 Michael Labouebe <gfarmerfr@free.fr>
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
# You should have imagemagick and gnome-icon-theme insatlled to make it work.

COMPOSE='composite -gravity NorthEast -compose src-over'

# Base Nicotine+ icon
convert -resize 16x16 img/n.png img/base.png

# Default icon in the notification area
$COMPOSE /usr/share/icons/gnome/8x8/emblems/emblem-default.png img/base.png img/trayicon_connect.png

# Notification area icon when disconnected
convert -resize 8x8 /usr/share/icons/gnome/16x16/actions/process-stop.png img/net_ko.png
$COMPOSE img/net_ko.png img/base.png img/trayicon_disconnect.png
rm -f img/net_ko.png

# Notification area icon when the user is away
convert -resize 8x8 /usr/share/icons/gnome/16x16/status/appointment-soon.png img/clock.png
$COMPOSE img/clock.png img/base.png img/trayicon_away.png
rm -f img/clock.png

# Notification area icon when you get a message
convert -resize 9x9 -alpha extract -alpha shape -background blue /usr/share/icons/gnome/16x16/status/starred.png img/msg.png
$COMPOSE img/msg.png img/base.png img/trayicon_msg.png
rm -f img/msg.png

rm -f img/base.png
