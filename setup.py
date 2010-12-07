#!/usr/bin/env python

from distutils.core import setup

setup(name="rhythmbox-ampache",
    version="0.11",
	description="A Rhythmbox plugin to stream music from an Ampache server",
	author="Rhythmbox Ampache plugin team",
	author_email="rhythmbox-ampache@googlegroups.com",
	url="http://code.google.com/p/rhythmbox-ampache",
	packages= ["ampache"],
	)
