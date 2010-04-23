import rb, rhythmdb

import gobject
import gtk
#import gnomevfs, gnome
import datetime
import hashlib

class AmpacheBrowser(rb.BrowserSource):
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

		self.shell = self.get_property("shell")
		self.db = self.shell.get_property("db")
		self.entry_type = self.get_property("entry-type")

		self.__activate = False

	# need if we use find_file
	def do_set_property(self, property, value):
		if property.name == 'plugin':
			self.__plugin = value
		else:
			raise AttributeError, 'unknown property %s' % property.name

	def load_db(self):
		import urllib2
		import time
		import md5
		import xml.dom.minidom

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

		auth_xml = urllib2.urlopen("%s?action=handshake&auth=%s&timestamp=%s&user=%s&version=350001" % (url, authkey, timestamp, username)).read()
		dom = xml.dom.minidom.parseString(auth_xml)
		auth = dom.getElementsByTagName("auth")[0].childNodes[0].data

		print "Auth: %s" % auth

		limit = 1000
		offset = 0

		# FIXME ugly, i know
		while True:
			print "offset: %s, limit: %s" % (offset, limit)
			request = "%s?offset=%s&limit=%s&action=songs&auth=%s" % (url, offset, limit, auth)
			print "url: %s" % request
			songs_xml = urllib2.urlopen(request).read()
			song = 0

			dom = xml.dom.minidom.parseString(songs_xml)
			for node in dom.getElementsByTagName("song"):
				song = song + 1

				e_id = node.getAttribute("id")

				e_url = node.getElementsByTagName("url")[0].childNodes[0].data
				e_title = node.getElementsByTagName("title")[0].childNodes[0].data
				e_artist = node.getElementsByTagName("artist")[0].childNodes[0].data
				e_album = node.getElementsByTagName("album")[0].childNodes[0].data
				#e_genre = node.getElementsByTagName("genre")[0].childNodes[0].data
				e_track_number = int(node.getElementsByTagName("track")[0].childNodes[0].data)
				e_duration = int(node.getElementsByTagName("time")[0].childNodes[0].data)

				#print "Processing %s - %s" % (artist, album) #DEBUG

				e = self.db.entry_new(self.entry_type, e_url)
				self.db.set(e, rhythmdb.PROP_TITLE, e_title)
				self.db.set(e, rhythmdb.PROP_ARTIST, e_artist)
				self.db.set(e, rhythmdb.PROP_ALBUM, e_album)
				#self.db.set(e, rhythmdb.PROP_GENRE, e_genre)
				self.db.set(e, rhythmdb.PROP_TRACK_NUMBER, e_track_number)
				self.db.set(e, rhythmdb.PROP_DURATION, e_duration)
				# FIXME date - not implemented in ampache yet
				#self.db.set(e, rhythmdb.PROP_DATE, datetime.date(2000, 1, 1).toordinal())


			self.db.commit()

			if (song < limit):
				break
			else:
				offset = offset + song

	# Source is first clicked on
	def do_impl_activate (self):

		# Connect to Ampache if not already
		if not self.__activate:
			self.__activate = True
			self.load_db()

		rb.BrowserSource.do_impl_activate(self)

gobject.type_register(AmpacheBrowser)
