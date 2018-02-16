# -*- coding: utf-8 -*-

import xbmcup.app

SITE_DOMAIN = str(xbmcup.app.setting['site_domain'])
SITE_URL = 'http://'+SITE_DOMAIN
PLUGIN_ID = 'plugin.video.zona.mobi.dev'
CACHE_DATABASE = 'zonamobi.cache.db'
COOKIE_FILE = 'zonamobi_cookie.txt'

QUALITYS = [None, '360', '480', '720', '1080']