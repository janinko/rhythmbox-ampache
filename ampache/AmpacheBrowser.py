# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
# vim: expandtab shiftwidth=8 softtabstop=8 tabstop=8

from gi.repository import RB
from gi.repository import GObject, Gtk, Gio, GLib

import time
from time import mktime
from datetime import datetime
import re
import hashlib
import os
import os.path
import sys

import xml.sax, xml.sax.handler

class HandshakeHandler(xml.sax.handler.ContentHandler):
      def __init__(self, handshake):
            xml.sax.handler.ContentHandler.__init__(self)
            self.__handshake = handshake

      def startElement(self, name, attrs):
            self.__text = ''

      def endElement(self, name):
            self.__handshake[name] = self.__text

      def characters(self, content):
            self.__text = self.__text + content

class SongsHandler(xml.sax.handler.ContentHandler):
        def __init__(self, db, entry_type, albumart):
                xml.sax.handler.ContentHandler.__init__(self)
                self.__db = db
                self.__entry_type = entry_type
                self.__albumart = albumart
                self.__clear()

        def startElement(self, name, attrs):
                if name == 'song':
                        self.__id = attrs['id']
                self.__text = ''

        def endElement(self, name):
                if name == 'song':
                        try:
                                # add the track to the source if it doesn't exist
                                entry = self.__db.entry_lookup_by_location(str(self.__url))
                                if entry == None:
                                        entry = RB.RhythmDBEntry.new(self.__db, self.__entry_type, str(self.__url))

                                if self.__artist != '':
                                        self.__db.entry_set(entry, RB.RhythmDBPropType.ARTIST, str(self.__artist))
                                if self.__album != '':
                                        self.__db.entry_set(entry, RB.RhythmDBPropType.ALBUM, str(self.__album))
                                if self.__title != '':
                                        self.__db.entry_set(entry, RB.RhythmDBPropType.TITLE, str(self.__title))
                                if self.__tag != '':
                                        self.__db.entry_set(entry, RB.RhythmDBPropType.GENRE, str(self.__tag))
                                self.__db.entry_set(entry, RB.RhythmDBPropType.TRACK_NUMBER, self.__track)
                                self.__db.entry_set(entry, RB.RhythmDBPropType.DURATION, self.__time)
                                self.__db.entry_set(entry, RB.RhythmDBPropType.FILE_SIZE, self.__size)
                                self.__db.entry_set(entry, RB.RhythmDBPropType.RATING, self.__rating)
                                self.__db.commit()

                                self.__albumart[str(self.__artist) + str(self.__album)] = str(self.__art)

                        except Exception,e: # This happens on duplicate uris being added
                                sys.excepthook(*sys.exc_info())
                                print("Couldn't add %s - %s" % (self.__artist, self.__title), e)

                        self.__clear()

                elif name == 'url':
                        self.__url = self.__text
                elif name == 'artist':
                        self.__artist = self.__text.encode('utf-8')
                elif name == 'album':
                        self.__album = self.__text.encode('utf-8')
                elif name == 'title':
                        self.__title = self.__text.encode('utf-8')
                elif name == 'tag':
                        self.__tag = self.__text
                elif name == 'track':
                        self.__track = int(self.__text)
                elif name == 'time':
                        self.__time = int(self.__text)
                elif name == 'size':
                        self.__size = int(self.__text)
                elif name == 'rating':
                        self.__rating = int(self.__text)
                elif name == 'art':
                        self.__art = self.__text
                else:
                        self.__null = self.__text

        def characters(self, content):
                self.__text = self.__text + content

        def __clear(self):
                self.__id = 0
                self.__url = ''
                self.__artist = ''
                self.__album = ''
                self.__title = ''
                self.__tag = ''
                self.__track = ''
                self.__time = 0
                self.__size = 0
                self.__rating = 0
                self.__art = ''

