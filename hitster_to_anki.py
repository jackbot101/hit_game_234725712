#!/usr/bin/env python3
"""Exportify-CSV -> hitster.apkg (Anki) + songs.json (Web-App).

Aufruf:  python hitster_to_anki.py playlist.csv --base-url https://DEINNAME.github.io/hitster/
Optional: --offline  (kein MusicBrainz, Jahr = Album-Datum von Spotify)
Benötigt: pip install genanki
"""
import argparse, csv, json, os, re, time, urllib.parse, urllib.request
import genanki

UA = "HitsterDeckBuilder/1.0 (privat)"

def clean_title(t):
    t = re.sub(r"\s*[-–]\s*(\d{4}\s+)?(Re-?master(ed)?|Single Version|Mono|Stereo)\b.*$", "", t, flags=re.I)
    t = re.sub(r"\s*\((\d{4}\s+)?Re-?master(ed)?[^)]*\)", "", t, flags=re.I)
    return t.strip()

def mb_year(isrc, cache):
    """Frühestes Veröffentlichungsjahr laut MusicBrainz (per ISRC)."""
    if not isrc:
        return None
    if isrc in cache:
        return cache[isrc]
    url = "https://musicbrainz.org/ws/2/recording?fmt=json&limit=25&query=" + urllib.parse.quote("isrc:" + isrc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = json.load(urllib.request.urlopen(req, timeout=20))
        years = [int(r["first-release-date"][:4]) for r in data.get("recordings", [])
                 if r.get("first-release-date")]
        cache[isrc] = min(years) if years else None
    except Exception as e:
        print("   MusicBrainz-Fehler:", e)
        return None
    time.sleep(1.1)  # Limit: 1 Anfrage pro Sekunde
    return cache[isrc]

class HitNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--base-url", required=True, help="z. B. https://name.github.io/hitster/")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    base = a.base_url.rstrip("/") + "/"

    cache_file = "mb_cache.json"
    cache = json.load(open(cache_file)) if os.path.exists(cache_file) else {}

    model = genanki.Model(
        1607392319, "Hitster",
        fields=[{"name": "Track"}, {"name": "Interpret"}, {"name": "Titel"}, {"name": "Jahr"}],
        templates=[{
            "name": "Karte",
            "qfmt": '<img src="https://api.qrserver.com/v1/create-qr-code/?size=300x300&data='
                    + base + '?t={{Track}}">',
            "afmt": '{{FrontSide}}<hr id="answer"><div class="y">{{Jahr}}</div>'
                    '<b>{{Interpret}}</b><br>{{Titel}}',
        }],
        css=".card{text-align:center;font-family:sans-serif}.y{font-size:48px;font-weight:bold}",
    )
    deck = genanki.Deck(2059400110, "Hitster")
    songs = []

    with open(a.csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for n, r in enumerate(rows, 1):
        tid = r["Track URI"].replace("spotify:track:", "").strip()
        title = clean_title(r["Track Name"])
        artist = r["Artist Name(s)"].replace(";", ", ")
        year = int(r["Release Date"][:4])
        if not a.offline:
            y = mb_year(r.get("ISRC", ""), cache)
            if y and y < year:
                print(f"[{n}/{len(rows)}] {title}: {year} -> {y}")
                year = y
            else:
                print(f"[{n}/{len(rows)}] {title}: {year}")
            json.dump(cache, open(cache_file, "w"))
        songs.append({"id": tid, "title": title, "artist": artist, "year": year})
        deck.add_note(HitNote(model=model, fields=[tid, artist, title, str(year)]))

    genanki.Package(deck).write_to_file("hitster.apkg")
    json.dump(songs, open("songs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nFertig: {len(songs)} Songs -> hitster.apkg und songs.json")

if __name__ == "__main__":
    main()
