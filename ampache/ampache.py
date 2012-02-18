# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
# vim: expandtab shiftwidth=8 softtabstop=8 tabstop=8

# todo:
# - do_deactivate: entry_delete_by_type() results in entry->refcount > 0
#   assertion and Segmentation Fault

import rb
from gi.repository import RB
from gi.repository import GObject, Peas, Gtk, Gio, GdkPixbuf

from AmpacheConfigDialog import AmpacheConfigDialog
from AmpacheBrowser import AmpacheBrowser

popup_ui = """
<ui>
  <popup name="AmpacheSourceViewPopup">
    <menuitem name="RefetchAmpacheLibrary" action="RefetchAmpache"/>
  </popup>
</ui>
"""

class AmpacheEntryType(RB.RhythmDBEntryType):
        def __init__(self):
                RB.RhythmDBEntryType.__init__(self, name='AmpacheEntryType')

        def can_sync_metadata(self, entry):
                return True

        def sync_metadata(self, entry, changes):
                return


class Ampache(GObject.Object, Peas.Activatable):
        __gtype_name__ = 'AmpachePlugin'
        object = GObject.property(type=GObject.Object)

        def do_activate(self):
                shell = self.object
                self.db = shell.props.db

                self.entry_type = AmpacheEntryType()
                self.db.register_entry_type(self.entry_type)

                theme = Gtk.IconTheme.get_default()
                what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
                icon = GdkPixbuf.Pixbuf.new_from_file_at_size(rb.find_plugin_file(self, 'ampache.ico'), width, height)

                group = RB.DisplayPageGroup.get_by_id("shared")
                settings = Gio.Settings("org.gnome.rhythmbox.plugins.ampache")

                self.source = GObject.new(
                        AmpacheBrowser,
                        shell=shell,
                        entry_type=self.entry_type,
                        pixbuf=icon,
                        plugin=self,
                        settings=settings.get_child("source"),
                        name=_("Ampache")
                )

                shell.register_entry_type_for_source(self.source, self.entry_type)
                shell.append_display_page(self.source, group)

                manager = shell.props.ui_manager
                self.action_group = Gtk.ActionGroup('AmpacheActions')
                action = Gtk.Action('RefetchAmpache',
                                    _('_Refetch Ampache Library'),
                                    _('Update the local ampache library'),
                                    '')

                action.connect('activate', self.refetch_ampache)
                self.action_group.add_action(action)
                manager.insert_action_group(self.action_group, -1)
                self.ui_id = manager.add_ui_from_string(popup_ui)
                manager.ensure_update()

        def do_deactivate(self):
                shell = self.object

                manager = shell.props.ui_manager
                manager.remove_ui(self.ui_id)
                manager.remove_action_group(self.action_group)
                self.action_group = None

#                self.db.entry_delete_by_type(self.entry_type)
#                self.db.commit()
                self.db = None

                self.entry_type = None

                self.source.delete_thyself()
                self.source = None

        def refetch_ampache(self, widget):
                shell = self.object
                self.source.download_catalog()
