import gconf, gtk;

gnomekeyring = None;

class AmpacheConfig(object):
	def __init__(self):
		global gnomekeyring;
		if not gnomekeyring:
			try:
				import gnomekeyring;
			except:
				print 'gnomekeyring python package not installed, using gconf';
				emsg = _('GnomeKeyring python module is not installed! ' +
					 'Please exit and try\n\n' +
					 'apt-get install python-gnomekeyring\n' +
					 'emerge gnome-keyring-python\n' +
					 'yum install gnome-python2-gnomekeyring\n\n' +
					 'depending on your distribution. If you do not, ' +
					 'your password will be stored in plain text!');
				dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO,
							gtk.BUTTONS_OK, emsg);
				dlg.run();
				dlg.destroy();

		self.gconf_keys = {
			'url'		: '/apps/rhythmbox/plugins/ampache/url',
			'username'	: '/apps/rhythmbox/plugins/ampache/username',
			'password'      : '/apps/rhythmbox/plugins/ampache/password',
			'auth'          : '/apps/rhythmbox/plugins/ampache/keyring-auth-key',

			'name'		: "/apps/rhythmbox/plugins/ampache/name",
			'group'		: "/apps/rhythmbox/plugins/ampache/group",

			'icon'		: "/apps/rhythmbox/plugins/ampache/icon",
			'icon_filename'	: "/apps/rhythmbox/plugins/ampache/icon_filename",

		}

		print 'config getting gconf keys'
		self.gconf = gconf.client_get_default()

		# Defaults ("hidden" options)
		self.set("name", "Ampache")
		self.set("group", "Shared")
		self.set("icon", "ampache.ico")

		if gnomekeyring:
			self.load_gnome_keyring_info();
		else:
			self._username = self.get('username');
			self._password = self.get('password');

	def load_gnome_keyring_info(self):
		self.keyring = gnomekeyring.get_default_keyring_sync();
		self.auth_key = self.get('auth');
		if self.auth_key:
			self.auth_key = int(self.auth_key);

		if not self.auth_key:
			self._username = '';
			self._password = '';
		else:
			def get_info_cb(result, item, data):
				if not result:
					data.append(item.get_secret());
				gtk.main_quit();
			data = [];
			gnomekeyring.item_get_info(self.keyring, self.auth_key, get_info_cb, data);
			gtk.main();
			try:
				secret = data[0];
			except ValueError:
				self._username = '';
				self._password = '';
				self.auth_key = 0;
			else:
				self._username, self._password = secret.split('\n');
		
	def get(self, key):
		if self.gconf.get_string(self.gconf_keys[key]):
			return self.gconf.get_string(self.gconf_keys[key])
		else:
			return ""

	def set(self, key, value):
		self.gconf.set_string(self.gconf_keys[key], str(value))

	def get_username(self):
		return self._username;

	def get_password(self):
		return self._password;

	def set_login_info(self, username, password):
		self._username = username;
		self._password = password;
		if gnomekeyring:
			self.set_gnome_keyring_info(username, password);
		else:
			self.set('username', username);
			self.set('password', password);

	def set_gnome_keyring_info(self, username, password):
		def item_create_cb(result, auth_key):
			if not result:
				self.set('auth', auth_key);
			else:
				print 'could not save login info in keyring:', result;
			gtk.main_quit();
		gnomekeyring.item_create(
			self.keyring,
			gnomekeyring.ITEM_GENERIC_SECRET,
			'rhythmbox-ampache login',
			{'appname':'rhythmbox-ampache'},
			'\n'.join((username, password)),
			True, item_create_cb);
		gtk.main();
			
#if __name__ == "__main__":
	##Note: These tests are no longer valid with the switch to gnomekeyring
	#config = AmpacheConfig()
	#print config.get("url")
	#config.set("password", "testing123")
	#print config.get("username")
	#print config.get("password")
	
