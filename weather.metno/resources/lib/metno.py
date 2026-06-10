# -*- coding: utf-8 -*-
"""MET Norway (Yr) weather provider for Kodi.

Forecast data : https://api.met.no/weatherapi/locationforecast/2.0/
Sunrise/sunset: https://api.met.no/weatherapi/sunrise/3.0/
Place search  : https://ws.geonorge.no/stedsnavn/v1/ (Kartverket)
"""
import json
import math
import os
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONNAME = ADDON.getAddonInfo('name')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD = ADDON.getAddonInfo('path')
LANGUAGE = ADDON.getLocalizedString

WINDOW = xbmcgui.Window(12600)

FORECAST_URL = 'https://api.met.no/weatherapi/locationforecast/2.0/complete?%s'
SUNRISE_URL = 'https://api.met.no/weatherapi/sunrise/3.0/sun?%s'
SEARCH_URL = 'https://ws.geonorge.no/stedsnavn/v1/navn?%s'

# Estuary (and most skins) build the forecast tile icons as
# resource://resource.images.weathericons.default/ + OutlookIcon, so the
# OutlookIcon properties must be bare filenames (e.g. "30.png") that exist in
# Kodi's bundled weather-icon pack, and FanartCode the matching 0-47 code.
ICON_RESOURCE = 'resource://resource.images.weathericons.default/%s.png'

TEMPUNIT = xbmc.getRegion('tempunit')
SPEEDUNIT = xbmc.getRegion('speedunit')
TIMEFORMAT = xbmc.getRegion('time').replace(':%S', '').replace('%S', '')
DATEFORMAT = xbmc.getRegion('dateshort')

MAXDAYS = 7
MAXHOURS = 36
MAXLOCATIONS = 5

# MET symbol base code -> (addon string id for the condition text,
# day icon code, night icon code). Icon codes are the standard 0-47 numbering
# used by Kodi's bundled resource.images.weathericons.default pack.
SYMBOLS = {
    'clearsky':                     (32200, '32', '31'),
    'cloudy':                       (32201, '26', '26'),
    'fair':                         (32202, '34', '33'),
    'fog':                          (32203, '20', '20'),
    'heavyrain':                    (32204, '40', '40'),
    'heavyrainandthunder':          (32205, '3', '3'),
    'heavyrainshowers':             (32206, '40', '40'),
    'heavyrainshowersandthunder':   (32207, '38', '38'),
    'heavysleet':                   (32208, '18', '18'),
    'heavysleetandthunder':         (32209, '18', '18'),
    'heavysleetshowers':            (32210, '6', '6'),
    'heavysleetshowersandthunder':  (32211, '6', '6'),
    'heavysnow':                    (32212, '41', '41'),
    'heavysnowandthunder':          (32213, '41', '41'),
    'heavysnowshowers':             (32214, '41', '41'),
    'heavysnowshowersandthunder':   (32215, '41', '41'),
    'lightrain':                    (32216, '9', '9'),
    'lightrainandthunder':          (32217, '4', '4'),
    'lightrainshowers':             (32218, '39', '45'),
    'lightrainshowersandthunder':   (32219, '37', '47'),
    'lightsleet':                   (32220, '6', '6'),
    'lightsleetandthunder':         (32221, '6', '6'),
    'lightsleetshowers':            (32222, '6', '6'),
    'lightssleetshowersandthunder': (32223, '6', '6'),
    'lightsnow':                    (32224, '13', '13'),
    'lightsnowandthunder':          (32225, '13', '13'),
    'lightsnowshowers':             (32226, '14', '46'),
    'lightssnowshowersandthunder':  (32227, '14', '46'),
    'partlycloudy':                 (32228, '30', '29'),
    'rain':                         (32229, '11', '11'),
    'rainandthunder':               (32230, '4', '4'),
    'rainshowers':                  (32231, '39', '45'),
    'rainshowersandthunder':        (32232, '37', '47'),
    'sleet':                        (32233, '18', '18'),
    'sleetandthunder':              (32234, '18', '18'),
    'sleetshowers':                 (32235, '6', '6'),
    'sleetshowersandthunder':       (32236, '6', '6'),
    'snow':                         (32237, '16', '16'),
    'snowandthunder':               (32238, '16', '16'),
    'snowshowers':                  (32239, '14', '46'),
    'snowshowersandthunder':        (32240, '14', '46'),
}