class AmpacheBrowser(RB.BrowserSource):

        def __init__(self):
                RB.BrowserSource.__init__(self, name=_("Ampache"))

                self.__limit = 5000

                self.__cache_filename = os.path.join(RB.user_cache_dir(), 'ampache', 'song_cache.xml')
                self.settings = Gio.Settings('org.gnome.rhythmbox.plugins.ampache')
                self.__albumart = {}

                self.__text = None
                self.__progress_text = None
                self.__progress = 1

                self.__activate = False

        def do_show_popup(self):
                if self.__activate:
                        self.__popup.popup(None, None, None, None, 3, Gtk.get_current_event_time())

        def download_catalog(self):

                def cache_saved_cb(stream, result, data):
                        try:
                                size = stream.write_finish(result)
                        except Exception, e:
                                print("error writing file: %s" % (self.__cache_filename))
                                sys.excepthook(*sys.exc_info())

                        # close stream
                        stream.close(Gio.Cancellable())

                        # change modification time to update time
                        update_time = int(mktime(self.__handshake_update.timetuple()))
                        os.utime(self.__cache_filename, (update_time, update_time))
                def open_append_cb(file, result, data):
                        try:
                                stream = file.append_to_finish(result)
                        except Exception, e:
                                print("error opening file for writing %s" % (self.__cache_filename))
                                sys.excepthook(*sys.exc_info())

                        stream.write_async(
                                data.encode('utf-8'),
                                GLib.PRIORITY_DEFAULT,
                                Gio.Cancellable(),
                                cache_saved_cb,
                                None)
                        print("write to cache file: %s" % (self.__cache_filename))

                def songs_downloaded_cb(file, result, data):
                        try:
                                (ok, contents, etag) = file.load_contents_finish(result)
                        except Exception, e:
                                emsg = _('Catalog response: %s') % e
                                edlg = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, emsg)
                                edlg.run()
                                edlg.destroy()
                                self.__activate = False
                                return

                        offset = data[0] + self.__limit

                        self.__progress = float(offset) / float(self.__handshake_songs)
                        self.notify_status_changed()

                        if offset < self.__handshake_songs:
                                # download subsequent chunk of songs
                                download_songs_chunk(offset, data[1], data[2])
                        else:
                                self.__text = ''
                                self.__progress = 1
                                self.notify_status_changed()

                        try:
                                data[1].feed(contents)
                                data[1].reset()
                        except xml.sax.SAXParseException, e:
                                print("error parsing songs: %s" % e)

                        # remove enveloping <?xml> and <root> tags
                        # as needed to regenerate one full .xml
                        lines = contents.decode('utf-8').splitlines(True)
                        if data[0] > 0:
                                del lines[:2]
                        if offset < self.__handshake_songs:
                                del lines[-2:]

                        contents = ''.join(lines)

                        data[2].append_to_async(
                                Gio.FileCreateFlags.NONE,
                                GLib.PRIORITY_DEFAULT,
                                Gio.Cancellable(),
                                open_append_cb,
                                contents)
                        print("append to cache file: %s" % (self.__cache_filename))

                def download_songs_chunk(offset, parser, cache_file):
                        ampache_server_uri = '%s/server/xml.server.php?action=songs&auth=%s&offset=%s&limit=%s' % (self.settings['url'], self.__handshake_auth, offset, self.__limit)
                        ampache_server_file = Gio.file_new_for_uri(ampache_server_uri)
                        ampache_server_file.load_contents_async(
                                Gio.Cancellable(),
                                songs_downloaded_cb,
                                (offset, parser, cache_file))
                        print("downloading songs: %s" % (ampache_server_uri))

                self.__text = 'Download songs from Ampache server...'
                self.notify_status_changed()

                # instantiate songs parser
                parser = xml.sax.make_parser()
                parser.setContentHandler(SongsHandler(self.__db, self.__entry_type, self.__albumart))

                cache_file = Gio.file_new_for_path(self.__cache_filename)

                # delete cache file if available
                try:
                        cache_file.delete(Gio.Cancellable())
                except Exception, e:
                        pass

                # delete all ampache songs from database
                self.__db.entry_delete_by_type(self.__entry_type)

                # download first chunk of songs
                download_songs_chunk(0, parser, cache_file)

        def update_catalog(self):

                def handshake_cb(file, result, parser):
                        try:
                                (ok, contents, etag) = file.load_contents_finish(result)
                        except Exception, e:
                                emsg = _('Handshake response: %s') % e
                                edlg = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, emsg)
                                edlg.run()
                                edlg.destroy()
                                self.__activate = False
                                return

                        try:
                                parser.feed(contents)
                        except xml.sax.SAXParseException, e:
                                print("error parsing handshake: %s" % e)

                        # convert handshake update time into datetime
                        self.__handshake_update = datetime.strptime(handshake['update'][0:18], '%Y-%m-%dT%H:%M:%S')
                        self.__handshake_auth = handshake['auth']
                        self.__handshake_songs = int(handshake['songs'])

                        # cache file mtime >= handshake update time: load cached
                        if os.path.exists(self.__cache_filename) and datetime.fromtimestamp(os.path.getmtime(self.__cache_filename)) >= self.__handshake_update:
                                load_catalog()
                        else:
                                self.download_catalog()

                # check for errors
                if not self.settings['url']:
                        edlg = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, _('URL missing'))
                        edlg.run()
                        edlg.destroy()
                        self.__activate = False
                        return

                if not self.settings['password']:
                        edlg = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, _('Password missing'))
                        edlg.run()
                        edlg.destroy()
                        self.__activate = False
                        return

                self.__text = 'Update songs...'
                self.__progress = 0
                self.notify_status_changed()

                handshake = {}

                # instantiate handshake parser
                parser = xml.sax.make_parser()
                parser.setContentHandler(HandshakeHandler(handshake))

                # build handshake url
                timestamp = int(time.time())
                password = hashlib.sha256(self.settings['password']).hexdigest()
                authkey = hashlib.sha256(str(timestamp) + password).hexdigest()

                # execute handshake
                ampache_server_uri = '%s/server/xml.server.php?action=handshake&auth=%s&timestamp=%s&user=%s&version=350001' % (self.settings['url'], authkey, timestamp, self.settings['username'])
                ampache_server_file = Gio.file_new_for_uri(ampache_server_uri)
                ampache_server_file.load_contents_async(
                        Gio.Cancellable(),
                        handshake_cb,
                        parser)
                print("downloading handshake: %s" % (ampache_server_uri))

                def load_catalog():
                        def songs_loaded_cb(file, result, parser):
                                try:
                                        (ok, contents, etag) = file.load_contents_finish(result)
                                except Exception, e:
                                        RB.error_dialog(
                                                title=_("Unable to load catalog"),
                                                message=_("Rhythmbox could not load the Ampache catalog."))
                                        return

                                try:
                                        parser.feed(contents)
                                except xml.sax.SAXParseException, e:
                                        print("error parsing songs: %s" % e)

                                self.__text = ''
                                self.__progress = 1
                                self.notify_status_changed()

                        self.__text = 'Load songs from cache...'
                        self.notify_status_changed()

                        # instantiate songs parser
                        parser = xml.sax.make_parser()
                        parser.setContentHandler(SongsHandler(self.__db, self.__entry_type, self.__albumart))

                        cache_file = Gio.file_new_for_path(self.__cache_filename)
                        cache_file.load_contents_async(
                                Gio.Cancellable(),
                                songs_loaded_cb,
                                parser)

        # Source is activated
        def do_activate(self):

                # activate source if inactive
                if not self.__activate:
                        self.__activate = True

                        shell = self.props.shell

                        # get db
                        self.__db = shell.props.db
                        self.__entry_type = self.props.entry_type

                        # connect playing-song-changed signal
                        self.__art_store = RB.ExtDB(name="album-art")
                        self.__art_request = self.__art_store.connect("request", self.__album_art_requested)

                        # get popup menu
                        self.__popup = shell.props.ui_manager.get_widget('/AmpacheSourceViewPopup')

                        # create cache directory if it doesn't exist
                        cache_path = os.path.dirname(self.__cache_filename)
                        if not os.path.exists(cache_path):
                                os.mkdir(cache_path, 0700)

                        self.update_catalog()

        # Source is activated
        def do_deactivate(self):

                # deactivate source if active
                if self.__activate:
                        self.__activate = False

                        self.__art_store.disconnect(self.__art_request)
                        self.__art_store = None

                        shell.props.ui_manager.remove_ui(self.__popup)

                        self.object = None

        def __album_art_requested(self, store, key, last_time):
                artist = key.get_field('artist')
                album = key.get_field('album')
                uri = self.__albumart[artist + album]
                print('album art uri: %s' % uri)
                if uri:
                        storekey = RB.ExtDBKey.create_storage('album', album)
                        storekey.add_field('artist', artist)
                        store.store_uri(storekey, RB.ExtDBSourceType.SEARCH, uri)

        def do_get_status(self, status, progress_text, progress):
                return (self.__text, self.__progress_text, self.__progress)

GObject.type_register(AmpacheBrowser)
