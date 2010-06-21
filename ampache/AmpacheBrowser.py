import rb, rhythmdb;

import gobject;
import gtk;
import datetime;
import hashlib;
import threading, urllib;

time = None;
xml_dom = None;

def url_open(url, callback, *args):
	data = [];
	def get_url_func(url, data):
		try:
			result = urllib.urlopen(url);
			out = result.read();
			data.append(out);
		except Exception, e:
			data.append(e);
		gtk.main_quit();
	get_url_thread = threading.Thread(target=get_url_func, args=[url, data]);
	get_url_thread.start();
	gtk.main();
	callback(data[0], *args);

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

	def init_ui(self):
		popup_ui = """<ui>
                                <popup name="AmpacheSourcePopup">
                                  <menuitem name="ReloadAmpacheDB" action="ReloadAmpacheDB"/>
                                </popup>
                              </ui>""";

		manager = self.shell.get_player().get_property('ui-manager');
		self.action_group = gtk.ActionGroup('AmpachePluginActions');
		action = gtk.Action('ReloadAmpacheDB', _('Reload'),
				    _('Renew session and reload data from Ampache server'),
				    None);
		self.action_group.add_action(action);
		manager.insert_action_group(self.action_group, 0);
		self.ui_id = manager.add_ui_from_string(popup_ui);
		action.connect('activate', self.reload_db);


	def activate(self, config):
		# Plugin activated
		self.config = config

		width, height = gtk.icon_size_lookup(gtk.ICON_SIZE_LARGE_TOOLBAR)
		icon = gtk.gdk.pixbuf_new_from_file_at_size(self.config.get("icon_filename"), width, height)
		self.set_property( "icon",  icon) 

		self.shell = self.get_property("shell")
		self.db = self.shell.get_property("db")
		self.entry_type = self.get_property("entry-type")
		self.init_ui();

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
		global time;
		if not time:
			import time;

		url = self.config.get("url")
		username = self.config.get_username();
		password = self.config.get_password();

		if not url:
			return
		if not password:
			return

		timestamp = int(time.time())
		password = hashlib.sha256(password).hexdigest()
		authkey = hashlib.sha256(str(timestamp) + password).hexdigest()

		self.offset = 0;
		auth_url = "%s?action=handshake&auth=%s&timestamp=%s&user=%s&version=350001" % (url, authkey, timestamp, username)
		self.url = url
		url_open(auth_url, self.load_db_cb);
		# This is the recommended Rhythmbox plugin recipe, but uses GIO which is causing session errors requiring reboots
		#rb.Loader().get_url(auth_url, self.load_db_cb)

	def load_db_cb(self, result):
		global xml_dom;
		if not xml_dom:
			import xml.dom.minidom as xml_dom;

		if isinstance(result, Exception) or not result:
			emsg = _("Error connecting to Ampache Server at %s") % (self.url,)
			if result:
				emsg += ': \n' + str(result.args);
				
			dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, emsg)
			dlg.run()
			dlg.destroy()
			return

		dom = xml_dom.parseString(result)
		self.auth = dom.getElementsByTagName("auth")[0].childNodes[0].data

		print "Auth: %s" % self.auth
		#gobject.idle_add(self.populate)
		self.populate()

	def populate(self):
		#gtk.gdk.threads_enter()
		print "offset: %s, limit: %s" % (self.offset, self.limit) #DEBUG
		request = "%s?offset=%s&limit=%s&action=songs&auth=%s" % (self.url, self.offset, self.limit, self.auth)
		print "url: %s" % request #DEBUG

		url_open(request, self.populate_cb, request);
		#See previous use of get_url for why this is no longer is use
		#rb.Loader().get_url(request, self.populate_cb, request)

	def populate_cb(self, result, url):
		global xml_dom;
		if not xml_dom:
			import xml.dom.minidom as xml_dom;

		if isinstance(result, Exception) or not result:
			emsg = _("Error downloading song database from Ampache Server at %s") % (self.url)
			if result:
				emsg += ': \n' + str(result.args);

			dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, emsg)
			dlg.run()
			dlg.destroy()
			return

		def getEltData(node, tagname, default=''):
			try:
				return node.getElementsByTagName(tagname)[0].childNodes[0].data;
			except:
				return default;

		dom = xml_dom.parseString(result);
		song = 0
		db_set = self.db.set;
		for node in dom.getElementsByTagName('song'):
			song += 1;

			#e_id = node.getAttribute('id')
			e_url = getEltData(node, 'url');
			e_title = getEltData(node, 'title');
			e_artist = getEltData(node, 'artist');
			e_album = getEltData(node, 'album');
			e_genre = getEltData(node, 'tag');
			e_track_number = int(getEltData(node, 'track', 0));
			e_duration = int(getEltData(node, 'time', 0));

			#print "Processing %s - %s" % (artist, album) #DEBUG

			e = self.db.entry_new(self.entry_type, e_url);
			db_set(e, rhythmdb.PROP_TITLE, e_title);
			db_set(e, rhythmdb.PROP_ARTIST, e_artist);
			db_set(e, rhythmdb.PROP_ALBUM, e_album);
			db_set(e, rhythmdb.PROP_GENRE, e_genre);
			db_set(e, rhythmdb.PROP_TRACK_NUMBER, e_track_number);
			db_set(e, rhythmdb.PROP_DURATION, e_duration);
			# FIXME date - not implemented in ampache yet
			#db_set(e, rhythmdb.PROP_DATE, datetime.date(2000, 1, 1).toordinal())

		self.db.commit()

		if (song < self.limit):
			#gtk.gdk.threads_leave()
			return False
		else:
			self.offset = self.offset + song
		#gtk.gdk.threads_leave()
		self.populate()
		return True


	# Source is first clicked on
	def do_impl_activate (self):
		# Connect to Ampache if not already
		if not self.__activate:
			self.__activate = True
			self.load_db()

		rb.BrowserSource.do_impl_activate(self)

	def unload_db(self):
		self.db.entry_delete_by_type(self.entry_type);

	def reload_db(self, *args):
		self.unload_db();
		self.load_db();

	def do_impl_show_popup(self):
		self.show_source_popup('/AmpacheSourcePopup');

gobject.type_register(AmpacheBrowser)