def log(txt, level=xbmc.LOGDEBUG):
    xbmc.log('%s: %s' % (ADDONID, txt), level)


def set_prop(name, value):
    WINDOW.setProperty(name, str(value))


def clear_prop(name):
    WINDOW.clearProperty(name)


def user_agent():
    contact = ADDON.getSettingString('contact').strip()
    agent = 'Kodi-%s/%s' % (ADDONID, ADDONVERSION)
    if contact:
        agent += ' (%s)' % contact
    return agent


def temp_text(celsius):
    """Temperature formatted in the locale unit (extended properties)."""
    if celsius is None:
        return ''
    if TEMPUNIT == '°F':
        value = celsius * 1.8 + 32
    elif TEMPUNIT == 'K':
        value = celsius + 273.15
    else:
        value = celsius
    return '%i%s' % (round(value), TEMPUNIT)


def beaufort(mps):
    for bft, limit in enumerate((0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9,
                                 17.2, 20.8, 24.5, 28.5, 32.7)):
        if mps < limit:
            return bft
    return 12


def speed_text(mps):
    """Wind speed formatted in the locale unit (extended properties)."""
    if mps is None:
        return ''
    unit = SPEEDUNIT
    if unit == 'm/s':
        value = mps
    elif unit == 'mph':
        value = mps * 2.237
    elif unit in ('knots', 'kts'):
        value = mps * 1.9438
    elif unit == 'Beaufort':
        return str(beaufort(mps))
    elif unit == 'ft/s':
        value = mps * 3.281
    elif unit == 'yard/s':
        value = mps * 1.094
    else:
        value = mps * 3.6
        unit = 'km/h'
    return '%i %s' % (round(value), unit)


