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
                RB.RhythmDBEntryType.__init__(
                                self,
                                name='AmpacheEntryType',
                                save_to_disk=False)

        def can_sync_metadata(self, entry):
                return True

        def sync_metadata(self, entry, changes):
                return


class Ampache(GObject.Object, Peas.Activatable):
        __gtype_name__ = 'AmpachePlugin'
        object = GObject.property(type=GObject.Object)

        def do_activate(self):
                shell = self.object
                db = shell.props.db

                # load icon
                theme = Gtk.IconTheme.get_default()
                what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
                icon = GdkPixbuf.Pixbuf.new_from_file_at_size(rb.find_plugin_file(self, 'ampache.ico'), width, height)

                # fetch plugin settings
                settings = Gio.Settings("org.gnome.rhythmbox.plugins.ampache")

                # register AmpacheEntryType
                self.__entry_type = AmpacheEntryType()
                db.register_entry_type(self.__entry_type)

                # create AmpacheBrowser source
                self.__source = GObject.new(
                        AmpacheBrowser,
                        shell=shell,
                        entry_type=self.__entry_type,
                        pixbuf=icon,
                        plugin=self,
                        settings=settings.get_child("source"),
                        name=_("Ampache")
                )

                # assign AmpacheEntryType to AmpacheBrowser source
                shell.register_entry_type_for_source(
                        self.__source,
                        self.__entry_type)

                # insert AmpacheBrowser source into Shared group
                shell.append_display_page(
                        self.__source,
                        RB.DisplayPageGroup.get_by_id("shared"))

                # add action RefetchAmpache and assign callback refetch_ampache
                action = Gtk.Action('RefetchAmpache',
                                    _('_Refetch Ampache Library'),
                                    _('Update the local ampache library'),
                                    '')
                action.connect('activate', self.refetch_ampache)

                self.__action_group = Gtk.ActionGroup('AmpacheActions')
                self.__action_group.add_action(action)

                ui_manager = shell.props.ui_manager

                ui_manager.insert_action_group(self.__action_group, -1)

                # add context menu
                self.__ui_id = ui_manager.add_ui_from_string(popup_ui)
                ui_manager.ensure_update()

        def do_deactivate(self):
                shell = self.object

                ui_manager = shell.props.ui_manager

                # remove context menu
                ui_manager.remove_ui(self.__ui_id)

                # remove action group
                ui_manager.remove_action_group(self.__action_group)
                self.__action_group = None

#                self.db.entry_delete_by_type(self.__entry_type)
#                self.db.commit()
#                self.db = None

                self.__entry_type = None

                # delete AmpacheBrowser source
                self.__source.delete_thyself()
                self.__source = None

        def refetch_ampache(self, widget):
                shell = self.object

#                db = shell.props.db
#                db.entry_delete_by_type(self.__entry_type)
#                db.commit()

                self.__source.update(True)
