import rb, rhythmdb

import gobject
import gtk
import datetime
import hashlib

class AmpacheBrowser(rb.BrowserSource):
	limit = 100
	offset = 0
	url = ''
	auth = None
	auth_stream = None

	__gproperties__ = {
		'plugin': (rb.Plugin, 'plugin', 'plugin', gobject.PARAM_WRITABLE|gobject.PARAM_CONSTRUCT_ONLY),
	}

	def __init__(self):
        	rb.BrowserSource.__init__(self)

	def activate(self, config):
		# Plugin activated
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

	def load_db(self):
		import time

		url = self.config.get("url")
		username = self.config.get("username")
		password = self.config.get("password")

		if not url:
			return

		if not password:
			return
		timestamp = int(time.time())
		password = hashlib.sha256(password).hexdigest()
		authkey = hashlib.sha256(str(timestamp) + password).hexdigest()

		auth_url = "%s?action=handshake&auth=%s&timestamp=%s&user=%s&version=350001" % (url, authkey, timestamp, username)
		self.url = url
		rb.Loader().get_url(auth_url, self.load_db_cb, url)

	def load_db_cb(self, result, url):
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

		song = 0

		dom = xml.dom.minidom.parseString(result)
		for node in dom.getElementsByTagName("song"):
			song = song + 1

			e_id = node.getAttribute("id")

			tmp = node.getElementsByTagName("url")
			if tmp == []:
				e_url = 0#node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					e_url = 0;
				else:
					e_url = tmp[0].childNodes[0].data
			#e_url = node.getElementsByTagName("url")[0].childNodes[0].data
				

			tmp = node.getElementsByTagName("title")
			if tmp == []:
				e_title = 0#node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					e_title = 0;
				else:
					e_title = tmp[0].childNodes[0].data
			#e_title = node.getElementsByTagName("title")[0].childNodes[0].data
			#print "title: %s" % e_title


			tmp = node.getElementsByTagName("artist")
			if tmp == []:
				e_artist = 0#node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					e_artist = 0;
				else:
					e_artist = tmp[0].childNodes[0].data
			#e_artist = node.getElementsByTagName("artist")[0].childNodes[0].data
			#print "artist: %s" % e_artist
				
				
			tmp = node.getElementsByTagName("album")
			if tmp == []:
				e_album = 0#node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					e_album = 0;
				else:
					e_album = tmp[0].childNodes[0].data
			#e_album = node.getElementsByTagName("album")[0].childNodes[0].data
			#print "album: %s" % e_album

				
			tmp = node.getElementsByTagName("tag")
			if tmp == []:
				e_genre = 0#node.getElementsByTagName("genre")[0].childNodes[0].data
			else:
				if tmp[0].childNodes == []:
					e_genre = 0;
				else:
					e_genre = tmp[0].childNodes[0].data
			#e_genre = node.getElementsByTagName("genre")[0].childNodes[0].data
			#print "genre: %s" % e_genre


			e_track_number = int(node.getElementsByTagName("track")[0].childNodes[0].data)
			e_duration = int(node.getElementsByTagName("time")[0].childNodes[0].data)

			#print "Processing %s - %s" % (artist, album) #DEBUG

			e = self.db.entry_new(self.entry_type, e_url)
			self.db.set(e, rhythmdb.PROP_TITLE, e_title)
			self.db.set(e, rhythmdb.PROP_ARTIST, e_artist)
			self.db.set(e, rhythmdb.PROP_ALBUM, e_album)
			self.db.set(e, rhythmdb.PROP_GENRE, e_genre)
			self.db.set(e, rhythmdb.PROP_TRACK_NUMBER, e_track_number)
			self.db.set(e, rhythmdb.PROP_DURATION, e_duration)
			# FIXME date - not implemented in ampache yet
			#self.db.set(e, rhythmdb.PROP_DATE, datetime.date(2000, 1, 1).toordinal())

		self.db.commit()

		if (song < self.limit):
			return False
		else:
			self.offset = self.offset + song
		self.populate()
		return True


	# Source is first clicked on
	def do_impl_activate (self):

		# Connect to Ampache if not already
		if not self.__activate:
			self.__activate = True
			self.load_db()

		rb.BrowserSource.do_impl_activate(self)

gobject.type_register(AmpacheBrowser)
