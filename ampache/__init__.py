# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
#
#
# Copyright (C) 2008 Seva <seva@sevatech.com>
#
# Portions from Magnatune Rhythmbox plugin
# Copyright (C) 2006 Adam Zimmerman <adam_zimmerman@sfu.ca>
# Copyright (C) 2006 James Livingston  <doclivingston@gmail.com>
#
# Portions from 'git clone http://quickplay.isfound.at'
# Copyright (C) 2008 Kevin James Purdy irc://irc.freenode.org/purdyk,isnick
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA.

import rhythmdb, rb
import gobject

from AmpacheConfig import AmpacheConfig
from AmpacheConfigDialog import AmpacheConfigDialog
from AmpacheBrowser import AmpacheBrowser

class Ampache(rb.Plugin):
	def __init__(self):
		print "INFO: ampache plugin init"

		self.config = AmpacheConfig()

		rb.Plugin.__init__(self)

	def activate(self, shell):
		print "INFO: activating ampache plugin"

		self.db = shell.props.db

		self.entry_type = self.db.entry_register_type("AmpacheEntryType")
		self.entry_type.can_sync_metadata = True
		self.entry_type.sync_metadata = None
		self.entry_type.category = rhythmdb.ENTRY_STREAM

		group = rb.rb_source_group_get_by_name(self.config.get("group"))
		if not group:
			group = rb.rb_source_group_register (
				"ampache",
				self.config.get("group"),
				rb.SOURCE_GROUP_CATEGORY_FIXED,
			)


		self.source = gobject.new (
			AmpacheBrowser,
 			entry_type=self.entry_type,
			source_group=group,
 			name=self.config.get("name"),
 			shell=shell,
		)

		self.config.set("icon_filename", self.find_file(self.config.get("icon")))
		self.source.activate(self.config)

		shell.register_entry_type_for_source(self.source, self.entry_type)
		shell.append_source(self.source, None)

	def deactivate(self, shell):
		print "INFO: deactivating ampache plugin"

		self.db.entry_delete_by_type(self.entry_type)

                self.db.commit()
                self.db = None

                self.entry_type = None

                self.source.delete_thyself()
                self.source = None

	def create_configure_dialog(self):
		print "INFO: creating configure dialog"

		glade_file = self.find_file("ampache-prefs.glade")

		if glade_file:
			dialog = AmpacheConfigDialog(glade_file, self.config).get_dialog()

		if dialog:
			return dialog
		else:
			print "ERROR: couldn't create configure dialog"
			return None
