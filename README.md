# Norweather — norsk vær for Kodi

### *Weather you want it or not!* ☔

Vær-addon for Kodi (addon-id `weather.metno`) som henter varsel rett fra
**Meteorologisk institutt** (api.met.no — samme data som yr.no) og søker steder
via **Kartverkets stedsnavnregister** (ws.geonorge.no). Finner alt fra Oslo til
Vuku.

> *"Are you using that Norwegian service?"* — Jeremy Clarkson

- Ingen API-nøkkel nødvendig (MET krever bare en identifiserende `User-Agent`)
- 7-dagers varsel + 36 timers timesvarsel + soloppgang/-nedgang
- Norsk og engelsk oversettelse
- Kun Python-standardbibliotek — ingen ekstra modul-avhengigheter
- **Alt er pakket i ZIP-en, inkludert værikonene.** Det eneste som hentes
  over nett er selve værmeldingen fra api.met.no.

## Installasjon på Xbox

1. Kopier `weather.metno-<versjon>.zip` til Xboxen — enkleste vei er en
   nettverksdeling (SMB) eller en USB-pinne, eller last den ned i Edge på
   Xboxen.
2. I Kodi: *Settings → System → Add-ons → Unknown sources* = **På**
3. *Settings → Add-ons → Install from zip file* → velg zip-fila
   (ingen avhengigheter hentes — alt ligger i fila)
4. *Settings → Interface (eller Services) → Weather → Service for weather
   information* → velg **Yr (MET Norway)**
5. Åpne addon-innstillingene → *Steder* → *Sted 1* → søk f.eks. `Vuku`
6. (Valgfritt, men god folkeskikk mot MET) Under *Avansert*: legg inn
   kontakt-eposten din — den sendes i `User-Agent` til api.met.no.
   **NB:** ikke bruk plassholder-adresser (`@example.com`) — MET svarer 403.

## Celsius i stedet for Fahrenheit

Temperatur, vind og dato styres av Kodi sine **regionsinnstillinger**, ikke
av addonet (Kodi konverterer verdiene selv). Står Kodi i amerikansk region
vises °F, mph og MM/DD. Fiks:

- *Settings → Interface → Regional → Temperature unit* → **Celsius**
- *Settings → Interface → Regional → Speed unit* → **metre per second**
  (eller km/h)
- (Valgfritt for norsk dato/klokke) sett *Region* til et europeisk/norsk
  oppsett, eller juster *Short date format* og *Time format* (24-timers).

## Kontakt-epost er påkrevd

MET krever en identifiserende `User-Agent` med kontaktinfo. Addonet **krever**
derfor at du legger inn en e-post under *innstillinger → Avansert*. Uten den
hentes ikke været — i stedet vises en tydelig melding om å fylle den inn.
Ikke bruk plassholder-adresser (`@example.com`) — MET svarer 403.

## Værikoner

Ikonene er MET/Yr sine egne offisielle værsymboler (MIT-lisens), hentet fra
[metno/weathericons](https://github.com/metno/weathericons) og pakket i
`resources/icons/` (navngitt etter MET sine `symbol_code`, f.eks.
`partlycloudy_day.png`). Ved oppstart peker addonet skinnets
`WeatherOutlookIcon.path` på denne mappa, så ikonene vises uten noen ekstern
ressurspakke. `na.png` er et eget «ingen data»-ikon.

## Utvikling

```
python tools/test_local.py            # kjør addonet utenfor Kodi mot live API-er
python tools/test_local.py search Vuku  # test stedssøket
python tools/make_icon.py             # regenerer resources/icon.png
python tools/build_zip.py             # bygg installerbar zip
```

`tools/test_local.py` stubber `xbmc`-modulene og skriver ut alle
window-properties addonet setter, så endringer kan verifiseres uten Xbox.

## API-er som brukes

| API | Bruk | Auth |
|---|---|---|
| [Locationforecast 2.0](https://api.met.no/weatherapi/locationforecast/2.0/documentation) | varsel | kun User-Agent |
| [Sunrise 3.0](https://api.met.no/weatherapi/sunrise/3.0/documentation) | sol opp/ned | kun User-Agent |
| [Kartverket stedsnavn](https://ws.geonorge.no/stedsnavn/v1/) | stedssøk | ingen |

Frost (frost.met.no) er *historiske observasjoner* og brukes ikke av
addonet — Kodi sine vær-skjermer viser bare varsel.

## Lisens og kreditering

Koden er **MIT-lisensiert** (se [`LICENSE`](LICENSE)).

- Værvarsel: **Meteorologisk institutt (MET Norway) / yr.no** — data under
  CC BY 4.0 / NLOD.
- Stedssøk: **Kartverket** (ws.geonorge.no) — data under NLOD / CC BY 4.0.
- Værikoner: MET Norway sitt [weathericons](https://github.com/metno/weathericons)-sett
  (MIT), se `weather.metno/resources/icons/License.txt`.

Dette er et uoffisielt addon og er ikke tilknyttet MET Norway eller NRK/Yr.
