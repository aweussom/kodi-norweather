# -*- coding: utf-8 -*-
"""Run the addon outside Kodi with stubbed xbmc modules, against live APIs.

Usage: python tools/test_local.py [search <query>]
"""
import os
import re
import sys
import types

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_DIR = os.path.join(BASE, 'weather.metno')

# ---------------------------------------------------------------- strings.po
strings = {}
po_path = os.path.join(ADDON_DIR, 'resources', 'language',
                       'resource.language.en_gb', 'strings.po')
with open(po_path, encoding='utf-8') as f:
    po = f.read()
for m in re.finditer(r'msgctxt "#(\d+)"\nmsgid "(.*)"\nmsgstr "(.*)"', po):
    strings[int(m.group(1))] = m.group(3) or m.group(2)

# ---------------------------------------------------------------- stub state
props = {}
settings = {
    'loc1_name': 'Vuku (Verdal)', 'loc1_lat': '63.7754', 'loc1_lon': '11.7381',
    'loc2_name': 'Verdal (Verdal)', 'loc2_lat': '63.7920', 'loc2_lon': '11.4800',
    # NB: api.met.no returns 403 for placeholder domains like example.com.
    # Override with env KODI_TEST_CONTACT (set empty to test the missing path).
    'contact': os.environ.get('KODI_TEST_CONTACT', 'tommy.leonhardsen@q-free.com'),
}

core = {284: 'No results found', 396: 'Select location', 14024: 'Enter location'}
for i, n in enumerate(['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                       'Friday', 'Saturday', 'Sunday']):
    core[11 + i] = n
    core[41 + i] = n[:3]
for i, n in enumerate(['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                       'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']):
    core[71 + i] = n

# ---------------------------------------------------------------- xbmc stubs
xbmc = types.ModuleType('xbmc')
xbmc.LOGDEBUG, xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 0, 1, 2, 3
xbmc.log = lambda msg, level=0: print('  [log:%i] %s' % (level, msg))
xbmc.getRegion = lambda k: {'tempunit': '°C', 'speedunit': 'm/s',
                            'time': '%H:%M:%S', 'dateshort': '%d.%m.%Y'}[k]
xbmc.getLocalizedString = lambda i: core.get(i, 'CORE#%i' % i)
xbmc.getInfoLabel = lambda label: ''
xbmc.executebuiltin = lambda cmd: print('  [builtin] %s' % cmd)


class Monitor:
    def abortRequested(self):
        return False

    def waitForAbort(self, t):
        import time
        time.sleep(min(t, 1))
        return False


class Keyboard:
    def __init__(self, default='', heading='', hidden=False):
        self.text = sys.argv[2] if len(sys.argv) > 2 else 'Vuku'

    def doModal(self):
        pass

    def isConfirmed(self):
        return True

    def getText(self):
        return self.text


xbmc.Monitor = Monitor
xbmc.Keyboard = Keyboard

xbmcaddon = types.ModuleType('xbmcaddon')


class Addon:
    def __init__(self, *a):
        pass

    def getAddonInfo(self, key):
        return {'id': 'weather.metno', 'name': 'Yr (MET Norway)',
                'version': '1.0.0', 'path': ADDON_DIR,
                'icon': os.path.join(ADDON_DIR, 'resources', 'icon.png')}[key]

    def getLocalizedString(self, i):
        return strings.get(i, 'ADDON#%i' % i)

    def getSettingString(self, key):
        return settings.get(key, '')

    def setSettingString(self, key, value):
        settings[key] = value
        print('  [setting] %s = %s' % (key, value))


xbmcaddon.Addon = Addon

xbmcgui = types.ModuleType('xbmcgui')


class Window:
    def __init__(self, _id):
        pass

    def setProperty(self, key, value):
        props[key] = value

    def clearProperty(self, key):
        props.pop(key, None)


class ListItem:
    def __init__(self, label='', label2=''):
        self.label, self.label2 = label, label2


class Dialog:
    def ok(self, heading, line):
        print('  [dialog.ok] %s: %s' % (heading, line))

    def notification(self, heading, message, icon=None, time=5000):
        print('  [notification] %s: %s' % (heading, message))

    def select(self, heading, items, useDetails=False):
        print('  [dialog.select] %s' % heading)
        for i, item in enumerate(items):
            print('    %i: %s | %s' % (i, item.label, item.label2))
        return 0 if items else -1


xbmcgui.Window = Window
xbmcgui.ListItem = ListItem
xbmcgui.Dialog = Dialog
xbmcgui.NOTIFICATION_WARNING = 'warning'
xbmcgui.NOTIFICATION_INFO = 'info'

xbmcvfs = types.ModuleType('xbmcvfs')
xbmcvfs.translatePath = lambda p: p

for name, mod in (('xbmc', xbmc), ('xbmcaddon', xbmcaddon),
                  ('xbmcgui', xbmcgui), ('xbmcvfs', xbmcvfs)):
    sys.modules[name] = mod

# ---------------------------------------------------------------- run
sys.path.insert(0, os.path.join(ADDON_DIR, 'resources', 'lib'))
import metno  # noqa: E402

if len(sys.argv) > 1 and sys.argv[1] == 'search':
    metno.Main('loc1')
else:
    metno.Main('1')
    print('\n%i window properties set' % len(props))

    def show(pattern):
        rx = re.compile(pattern)
        for key in sorted(props):
            if rx.match(key):
                print('  %-28s = %s' % (key, props[key]))

    print('\n--- Current / Forecast / Today ---')
    show(r'(Current|Forecast|Today)\.')
    print('\n--- Days (legacy) ---')
    show(r'Day\d')
    print('\n--- Daily 1-2 (extended) ---')
    show(r'Daily\.[12]\.')
    print('\n--- Hourly 1-3 ---')
    show(r'Hourly\.[123]\.')
    print('\n--- Window ---')
    show(r'(Locations|Location\d|WeatherProvider)')

    missing = [k for k in ('Current.IsFetched', 'Daily.IsFetched', 'Hourly.IsFetched',
                           'Today.IsFetched', 'Forecast.IsFetched') if k not in props]
    if missing:
        print('\nFAILED, missing: %s' % missing)
        sys.exit(1)
    print('\nOK')
