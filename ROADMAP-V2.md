# Norweather — V2 Roadmap (international)

V1 (the current `1.2.x` line) is the **Norwegian** release: Norwegian-first
README/UI, location search via Kartverket only. It works and is published.

V2 makes Norweather **international** — usable and discoverable for the large
Yr/MET audience abroad (UK, Australia, …) — **without weakening** the thing it
was built for: the best Norwegian place-name coverage anywhere.

> Guiding principle: **Norwegian coverage is non-negotiable and keeps priority.**
> Global reach is *added on top*, never at the expense of finding Vuku.

---

## 1. Hybrid location search (the headline feature, top priority)

Today: search = Kartverket only (Norway). Forecast = MET (already global).
V2: search **both** sources and merge.

- **Kartverket** (`ws.geonorge.no`) — Norwegian place-name register. Catches the
  tiniest places (Vuku, Stor-Vuku, …). **Always queried, always shown first.**
- **Open-Meteo Geocoding** (`geocoding-api.open-meteo.com`) — global, free, no
  API key. Catches Sydney, Tokyo, Chipping Norton, …
- **Merge rules (Norwegian priority):**
  1. Run both queries (in parallel where possible).
  2. List **Kartverket hits first**, then global hits.
  3. De-duplicate: if a global hit is in Norway and coincides (≈same lat/lon)
     with a Kartverket hit, drop the global duplicate — keep the richer
     Norwegian entry.
  4. Never let a global result push a Norwegian match out of view.
- **Localisation:** pass the Kodi UI language (`xbmc.getLanguage(ISO_639_1)`,
  e.g. `en`, `nb`) to Open-Meteo so results read in the user's language.
- **Labelling:** show country/region so duplicates are distinguishable, e.g.
  `Sydney · NSW · AU`, `Bergen · Vestland · NO`, `London · Gausdal (NO)`.
- Stored per location: name, lat, lon (4 decimals, MET requirement) — same as
  today, so the forecast path is unchanged.

**Acceptance:** searching `Vuku` still returns the Verdal bygd first; searching
`Sydney` returns Sydney, AU; searching `Bergen` returns the Norwegian Bergen
before any foreign Bergen.

## 2. English-first documentation & metadata

- Translate `README.md` to **English** (primary), keep a Norwegian section or
  `README.no.md`.
- `addon.xml`: English summary/description already present — refine for an
  international audience; keep the "Are you using that Norwegian service?" hook.
- Screenshots in the repo / release.

## 3. UI language coverage

- Strings already exist in `en_gb` + `nb_no`. Consider adding common ones
  (de, fr, es, sv, da) — the condition texts are short and high-value.
- Make sure the contact-e-mail prompt and search dialog read well in English.

## 4. Distribution

- **GitHub Releases** (started in V1) — attach the zip per version.
- **Self-hosted repo add-on** (`repository.norweather`) so users get
  auto-updates without manual zip installs.
- **Official Kodi repo** PR (`repo-scripts`, branch per Kodi version) once V2 is
  stable — no MET-Norway/yr service exists there today, so it fills a real gap.
  Mind the trademark guidance (unofficial; attribute MET/Yr, don't imply
  affiliation).

## 5. Nice-to-haves (not blocking)

- Optional setting: search scope (Norway-only / Worldwide / Both[default]).
- Kodi 22 (Estuary custom icon path) → ship the official Yr symbol set as an
  optional prettier icon pack. (On Kodi 21 Estuary the icon source is hardcoded
  to `resource.images.weathericons.default`, so this only applies to 22+.)
- Air-quality / UV / alerts endpoints from MET.
- Cache last good forecast to ride out brief network/API hiccups.

## Versioning

- V1 milestone: **`1.2.2`** (this release) — Norwegian.
- V2 target: **`2.0.0`** — hybrid global search + English-first.

## Notes / constraints (carry-over learnings)

- MET requires an identifying contact e-mail in the User-Agent (placeholder
  domains like `example.com` get HTTP 403). Already enforced.
- On Kodi 21 Estuary, forecast tile icons come from
  `resource://resource.images.weathericons.default/<OutlookIcon>` — OutlookIcon
  must be a bare `<0-47>.png` filename. Custom icons need Kodi 22+.
- Don't fake missing assets (e.g. emoji) — degrade honestly to `na`.
