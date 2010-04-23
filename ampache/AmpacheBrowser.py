import rb, rhythmdb

import gobject
import gtk
#import gnomevfs, gnome
import datetime

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

	def do_set_property(self, property, value):
		# No idea what this is
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

		print "URL is %s" % url

		timestamp = int(time.time())
		auth_xml = urllib2.urlopen("%s?action=handshake&user=%s&auth=%s&timestamp=%s" % (url, username, md5.md5(str(timestamp) + password).hexdigest(), timestamp)).read()
		dom = xml.dom.minidom.parseString(auth_xml)
		auth = dom.getElementsByTagName("auth")[0].childNodes[0].data

		print "Auth: %s" % auth
		print "Getting songs... will take a while"

		songs_xml = urllib2.urlopen("%s?limit=2&action=songs&auth=%s" % (url, auth)).read()
		#print "Songs?: %s" % songs_xml

		#e = self.db.entry_new(self.entry_type, "http://192.168.11.176/play/....mp3")
		#self.db.set(e, rhythmdb.PROP_DATE, datetime.date(1999, 1, 1).toordinal())
		#self.db.set(e, rhythmdb.PROP_TITLE, "Blah")
		#self.db.set(e, rhythmdb.PROP_ARTIST, "Blah")
		#self.db.set(e, rhythmdb.PROP_ALBUM, "Blah")
		# rhythmdb.PROP_DURATION
		#self.db.set(e, rhythmdb.PROP_TRACK_NUMBER, 1)
		# rhythmdb.PROP_GENRE
		# rhythmdb.PROP_MUSICBRAINZ_ALBUMID

		dom = xml.dom.minidom.parseString(songs_xml)
		for node in dom.getElementsByTagName("song"):
			id = node.getAttribute("id")
			title = node.getElementsByTagName("title")[0].childNodes[0].data
			artist = node.getElementsByTagName("artist")[0].childNodes[0].data
			album = node.getElementsByTagName("album")[0].childNodes[0].data
			genre = node.getElementsByTagName("genre")[0].childNodes[0].data
			track_number = int(node.getElementsByTagName("track")[0].childNodes[0].data)
			duration = int(node.getElementsByTagName("time")[0].childNodes[0].data)
			url = node.getElementsByTagName("url")[0].childNodes[0].data

			#print "Processing %s - %s" % (artist, album) #DEBUG

			e = self.db.entry_new(self.entry_type, url)
			self.db.set(e, rhythmdb.PROP_TITLE, title)
			self.db.set(e, rhythmdb.PROP_ARTIST, artist)
			self.db.set(e, rhythmdb.PROP_ALBUM, album)
			self.db.set(e, rhythmdb.PROP_GENRE, genre)
			self.db.set(e, rhythmdb.PROP_TRACK_NUMBER, track_number)
			self.db.set(e, rhythmdb.PROP_DURATION, duration)
			self.db.set(e, rhythmdb.PROP_DATE, datetime.date(2000, 1, 1).toordinal())

		self.db.commit()

	def do_impl_activate (self):
		# Source is first clicked on

		# Connect to Ampache
		if not self.__activate:
			print "INFO: AmpacheBrowser activated"
			self.__activate = True
			self.load_db()

		rb.BrowserSource.do_impl_activate(self)

gobject.type_register(AmpacheBrowser)
