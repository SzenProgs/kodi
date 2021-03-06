# -*- coding: utf-8 -*-

import os
import re
import sys
import urllib
import xbmc
import xbmcgui
import xbmcplugin
import urlparse


def mkreq(params):
	return '%s?%s' % (sys.argv[0], urllib.urlencode(params))


def show_message(heading, message, times=3000, icon=''):
	xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s, "%s")' % (heading, message, times, icon))


def fs_enc(path):
	sys_enc = sys.getfilesystemencoding() if sys.getfilesystemencoding() else 'utf-8'
	return path.decode('utf-8').encode(sys_enc)


def fs_dec(path):
	sys_enc = sys.getfilesystemencoding() if sys.getfilesystemencoding() else 'utf-8'
	return path.decode(sys_enc).encode('utf-8')


class Main:
	__plugin__ = sys.modules["__main__"].__plugin__
	__settings__ = sys.modules["__main__"].__settings__
	__root__ = sys.modules["__main__"].__root__
	__handle__ = int(sys.argv[1])
	site_url = 'https://tr.anidub.com/'

	def __init__(self):
		from cdebug import CDebug
		self.log = CDebug('AniDUBadv.log', 'MAIN')
		del CDebug
		self.log('Initialization')
		self.adv_log = False
		self.addon_data_dir = fs_enc(xbmc.translatePath(Main.__settings__.getAddonInfo('profile')))
		self.images_dir = os.path.join(self.addon_data_dir, 'images')
		self.torrents_dir = os.path.join(self.addon_data_dir, 'torrents')
		self.library_dir = os.path.join(self.addon_data_dir, 'library')
		self.icon = os.path.join(Main.__root__, 'icon.png')
		self.fanart = os.path.join(Main.__root__, 'fanart.jpg')
		self.source_quality = int(Main.__settings__.getSetting("source_quality"))
		self.show_rating = bool(Main.__settings__.getSetting("show_rating").lower() == 'true')
		self.show_history = bool(Main.__settings__.getSetting("show_history").lower() == 'true')
		self.show_search = bool(Main.__settings__.getSetting("show_search").lower() == 'true')
		self.show_peers = bool(Main.__settings__.getSetting("show_peers").lower() == 'true')
		self.progress = xbmcgui.DialogProgress()
		if not os.path.exists(self.addon_data_dir):
			self.log('Creating folder: ' + self.addon_data_dir)
			os.makedirs(self.addon_data_dir)
		if not os.path.exists(self.images_dir):
			self.log('Creating folder: ' + self.images_dir)
			os.mkdir(self.images_dir)
		if not os.path.exists(self.torrents_dir):
			self.log('Creating folder: ' + self.torrents_dir)
			os.mkdir(self.torrents_dir)
		if not os.path.exists(self.library_dir):
			self.log('Creating folder: ' + self.library_dir)
			os.mkdir(self.library_dir)
		self.params = {'mode': 'main', 'url': Main.site_url, 'param': '', 'page': 1}
		args = urlparse.parse_qs(sys.argv[2][1:])
		for a in args:
			self.params[a] = args[a][0]
		from Url import Url
		self.url = Url(use_auth=True, auth_state=bool(self.__settings__.getSetting("auth").lower() == 'true'))
		del Url
		self.url.auth_url = Main.site_url
		self.url.auth_post_data = {'login_name': self.__settings__.getSetting('login'),
								   'login_password': self.__settings__.getSetting('password'), 'login': 'submit'}
		self.url.sid_file = fs_enc(os.path.join(xbmc.translatePath('special://temp/'), 'anidub.sid'))
		self.url.download_dir = self.addon_data_dir
		self.url.cb_auth_ok = self._save_auth_setting
		if not self.__settings__.getSetting("login") or not self.__settings__.getSetting("password"):
			show_message('Авторизация', 'Укажите логин и пароль')
			self.params['mode'] = 'check_settings'
			return
		if not self.url.auth_state:
			if not self.url.auth_try():
				self.params['mode'] = 'check_settings'
				show_message('Ошибка', 'Проверьте логин и пароль')
				self.log('Wrong authentication credentials (init)')
				return
		if Main.__settings__.getSetting("engine") != '':
			Main.__settings__.setSetting("engine", '')
			self.params['mode'] = 'p2psettings'
		self.res_list = ['bd1080', 'tv1080', 'bd720', 'tv720', 'dvd720', 'dvd480', 'hwp', 'psp', '']
		from AnimeDB import AnimeDB
		self.DB = AnimeDB(fs_dec(os.path.join(self.addon_data_dir, 'anidata.db')))
		del AnimeDB

	def _get_soup(self, target, referer='', post=None):
		from bs4 import BeautifulSoup as bs
		html = self.url.get(target=target, referer=referer, post=post)
		soup = bs(html, 'html.parser')
		del bs
		logged = soup.find('span', class_='avatar')
		self._log('logged: %s' % logged)
		if not logged:
			self.url.auth_state = False
			if not self.url.auth_try():
				self.params['mode'] = 'check_settings'
				show_message('Ошибка', 'Проверьте логин и пароль')
				self.log('Wrong authentication credentials (_get_soup)')
				sys.exit()
		return soup;

	def _log(self, data):
		if self.adv_log:
			self.log(data)

	def _dump(self, data):
		if self.adv_log:
			self.dump(data)

	def _save_auth_setting(self):
		self._log('< _save_auth_setting >')
		self.__settings__.setSetting("auth", str(self.url.auth_state))

	def _create_li(self, title, params=None, folder=True, playable=False, context_menu=None, replace_cm=True,
				   selected=False, info=None, art=None, mime=None):
		self._log('< _create_li >')
		if self.show_rating and info and info['rating']:
			if info['rating'] >= 7:
				title = u'[COLOR=F020F020][%s][/COLOR] %s' % (info['rating'], title)
			elif info['rating'] >= 5:
				title = u'[COLOR=F0F0F020[%s][/COLOR] %s' % (info['rating'], title)
			else:
				title = u'[COLOR=F0F02020][%s][/COLOR] %s' % (info['rating'], title)
		li = xbmcgui.ListItem(title)
		if art:
			li.setArt(art)
		if not params:
			params = dict()
		url = '%s?%s' % (sys.argv[0], urllib.urlencode(params))
		if info:
			li.setInfo(type='video', infoLabels=info)
		if context_menu:
			li.addContextMenuItems(context_menu, replaceItems=replace_cm)
		elif replace_cm:
			li.addContextMenuItems([('', '')], replaceItems=True)
		if folder:
			li.setProperty("folder", "true")
		if playable:
			li.setProperty('IsPlayable', 'true')
		if selected:
			li.select(True)
		if mime:
			li.setProperty('mimetype', mime)
		xbmcplugin.addDirectoryItem(handle=Main.__handle__, url=url, listitem=li, isFolder=folder)

	def _get_id_from_url(self, url):
		self._log('< _get_id_from_url >')
		try:
			anime_id = int(re.search(r'/(\d+)-', url).group(1))
		except:
			anime_id = int(re.search(r'newsid=(\d+)', url).group(1))
		return anime_id

	def _get_short_url(self, url=None, anime_id=None):
		self._log('< _get_short_url >')
		if url:
			return '%sindex.php?newsid=%s' % (Main.site_url, self._get_id_from_url(url))
		elif anime_id:
			return '%sindex.php?newsid=%d' % (Main.site_url, int(anime_id))
		else:
			return Main.site_url

	def _get_image(self, anime_id, url=None):
		self._log('< _get_image >')
		if url is None:
			for fl in os.listdir(self.images_dir):
				if fs_enc(str(anime_id)) in fl:
					return fs_dec(os.path.join(self.images_dir, fl))
			return self.icon
		else:
			fl = fs_enc('%d.%s' % (int(anime_id), os.path.basename(url).rsplit('.')[1]))
			if fl in os.listdir(self.images_dir):
				return fs_dec(os.path.join(self.images_dir, fl))
			else:
				self.url.download_dir = self.images_dir
				return fs_dec(self.url.download_file(target=url, dest_name=fl))

	def _get_parse_url(self):
		self._log('< _get_parse_url >')
		if self.params['page'] == 1:
			return '%s%s/' % (Main.site_url, self.params['param'])
		else:
			return '%s%s/page/%d/' % (Main.site_url, self.params['param'], int(self.params['page']))

	def execute(self):
		self._log('< execute >')
		self.log('Mode: %s %s' % (self.params['mode'], self.params['param']))
		getattr(self, 'f_' + self.params['mode'])()
		self.end()

	def end(self):
		self._log('< end >')
		self.log('Shutting down')
		try:
			self.DB.end()
		except:
			pass

	def f_main(self):
		self._log('< f_main >')
		if self.params['page'] == 1:
			self._create_li(title=u'[B][COLOR=FFE84C3D][ Избранное ][/COLOR][/B]',
							params={'mode': 'subcategory', 'param': 'favorites'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			if self.show_search:
				self._create_li(title=u'[COLOR=FFE84C3D][ Поиск ][/COLOR]', params={'mode': 'search'},
								art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			if self.show_history:
				self._create_li(title=u'[COLOR=FFE84C3D][ История просмотров ][/COLOR]', params={'mode': 'history'},
								art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F0F0][ Каталог ][/COLOR]', params={'mode': 'catalog'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F020][ Аниме ][/COLOR]', params={'mode': 'category', 'param': 'anime_tv'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F020][ Дорамы ][/COLOR]', params={'mode': 'subcategory', 'param': 'dorama'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
		self.f_subcategory()

	def f_history(self):
		self._log('< f_history >')
		for i in self.DB.get_history():
			self._create_li_from_id(i)
		xbmcplugin.setContent(handle=Main.__handle__, content='movies')
		xbmcplugin.endOfDirectory(handle=Main.__handle__, succeeded=True)

	def f_catalog(self):
		self._log('< f_catalog >')
		if self.params['param'] == '':
			self._create_li(title=u'[COLOR=F020F0F0][ Популярное за неделю ][/COLOR]', params={'mode': 'popular', 'param': ''},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F0F0][ Аниме по рейтингу ][/COLOR]', params={'mode': 'catalog', 'param': 'rating'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F0F0][ Аниме по жанрам ][/COLOR]', params={'mode': 'catalog', 'param': 'genre'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F0F0][ Аниме по годам ][/COLOR]', params={'mode': 'catalog', 'param': 'year'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F0F0][ Аниме по дабберам ][/COLOR]', params={'mode': 'catalog', 'param': 'dub'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
		elif self.params['param'] == 'rating':
			query = r'dlenewssortby=rating&dledirection=desc&set_new_sort=dle_sort_main&set_direction_sort=dle_direction_main'
			self.common_parser('%s/page/%d/' % (Main.site_url, int(self.params['page'])), query)
		elif self.params['param'] == 'year':
			import datetime
			for i in range(int(datetime.datetime.now().year), 1994, -1):
				self._create_li(title='%d' % i, params={'mode': 'subcategory', 'param': 'xfsearch/%d' % i},
								art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
		elif self.params['param'] == 'genre':
			for i in self.DB.get_genre_list(True):
				self._create_li(title='%s' % i, params={'mode': 'subcategory', 'param': 'xfsearch/%s' % i},
								art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
		elif self.params['param'] == 'dub':
			for i in self.DB.get_dubbers_list():
				self._create_li(title='%s' % i, params={'mode': 'subcategory', 'param': 'xfsearch/%s' % i},
								art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
		xbmcplugin.setContent(handle=Main.__handle__, content='movies')
		xbmcplugin.endOfDirectory(handle=Main.__handle__, succeeded=True)

	def f_popular(self):
		self._log('< f_popular >')
		self.progress.create("AniDUB", "Загрузка")
		soup = self._get_soup(Main.site_url)
		i = 0
		for s in soup.find('div', class_='overflowholder').ul.find_all('li'):
			i += 5
			self.progress.update(i, "Идет загрузка данных", ' ')
			anime_id = self._get_id_from_url(s.find_all('a')[-1].get('href'))
			cover = self._get_image(anime_id, s.span.img.get('src'))
			self._create_li_from_id(anime_id, cover=cover)
		self.progress.close()
		xbmcplugin.setContent(handle=Main.__handle__, content='movies')
		xbmcplugin.endOfDirectory(handle=Main.__handle__, succeeded=True)

	def f_category(self):
		self._log('< f_category >')
		if self.params['page'] == 1:
			self._create_li(title=u'[COLOR=F020F020][ TV Онгоинги ][/COLOR]',
							params={'mode': 'subcategory', 'param': 'anime_tv/anime_ongoing'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F020][ TV 100+ ][/COLOR]',
							params={'mode': 'subcategory', 'param': 'anime_tv/shonen'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F020][ TV Законченные ][/COLOR]',
							params={'mode': 'subcategory', 'param': 'anime_tv/full'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F020][ Аниме OVA ][/COLOR]',
							params={'mode': 'subcategory', 'param': 'anime_ova'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F020][ Аниме фильмы ][/COLOR]',
							params={'mode': 'subcategory', 'param': 'anime_movie'},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})
		self.f_subcategory()

	def f_subcategory(self):
		self._log('< f_subcategory >')
		self.common_parser(self._get_parse_url())
		xbmcplugin.setContent(handle=Main.__handle__, content='movies')
		xbmcplugin.endOfDirectory(handle=Main.__handle__, succeeded=True)

	def f_favorites(self):
		self._log('< f_favorites >')
		if self.params['param'] == 'add':
			self.url.get('%s?do=favorites&doaction=add&id=%d' % (Main.site_url, int(self.params['id'])))
			xbmc.executebuiltin('RunPlugin(plugin://script.media.aggregator/?action=anidub-add-favorites)')
			show_message("Добавлено в избранное", self.params['title'])
			self.log('Favorites added (%s)' % self.params['title'])
		elif self.params['param'] == 'remove':
			self.url.get('%s?do=favorites&doaction=del&id=%d' % (Main.site_url, int(self.params['id'])))
			show_message("Удалено", self.params['title'])
			self.log('Favorites removed (%s)' % self.params['title'])
			xbmc.executebuiltin('Container.Refresh')

	def f_related(self):
		self._log('< f_related >')
		anime_id = self.params['id']
		url = self._get_short_url(anime_id=anime_id)
		soup = self._get_soup(url)
		related = soup.find('div', class_='related').find('ul').find_all('li', recursive=False)
		for r in related:
			link = r.find('a')
			title = link.get_text()
			p_url = link.get('href')
			r_id = self._get_id_from_url(p_url)
			self._create_li_from_id(r_id, title);
		xbmcplugin.setContent(handle=Main.__handle__, content='movies')
		xbmcplugin.endOfDirectory(handle=Main.__handle__, succeeded=True)

	def f_library(self):
		self._log('< f_library >')
		anime_id = int(self.params['id'])
		if self.params['param'] == 'add':
			dir_name = re.sub(r'[\\/:\*\?\"<>\|]', '_', self.DB.get_anime_title(anime_id)[1])
			series_dir = os.path.join(self.library_dir, dir_name)
			os.mkdir(series_dir)
			from tengine import TEngine
			torrent = TEngine(file_name=os.path.join(fs_dec(self.torrents_dir), 'anidub_%d.torrent' % anime_id))
			for i in torrent.enumerate_files():
				fl = open(os.path.join(series_dir, '%s.strm' % os.path.splitext(i['file'])[0]), 'w')
				fl.write(mkreq({'mode': 'play_torrent', 'param': 'query_info', 'index': int(i['index']), 'id': int(anime_id)}))
				fl.close()
			torrent.end()

	def f_select_anime(self):
		self._log('< f_select_anime >')
		data = self._parse_torrent_from_anime_page(self.params['id'])
		cover = self._get_image(anime_id=self.params['id'])
		excl_res = ['ost', 'manga']
		self.log('Loading id: %s' % self.params['id'])
		if self.source_quality > 0:
			tf = None
			idx = 10
			peers = 0
			for v in data:
				if v['id'] in excl_res or not v['id'] in self.res_list:
					continue
				if self.source_quality == 1 and self.res_list.index(v['id']) < idx:
					idx = self.res_list.index(v['id'])
					tf = v
				if self.source_quality == 2 and v['s'] > peers:
					peers = v['s']
					tf = v
			if not tf:
				show_message('AniDUB', 'Ошибка загрузки', icon=self.icon)
				self.log('Loading error')
				return
			self.params = {'mode': 'play_torrent', 'torrent_file_url': tf['t'],
						   'id': self.params['id'], 's': tf['s'], 'l': tf['l']}
			self.f_play_torrent()
		else:
			for v in reversed(data):
				if v['id'] in excl_res:
					continue
				label = u'Качество [%s]  -  раздают: [COLOR=F000F000]%d[/COLOR] качают: [COLOR=F0F00000]%d[/COLOR]' %\
						(v['name'], v['s'], v['l'])
				self._create_li(title=label, params={'mode': 'play_torrent', 'torrent_file_url': v['t'],
													 'id': self.params['id'], 's': v['s'], 'l': v['l']},
													 art={'icon': cover, 'fanart': self.fanart})
			self._create_li(title=u'[COLOR=F020F020][ Похожие ][/COLOR]',
							params={'mode': 'related', 'id': self.params['id']})
			xbmcplugin.endOfDirectory(handle=Main.__handle__, succeeded=True)

	def f_play_torrent(self):
		self._log('< f_play_torrent >')
		if xbmc.getInfoLabel('Container.PluginName') != 'plugin.video.anidub.adv':
			self.log('External playback calls denied')
			return
		from tengine import TEngine
		torrent = TEngine()
		anime_id = self.params['id']
		cover = self._get_image(anime_id=anime_id)
		if 'torrent_file_url' in self.params:
			self.url.download_dir = self.torrents_dir
			file_name = self.url.download_file(target=self.params['torrent_file_url'],
											   referer=self._get_short_url(anime_id=self.params['id']),
											   dest_name='anidub_%d.torrent' % int(self.params['id']))
			self.log('Loading torrent file %s' % file_name)
			torrent.load_file(fs_dec(file_name))
			for fl in torrent.enumerate_files():
				viewed_ep = self.DB.is_episode_viewed(anime_id=anime_id, file_name=fl['file'])
				if self.show_peers:
					title = '%s  [LIGHT][COLOR=F0009000]%d[/COLOR] [COLOR=F0900000]%d[/COLOR][/LIGHT] ' % \
							(fl['file'], int(self.params['s']), int(self.params['l']))
				else:
					title = '%s' % fl['file']
				self._create_li(title=title, params={'mode': 'play_torrent', 'index': int(fl['index']), 'id': int(anime_id)},
								folder=False, playable=True, selected=viewed_ep, info={'size': fl['size'], 'director': 'HUI', 'country': 'RU'},
								art={'icon': cover, 'thumb': cover, 'fanart': self.fanart}, replace_cm=False)
			xbmcplugin.setContent(handle=self.__handle__, content='Movies')
			xbmcplugin.addSortMethod(handle=Main.__handle__, sortMethod=xbmcplugin.SORT_METHOD_LABEL)
			xbmcplugin.endOfDirectory(handle=Main.__handle__, succeeded=True)
		else:
			torrent.load_file(os.path.join(fs_dec(self.torrents_dir), 'anidub_%d.torrent' % int(self.params['id'])))
			title = filter(lambda x: x['index'] == int(self.params['index']), torrent.enumerate_files())[0]['file']
			self.log('Starting playback %s file' % title)
			self.DB.viewed_episode_add(anime_id=anime_id, file_name=title)
			torrent.play(int(self.params['index']), title, 'DefaultVideo.png', cover, True)
		torrent.end()

	def f_check_settings(self):
		self._log('< f_check_settings >')
		self.__settings__.openSettings()

	def f_p2psettings(self):
		self._log('< f_p2psettings >')
		import xbmcaddon
		xbmcaddon.Addon(id='script.module.tengine').openSettings()
		self.f_check_settings()

	def f_search(self):
		self._log('< f_search >')
		if 'new' in self.params:
			skbd = xbmc.Keyboard()
			skbd.setHeading('Поиск:')
			skbd.doModal()
			if skbd.isConfirmed():
				self.params['search_string'] = skbd.getText()
			else:
				return False
		if 'search_string' in self.params:
			if self.params['search_string'] == '':
				return False
			self.DB.searches_add(self.params['search_string'])
			self.search_parser(self.params['search_string'])
			xbmcplugin.setContent(handle=Main.__handle__, content='movies')
		else:
			self._create_li('[B][COLOR=FFFFFFFF]Поиск...[/COLOR][/B]', {'mode': 'search', 'new': 'true'})
			for i in reversed(self.DB.searches_get()):
				self._create_li(i, {'mode': 'search', 'search_string': i})
		xbmcplugin.endOfDirectory(handle=Main.__handle__, succeeded=True)

	def _create_li_from_id(self, anime_id, title=None, cover=None):
		self._log('< _create_li_from_id >')
		if not self.DB.is_anime_in_db(anime_id=anime_id):
			if not self._parse_anime_page_to_db(anime_id):
				return
		ai = self.DB.get_anime(anime_id)
		if not title:
			t = self.DB.get_anime_title(anime_id)
			title = '%s / %s' % (t[0], t[1])
		if not cover:
			cover = self._get_image(anime_id)
		info = {'title': title, 'year': int(ai[0]), 'genre': ai[1], 'director': ai[2], 'writer': ai[3],
				'plot': ai[4], 'rating': float(ai[8] / 10.0)}
		info['plot'] += u'\n[B]Озвучивание:[/B] ' + ai[5]
		info['plot'] += u'\n[B]Перевод:[/B] ' + ai[6]
		info['plot'] += u'\n[B]Тайминг и работа со звуком:[/B] ' + ai[7]
		stitle = self.DB.split_title(title)
		label = '[COLOR=FFFFFFFF][B]%s[/B] / %s[/COLOR] %s' % (stitle[1], stitle[2], stitle[0])
		context_menu = [('Добавить в избранное', 'RunPlugin(%s)' %
						 mkreq({'mode': 'favorites', 'param': 'add', 'title': stitle[1].encode('utf-8'), 'id': anime_id}))]
		self._create_li(title=label, params={'mode': 'select_anime', 'id': anime_id},
						context_menu=context_menu, info=info, art={'icon': cover, 'thumb': cover, 'fanart': cover})

	def _parse_anime_page_to_db(self, anime_id):
		self._log('< _parse_anime_page_to_db >')
		soup = self._get_soup(self._get_short_url(anime_id=anime_id))
		s = soup.find('article')
		self._get_image(anime_id=anime_id, url=s.find('span', class_='poster').img.get('src'))
		ai = self._parse_anime_info(s, False)
		self.DB.add_anime(anime_id, ai['title'], ai['year'], ai['genre'], ai['director'], ai['writer'], ai['plot'],
						  ai['dubbing'], ai['translation'], ai['sound'], int(ai['rating'] * 10))
		return True

	def _parse_anime_info(self, soup, from_list=True):
		self._log('< _parse_anime_info >')
		info = dict()
		info['title'] = soup.h2.a.get_text() if from_list else soup.h1.get_text()
		try:
			info['year'] = int(re.search(r'\d+', soup.find('b', string=u'Год: ').next_sibling.get_text()).group())
		except:
			try:
				info['year'] = int(re.search('\d\d\.\d\d.(\d\d\d\d)',
											 soup.find(string='Дата выпуска: ').parent.parent.get_text()).group(1))
			except:
				info['year'] = 0
		try: info['rating'] = float(re.search(r'\d+.\d+', soup.find('div', class_='rcol').sup.b.get_text()).group()) * 2
		except: info['rating'] = float(re.search(r'\d+', soup.find('div', class_='rcol').sup.b.get_text()).group()) * 2
		try: info['genre'] = soup.find('b', string=u'Жанр: ').next_sibling.get_text()
		except: info['genre'] = ''
		try: info['director'] = soup.find('b', string=u'Режиссер: ').next_sibling.get_text()
		except: info['director'] = ''
		try: info['writer'] = soup.find('b', string=u'Автор оригинала / Сценарист: ').next_sibling.get_text()
		except: info['writer'] = ''
		try: info['dubbing'] = soup.find('b', string=u'Озвучивание: ').next_sibling.get_text()
		except: info['dubbing'] = ''
		try: info['translation'] = soup.find('b', string=u'Перевод: ').next_sibling.get_text()
		except: info['translation'] = ''
		try: info['sound'] = soup.find('b', string=u'Тайминг и работа со звуком: ').next_sibling.get_text()
		except: info['sound'] = ''
		try:
			if from_list:
				info['plot'] = soup.find('b', string=u'Описание:').parent.get_text()[11:-10]
			else:
				if soup.find('div', class_='screens'):
					soup.find('div', class_='screens').clear()
				info['plot'] = soup.find(string=u'Описание:').parent.parent.get_text()[24:-2]
		except: info['plot'] = ''
		return info

	def _parse_torrent_from_anime_page(self, anime_id):
		self._log('< _parse_torrent_from_anime_page >')
		url = self._get_short_url(anime_id=anime_id)
		soup = self._get_soup(url)
		res = list()
		qualities = soup.find('div', class_='torrent_c').find_all('div', recursive=False)
		for q in qualities:
			qid = q.get('id')
			try:
				desription = soup.find(href='#' + qid).get_text()
			except:
				desription = 'N/A'
			seeders = q.find('span', class_='li_distribute_m').get_text()
			leechers = q.find('span', class_='li_swing_m').get_text()
			t_url = Main.site_url + q.a.get('href')[1:]
			res.append({'id': str(qid), 'name': desription, 's': int(seeders), 'l': int(leechers), 't': t_url})
		return res

	def common_parser(self, url, post=None):
		self._log('< common_parser >')
		self.progress.create("AniDUB", "Инициализация")
		soup = self._get_soup(url, post=post)
		articles = soup.find_all('article', {'class': 'story'})
		i = 20
		for article in articles:
			if xbmc.abortRequested or self.progress.iscanceled():
				break
			xbmc.sleep(50)
			self.progress.update(i, "Идет загрузка данных", '')
			if u'Манга' in article.div.div.div.get_text() or u'OST' in article.div.div.div.get_text():
				continue
			i += 5
			anime_url = article.h2.a.get('href')
			anime_id = int(self._get_id_from_url(anime_url))
			cover = self._get_image(anime_id=anime_id, url=article.find('div', class_='story_c').img.get('src'))
			ai = self._parse_anime_info(article)
			stitle = self.DB.split_title(ai['title'])
			if stitle[0] == '[VN]':
				continue
			if not self.DB.is_anime_in_db(anime_id=anime_id):
				self.DB.add_anime(anime_id, ai['title'], int(ai['year']), ai['genre'], ai['director'], ai['writer'],
								  ai['plot'], ai['dubbing'], ai['translation'], ai['sound'], int(ai['rating'] * 10))
			else:
				self.DB.update_rating(anime_id, int(ai['rating'] * 10))
			ai['plot'] += u'\n[B]Озвучивание:[/B] ' + ai['dubbing']
			ai['plot'] += u'\n[B]Перевод:[/B] ' + ai['translation']
			ai['plot'] += u'\n[B]Тайминг и работа со звуком:[/B] ' + ai['sound']
			ai.pop('dubbing', None)
			ai.pop('translation', None)
			ai.pop('sound', None)
			label = '[COLOR=FFFFFFFF][B]%s[/B] / %s[/COLOR] %s' % (stitle[1], stitle[2], stitle[0])
			if self.params['param'] == 'favorites':
				cm = [('Удалить из избранного', 'RunPlugin(%s)' %
					   mkreq({'mode': 'favorites', 'param': 'remove', 'title': stitle[1].encode('utf-8'), 'id': anime_id}))]#,
					  #('Добавить в медиатеку', 'RunPlugin(%s)' %
					  # mkreq({'mode': 'library', 'param': 'add', 'id': anime_id}))]
			else:
				cm = [('Добавить в избранное', 'RunPlugin(%s)' %
					   mkreq({'mode': 'favorites', 'param': 'add', 'title': stitle[1].encode('utf-8'), 'id': anime_id}))]
			self._create_li(title=label, params={'mode': 'select_anime', 'id': anime_id},
							info=ai, context_menu=cm, art={'icon': cover, 'thumb': cover, 'fanart': cover})
		self.progress.close()
		if 'page/%d' % (int(self.params['page']) + 1) in str(soup.find('span', class_='navi_link')) and i > 20:
			self._create_li(title=u'[ Следующая страница ]',
							params={'mode': self.params['mode'], 'param': self.params['param'],
									'page': (int(self.params['page']) + 1)},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})

	def search_parser(self, s):
		self._log('< search_parser >')
		self.progress.create("Поиск", "Инициализация")
		search_query = r'index.php?do=search&story=' + urllib.quote(s, safe='') + \
					   r'&search_start=' + str(self.params['page']) + \
					   r'&result_from=' + str(((int(self.params['page']) - 1) * 15) + 1) + \
					   r'&replyless=0&full_search=1&showposts=0&subaction=search&beforeafter=after&replylimit=0' \
					   r'&titleonly=0&searchdate=0&catlist%5B%5D=2&catlist%5B%5D=14&catlist%5B%5D=10&catlist%5B%5D=11' \
					   r'&catlist%5B%5D=3&catlist%5B%5D=4&catlist%5B%5D=5&catlist%5B%5D=9&catlist%5B%5D=6' \
					   r'&catlist%5B%5D=7&catlist%5B%5D=8&sortby=&resorder=desc&searchuser='
		soup = self._get_soup(Main.site_url + 'index.php?do=search', post=search_query)
		self.progress.update(10, "Поиск...", s)
		searches = soup.find_all('div', class_="search_post")
		i = 20
		for sr in searches:
			if xbmc.abortRequested or self.progress.iscanceled():
				return
			i += 5
			anime_id = self._get_id_from_url(sr.h2.a.get('href'))
			cover = self._get_image(anime_id, sr.div.img.get('src'))
			title = sr.h2.a.get_text()
			self.progress.update(i, "Идет загрузка данных", ' ')
			self._create_li_from_id(anime_id, title, cover)
		self.progress.close()
		if soup.find('a', id='nextlink'):
			self._create_li(title=u'[ Следующая страница ]',
							params={'mode': 'search', 'search_string': s, 'page': int(self.params['page']) + 1},
							art={'icon': 'DefaultFolder.png', 'fanart': self.fanart})

