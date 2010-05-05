import rb, rhythmdb

import gobject
import gtk
import gio
import datetime
import hashlib
import os

class AmpacheCache():
	def __init__(self, cache_file, cache_enabled):
		import xml.dom.minidom
		self.file          = cache_file                                  # path to the cache file

		self.xml_document  = xml.dom.minidom.Document()                  # xml root element 
		self.xml_songs     = self.xml_document.createElement('songs')    # xml songs element
		self.enabled       = cache_enabled

       	def add_song(self, song_id, song_url, song_title, song_artist, song_album, song_genre, song_track_number, song_duration):
		song = self.xml_document.createElement('song')
		song.setAttribute('id', str(song_id))
		song.setAttribute('url', str(song_url))
		song.setAttribute('title', str(song_title))
		song.setAttribute('artist', str(song_artist))
		song.setAttribute('album', str(song_album))
		song.setAttribute('genre', str(song_genre))
		song.setAttribute('track_number', str(song_track_number))
		song.setAttribute('duration', str(song_duration))
		self.xml_songs.appendChild(song)

	def write(self):
		self.xml_document.appendChild(self.xml_songs)

		h = open(self.file, 'w')
		h.writelines(self.xml_document.toprettyxml(indent='  '))
		h.close()


class AmpacheBrowser(rb.BrowserSource):
	__gproperties__ = {
		'plugin': (rb.Plugin, 'plugin', 'plugin', gobject.PARAM_WRITABLE|gobject.PARAM_CONSTRUCT_ONLY),
	}

	def __init__(self):
        	rb.BrowserSource.__init__(self)

	def activate(self, config):
		# Plugin activated
		self.limit         = 100
		self.offset        = 0
		self.url           = ''
		self.auth          = None
		
		self.cache_stream  = None
		
		self.cache = AmpacheCache('/home/%s/.gnome2/rhythmbox/plugins/ampache/song-cache.xml' % os.getlogin(), True)

		self.config = config

		width, height = gtk.icon_size_lookup(gtk.ICON_SIZE_LARGE_TOOLBAR)
		icon = gtk.gdk.pixbuf_new_from_file_at_size(self.config.get("icon_filename"), width, height)
		self.set_property( "icon",  icon) 

		shell = self.get_property("shell")
		self.db = shell.get_property("db")
		self.entry_type = self.get_property("entry-type")

		self.__activate = False

	# need if we use find_file
	def do_set_property(self, property, value):
		if property.name == 'plugin':
			self.__plugin = value
		else:
			raise AttributeError, 'unknown property %s' % property.name

        def do_impl_get_browser_key(self):
                return "/apps/rhythmbox/plugins/ampache/show_browser"

        def do_impl_get_paned_key(self):
                return "/apps/rhythmbox/plugins/ampache/paned_position"

	def db_add_entry(self, song_id, song_url, song_title, song_artist, song_album, song_genre, song_track_number, song_duration):
		entry = self.db.entry_new(self.entry_type, song_url)

		if song_id != '':
			self.db.set(entry, rhythmdb.PROP_TITLE, song_title)
		if song_artist != '':
			self.db.set(entry, rhythmdb.PROP_ARTIST, song_artist)
       		if song_album != '':
			self.db.set(entry, rhythmdb.PROP_ALBUM, song_album)
		if song_genre != '':
			self.db.set(entry, rhythmdb.PROP_GENRE, song_genre)

       		self.db.set(entry, rhythmdb.PROP_TRACK_NUMBER, song_track_number)
		self.db.set(entry, rhythmdb.PROP_DURATION, song_duration)

	def load_db(self):
		self.cache_stream = gio.File(self.cache.file)
		self.cache_stream.read_async(self.load_db_cb)

       	def load_db_cb(self, gdaemonfile, result):
		import xml.dom.minidom
    
		xmldata = self.cache_stream.read_finish(result).read()
		dom = xml.dom.minidom.parseString(xmldata)
		self.cache_stream = None
		
		for song in dom.getElementsByTagName('song'):
			song_id           = song.getAttribute('id')
			song_url          = song.getAttribute('url')
			song_title        = song.getAttribute('title')
			song_artist       = song.getAttribute('artist')
			song_album        = song.getAttribute('album')
			song_genre        = song.getAttribute('genre')
			song_track_number = int(song.getAttribute('track_number'))
			song_duration     = int(song.getAttribute('duration'))

			self.db_add_entry(song_id, song_url, song_title, song_artist, song_album, song_genre, song_track_number, song_duration)
    
		self.db.commit()

       	def download_db(self):
		import time

		self.url = self.config.get("url")

		username = self.config.get("username") # necessary ?
		password = self.config.get("password")

		if not self.url:
			# GUI: No URL entered
			return

		if not password:
			# GUI: No password entered
			return

		timestamp = int(time.time())
		password  = hashlib.sha256(password).hexdigest()
		authkey   = hashlib.sha256(str(timestamp) + password).hexdigest()

		auth_url = "%s?action=handshake&auth=%s&timestamp=%s&user=%s&version=350001" % (self.url, authkey, timestamp, username)

		rb.Loader().get_url(auth_url, self.download_db_cb, self.url)

	def download_db_cb(self, result, url):
		import xml.dom.minidom

		if result is None:
			emsg = _("Error connecting to Ampache Server at %s") % (self.url)
			dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, emsg)
			dlg.run()
			dlg.destroy()
			return

		dom = xml.dom.minidom.parseString(result)
		self.auth = dom.getElementsByTagName("auth")[0].childNodes[0].data

		print "Auth: %s" % self.auth
		#gobject.idle_add(self.populate)
		self.populate()

	def populate(self):
		print "offset: %s, limit: %s" % (self.offset, self.limit)
		request = "%s?offset=%s&limit=%s&action=songs&auth=%s" % (self.url, self.offset, self.limit, self.auth)
		print "url: %s" % request

		rb.Loader().get_url(request, self.populate_cb, request)

	def populate_cb(self, result, url):
		import xml.dom.minidom

		if result is None:
			emsg = _("Error downloading song database from Ampache Server at %s") % (self.url)
			dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, emsg)
			dlg.run()
			dlg.destroy()
			return

		song_count = 0

		dom = xml.dom.minidom.parseString(result)
		for node in dom.getElementsByTagName("song"):
			song_count = song_count + 1
			song_id    = node.getAttribute("id")

			tmp = node.getElementsByTagName("url")
			if tmp == []:
				song_url = '' #node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					song_url = '';
				else:
					song_url = tmp[0].childNodes[0].data
        
		       	tmp = node.getElementsByTagName("title")
			if tmp == []:
				song_title = '' #node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					song_title = '';
				else:
					song_title = tmp[0].childNodes[0].data
                        #print "title: %s" % e_title

		       	tmp = node.getElementsByTagName("artist")
			if tmp == []:
				song_artist = '' #node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					song_artist = '';
				else:
					song_artist = tmp[0].childNodes[0].data
                        #print "artist: %s" % e_artist
        
			tmp = node.getElementsByTagName("album")
			if tmp == []:
				song_album = '' #node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					song_album = '';
				else:
					song_album = tmp[0].childNodes[0].data
                        #print "album: %s" % e_album

			tmp = node.getElementsByTagName("tag")
			if tmp == []:
				song_genre = '' #node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					song_genre = '';
				else:
					song_genre = tmp[0].childNodes[0].data
                        #print "genre: %s" % e_genre

			song_track_number = int(node.getElementsByTagName("track")[0].childNodes[0].data)
			song_duration     = int(node.getElementsByTagName("time")[0].childNodes[0].data)

                        #print "Processing %s - %s" % (artist, album) #DEBUG

                        # adding the song to our database
			self.db_add_entry(song_id, song_url, song_title, song_artist, song_album, song_genre, song_track_number, song_duration)

			if self.cache.enabled == True:
				# create an entry for the cache file
				self.cache.add_song(song_id, song_url, song_title, song_artist, song_album, song_genre, song_track_number, song_duration)
				
		self.db.commit()
		if (song_count < self.limit):
			if self.cache.enabled == True:
				# write the xml cache file, so the next time we dont need to download this information
				self.cache.write()
				
	       		return False
		else:
			self.offset = self.offset + song_count

	       	self.populate()
		return True

	# Source is first clicked on
	def do_impl_activate (self):
		# Connect to Ampache if not already
		if not self.__activate:
			self.__activate = True
			if self.cache.enabled == True:
				if not os.path.exists(self.cache.file):
					self.download_db()
				else:
					self.load_db()
			else:
				self.download_db()
				
		rb.BrowserSource.do_impl_activate(self)
		
gobject.type_register(AmpacheBrowser)