def wind_dir(degrees):
    """Compass direction, localized by Kodi core strings 71-86 (N..NNW)."""
    if degrees is None:
        return ''
    index = int((degrees % 360 + 11.25) // 22.5) % 16
    return xbmc.getLocalizedString(71 + index)


def feels_like(temp, humidity, windspeed):
    """Apparent temperature (Steadman), input °C / % / m/s, output °C."""
    if temp is None:
        return None
    humidity = humidity or 50.0
    windspeed = windspeed or 0.0
    vapour = (humidity / 100.0) * 6.105 * math.exp(17.27 * temp / (237.7 + temp))
    return temp + 0.33 * vapour - 0.7 * windspeed - 4.0


def symbol_info(code, force_day=False):
    """Return (localized condition text, 0-47 icon code) for a MET symbol_code.

    The icon code maps to Kodi's bundled weather-icon pack. For daily tiles
    (force_day) the day icon is always used.
    """
    if not code:
        return ('', 'na')
    base, _, variant = code.partition('_')
    if base not in SYMBOLS:
        log('unknown symbol code: %s' % code, xbmc.LOGWARNING)
        return (base, 'na')
    string_id, day, night = SYMBOLS[base]
    icon = night if (variant == 'night' and not force_day) else day
    return (LANGUAGE(string_id), icon)


def short_date(date):
    fmt = DATEFORMAT
    for token in ('%Y-', '-%Y', '/%Y', '%Y/', '.%Y', '%Y.', '%Y'):
        fmt = fmt.replace(token, '')
    return date.strftime(fmt or '%d.%m')


def parse_entries(data):
    entries = []
    for item in data['properties']['timeseries']:
        utc = datetime.strptime(item['time'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        block = item['data']
        entries.append({'utc': utc,
                        'local': utc.astimezone(),
                        'instant': block['instant']['details'],
                        'next1': block.get('next_1_hours'),
                        'next6': block.get('next_6_hours'),
                        'next12': block.get('next_12_hours')})
    return entries


def summary_code(block):
    if not block:
        return None
    return block.get('summary', {}).get('symbol_code')


class Main:

    def __init__(self, mode):
        log('version %s started: %s' % (ADDONVERSION, mode), xbmc.LOGINFO)
        self.monitor = xbmc.Monitor()
        try:
            if mode.startswith('loc'):
                self.find_location(mode)
            else:
                self.fetch(mode)
            self.refresh_locations()
        except Exception:
            # Never raise: an unhandled exception makes Kodi pop a scary
            # "<addon> error - Check the log" dialog. Log the traceback for
            # diagnosis and fail quietly instead.
            log('unhandled error:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
        log('finished', xbmc.LOGINFO)

    def contact_ok(self):
        """MET requires an identifying contact in the User-Agent. Make it a
        hard requirement and tell the user clearly when it is missing."""
        contact = ADDON.getSettingString('contact').strip()
        if '@' in contact and '.' in contact.split('@')[-1]:
            return True
        log('no contact e-mail configured', xbmc.LOGWARNING)
        self.clear_props()
        set_prop('Current.Location', ADDONNAME)
        set_prop('Current.Condition', LANGUAGE(32123))  # short hint on the screen
        xbmcgui.Dialog().notification(ADDONNAME, LANGUAGE(32122),
                                      xbmcgui.NOTIFICATION_WARNING, 8000)
        return False

    def get_json(self, url, retries=3):
        request = urllib.request.Request(url, headers={'User-Agent': user_agent(),
                                                       'Accept': 'application/json'})
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    return json.loads(response.read().decode('utf-8'))
            except Exception as error:  # URLError, timeout, JSON errors
                log('request failed (%s): %s' % (url, error), xbmc.LOGWARNING)
                if attempt < retries - 1 and self.monitor.waitForAbort(5):
                    return None
        return None

    # ------------------------------------------------------------ location

    def find_location(self, slot):
        keyboard = xbmc.Keyboard('', xbmc.getLocalizedString(14024), False)
        keyboard.doModal()
        if not (keyboard.isConfirmed() and keyboard.getText()):
            return
        query = keyboard.getText()
        log('searching for: %s' % query, xbmc.LOGINFO)
        params = urllib.parse.urlencode({'sok': query, 'fuzzy': 'true',
                                         'utkoordsys': '4258',
                                         'treffPerSide': '30', 'side': '1'})
        data = self.get_json(SEARCH_URL % params, retries=1)
        hits = data.get('navn') if data else None
        dialog = xbmcgui.Dialog()
        if not hits:
            dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))
            return
        items = []
        for hit in hits:
            kommune = hit['kommuner'][0]['kommunenavn'] if hit.get('kommuner') else ''
            fylke = hit['fylker'][0]['fylkesnavn'].split(' - ')[0] if hit.get('fylker') else ''
            point = hit.get('representasjonspunkt') or {}
            listitem = xbmcgui.ListItem(hit['skrivemåte'],
                                        '%s — %s, %s [%.4f / %.4f]'
                                        % (hit.get('navneobjekttype', ''), kommune, fylke,
                                           point.get('nord', 0), point.get('øst', 0)))
            items.append(listitem)
        selected = dialog.select(xbmc.getLocalizedString(396), items, useDetails=True)
        if selected == -1:
            return
        hit = hits[selected]
        point = hit['representasjonspunkt']
        kommune = hit['kommuner'][0]['kommunenavn'] if hit.get('kommuner') else ''
        name = hit['skrivemåte']
        if kommune and kommune != name:
            name += ' (%s)' % kommune
        ADDON.setSettingString('%s_name' % slot, name)
        # MET terms: max 4 decimals on coordinates
        ADDON.setSettingString('%s_lat' % slot, '%.4f' % point['nord'])
        ADDON.setSettingString('%s_lon' % slot, '%.4f' % point['øst'])
        log('selected: %s (%.4f / %.4f)' % (name, point['nord'], point['øst']), xbmc.LOGINFO)

    # ------------------------------------------------------------ forecast

    def fetch(self, mode):
        if not self.contact_ok():
            return
        name = ADDON.getSettingString('loc%s_name' % mode)
        lat = ADDON.getSettingString('loc%s_lat' % mode)
        lon = ADDON.getSettingString('loc%s_lon' % mode)
        if not lat and mode != '1':
            log('location %s not set, falling back to location 1' % mode)
            name = ADDON.getSettingString('loc1_name')
            lat = ADDON.getSettingString('loc1_lat')
            lon = ADDON.getSettingString('loc1_lon')
        if not lat:
            log('no location configured', xbmc.LOGINFO)
            self.clear_props()
            return
        params = urllib.parse.urlencode({'lat': lat, 'lon': lon})
        data = self.get_json(FORECAST_URL % params)
        if not data:
            log('failed to fetch forecast', xbmc.LOGERROR)
            self.clear_props()
            return
        entries = parse_entries(data)
        if not entries:
            self.clear_props()
            return
        self.set_current(name, lat, lon, entries)
        self.set_daily(entries)
        self.set_hourly(entries)
        self.set_sun(lat, lon)

    def set_current(self, name, lat, lon, entries):
        entry = entries[0]
        details = entry['instant']
        code = (summary_code(entry['next1']) or summary_code(entry['next6'])
                or summary_code(entry['next12']))
        condition, icon = symbol_info(code)
        temp = details.get('air_temperature')
        humidity = details.get('relative_humidity')
        windspeed = details.get('wind_speed')
        # legacy properties: plain °C / km/h numbers, Kodi converts to locale
        set_prop('Current.Location', name)
        set_prop('Current.Condition', condition)
        set_prop('Current.Temperature', round(temp) if temp is not None else '')
        set_prop('Current.Humidity', round(humidity) if humidity is not None else '')
        set_prop('Current.Wind', round((windspeed or 0) * 3.6))
        set_prop('Current.WindDirection', wind_dir(details.get('wind_from_direction')))
        set_prop('Current.FeelsLike', round(feels_like(temp, humidity, windspeed))
                 if temp is not None else '')
        set_prop('Current.DewPoint', round(details.get('dew_point_temperature', temp or 0)))
        set_prop('Current.UVIndex', round(details.get('ultraviolet_index_clear_sky', 0)))
        set_prop('Current.OutlookIcon', '%s.png' % icon)
        set_prop('Current.ConditionIcon', ICON_RESOURCE % icon)
        set_prop('Current.FanartCode', icon)
        # extended properties: pre-formatted with locale units
        set_prop('Current.WindSpeed', speed_text(windspeed))
        gust = details.get('wind_speed_of_gust')
        set_prop('Current.WindGust', speed_text(gust) if gust else '')
        set_prop('Current.Pressure', '%i hPa' % round(details.get('air_pressure_at_sea_level', 0)))
        set_prop('Current.Cloudiness', '%i%%' % round(details.get('cloud_area_fraction', 0)))
        precip = (entry['next1'] or {}).get('details', {}).get('precipitation_amount')
        set_prop('Current.Precipitation', '%.1f mm' % precip if precip is not None else '')
        set_prop('Forecast.City', name.split(' (')[0])
        set_prop('Forecast.Country', 'Norge')
        set_prop('Forecast.Latitude', lat)
        set_prop('Forecast.Longitude', lon)
        set_prop('Forecast.Updated',
                 datetime.now().strftime('%s %s' % (DATEFORMAT, TIMEFORMAT)))
        set_prop('Current.IsFetched', 'true')
        set_prop('Forecast.IsFetched', 'true')

    def set_daily(self, entries):
        days = {}
        order = []
        for entry in entries:
            date = entry['local'].date()
            if date not in days:
                days[date] = []
                order.append(date)
            days[date].append(entry)

        # precipitation: walk the timeline so hourly and 6-hourly steps
        # are not double counted
        precip = dict.fromkeys(order, 0.0)
        for index, entry in enumerate(entries):
            if index + 1 < len(entries):
                step = (entries[index + 1]['utc'] - entry['utc']).total_seconds() / 3600
            else:
                step = 6
            if step <= 1 and entry['next1']:
                amount = entry['next1'].get('details', {}).get('precipitation_amount')
            elif entry['next6']:
                amount = entry['next6'].get('details', {}).get('precipitation_amount')
            else:
                amount = 0
            precip[entry['local'].date()] += amount or 0

        for count, date in enumerate(order[:MAXDAYS]):
            daylist = days[date]
            temps = [e['instant']['air_temperature'] for e in daylist
                     if e['instant'].get('air_temperature') is not None]
            for entry in daylist:
                details = (entry['next6'] or {}).get('details', {})
                for key in ('air_temperature_max', 'air_temperature_min'):
                    if details.get(key) is not None:
                        temps.append(details[key])
            if not temps:
                break
            high, low = max(temps), min(temps)

            # outlook: 12h summary from the morning, else 6h around noon
            pick = None
            for entry in daylist:
                if 5 <= entry['local'].hour <= 9 and entry['next12']:
                    pick = entry['next12']
                    break
            if not pick:
                for entry in daylist:
                    if 10 <= entry['local'].hour <= 14 and entry['next6']:
                        pick = entry['next6']
                        break
            if not pick:
                first = daylist[0]
                pick = first['next6'] or first['next12'] or first['next1']
            condition, icon = symbol_info(summary_code(pick), force_day=True)

            windiest = max(daylist, key=lambda e: e['instant'].get('wind_speed') or 0)
            maxwind = windiest['instant'].get('wind_speed')
            humidities = [e['instant']['relative_humidity'] for e in daylist
                          if e['instant'].get('relative_humidity') is not None]

            # legacy Day0..Day6
            set_prop('Day%i.Title' % count, xbmc.getLocalizedString(11 + date.weekday()))
            set_prop('Day%i.HighTemp' % count, round(high))
            set_prop('Day%i.LowTemp' % count, round(low))
            set_prop('Day%i.Outlook' % count, condition)
            set_prop('Day%i.OutlookIcon' % count, '%s.png' % icon)
            set_prop('Day%i.FanartCode' % count, icon)
            # extended Daily.1..Daily.7
            index = count + 1
            set_prop('Daily.%i.ShortDay' % index, xbmc.getLocalizedString(41 + date.weekday()))
            set_prop('Daily.%i.LongDay' % index, xbmc.getLocalizedString(11 + date.weekday()))
            set_prop('Daily.%i.ShortDate' % index, short_date(date))
            set_prop('Daily.%i.HighTemperature' % index, temp_text(high))
            set_prop('Daily.%i.LowTemperature' % index, temp_text(low))
            set_prop('Daily.%i.Outlook' % index, condition)
            set_prop('Daily.%i.OutlookIcon' % index, '%s.png' % icon)
            set_prop('Daily.%i.FanartCode' % index, icon)
            set_prop('Daily.%i.WindSpeed' % index, speed_text(maxwind))
            set_prop('Daily.%i.WindDirection' % index,
                     wind_dir(windiest['instant'].get('wind_from_direction')))
            set_prop('Daily.%i.Precipitation' % index, '%.1f mm' % precip[date])
            set_prop('Daily.%i.Humidity' % index,
                     '%i%%' % round(sum(humidities) / len(humidities)) if humidities else '')
        set_prop('Daily.IsFetched', 'true')

    def set_hourly(self, entries):
        count = 0
        for entry in entries:
            if not entry['next1']:
                continue
            count += 1
            if count > MAXHOURS:
                break
            details = entry['instant']
            condition, icon = symbol_info(summary_code(entry['next1']))
            temp = details.get('air_temperature')
            humidity = details.get('relative_humidity')
            windspeed = details.get('wind_speed')
            set_prop('Hourly.%i.Time' % count, entry['local'].strftime(TIMEFORMAT))
            set_prop('Hourly.%i.ShortDate' % count, short_date(entry['local'].date()))
            set_prop('Hourly.%i.Outlook' % count, condition)
            set_prop('Hourly.%i.OutlookIcon' % count, '%s.png' % icon)
            set_prop('Hourly.%i.FanartCode' % count, icon)
            set_prop('Hourly.%i.Temperature' % count, temp_text(temp))
            set_prop('Hourly.%i.FeelsLike' % count,
                     temp_text(feels_like(temp, humidity, windspeed)))
            set_prop('Hourly.%i.DewPoint' % count,
                     temp_text(details.get('dew_point_temperature')))
            set_prop('Hourly.%i.Humidity' % count,
                     '%i%%' % round(humidity) if humidity is not None else '')
            set_prop('Hourly.%i.Pressure' % count,
                     '%i hPa' % round(details.get('air_pressure_at_sea_level', 0)))
            set_prop('Hourly.%i.WindSpeed' % count, speed_text(windspeed))
            set_prop('Hourly.%i.WindDirection' % count,
                     wind_dir(details.get('wind_from_direction')))
            precipitation = entry['next1'].get('details', {}).get('precipitation_amount')
            set_prop('Hourly.%i.Precipitation' % count,
                     '%.1f mm' % precipitation if precipitation is not None else '')
        set_prop('Hourly.IsFetched', 'true')

    def set_sun(self, lat, lon):
        now = datetime.now().astimezone()
        offset = now.strftime('%z')
        params = urllib.parse.urlencode({'lat': lat, 'lon': lon,
                                         'date': now.strftime('%Y-%m-%d'),
                                         'offset': '%s:%s' % (offset[:3], offset[3:])})
        data = self.get_json(SUNRISE_URL % params, retries=1)
        if not data:
            return
        properties = data.get('properties', {})
        for prop, key in (('Today.Sunrise', 'sunrise'), ('Today.Sunset', 'sunset')):
            stamp = (properties.get(key) or {}).get('time')
            if stamp:
                set_prop(prop, datetime.fromisoformat(stamp).strftime(TIMEFORMAT))
            else:
                clear_prop(prop)  # midnight sun / polar night
        set_prop('Today.IsFetched', 'true')

    # ------------------------------------------------------------ window

    def clear_props(self):
        set_prop('Current.Condition', 'N/A')
        set_prop('Current.Temperature', '0')
        set_prop('Current.Wind', '0')
        set_prop('Current.WindDirection', 'N/A')
        set_prop('Current.Humidity', '0')
        set_prop('Current.FeelsLike', '0')
        set_prop('Current.UVIndex', '0')
        set_prop('Current.DewPoint', '0')
        set_prop('Current.OutlookIcon', 'na.png')
        set_prop('Current.FanartCode', 'na')
        for count in range(MAXDAYS):
            set_prop('Day%i.Title' % count, 'N/A')
            set_prop('Day%i.HighTemp' % count, '0')
            set_prop('Day%i.LowTemp' % count, '0')
            set_prop('Day%i.Outlook' % count, 'N/A')
            set_prop('Day%i.OutlookIcon' % count, 'na.png')
            set_prop('Day%i.FanartCode' % count, 'na')
        for name in ('Current.IsFetched', 'Forecast.IsFetched', 'Today.IsFetched',
                     'Daily.IsFetched', 'Hourly.IsFetched'):
            clear_prop(name)

    def refresh_locations(self):
        count = 0
        for index in range(1, MAXLOCATIONS + 1):
            name = ADDON.getSettingString('loc%i_name' % index)
            if name:
                count += 1
                set_prop('Location%i' % count, name)
        for index in range(count + 1, MAXLOCATIONS + 1):
            clear_prop('Location%i' % index)
        set_prop('Locations', count)
        set_prop('WeatherProvider', 'MET Norway (yr.no) v%s' % ADDONVERSION)
        set_prop('WeatherProviderLogo',
                 xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'icon.png')))
