"""Télécharge des photos réelles de maisons/quartiers de Kinshasa depuis Wikimedia Commons
(licences libres uniquement) dans seed_photos/, avec les crédits dans seed_photos/credits.json.

Usage : python fetch_photos.py [nombre_max]   (nécessite l'accès réseau à commons.wikimedia.org)
Puis  : python seed.py --reset                (utilise ces photos au lieu des illustrations)
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_photos")
QUERIES = ["Kinshasa house", "Kinshasa villa", "Kinshasa Gombe building", "Kinshasa residential", "Kinshasa Limete",
           "Kinshasa Ngaliema", "Lubumbashi house", "Goma house"]
FREE = re.compile(r"^(CC0|CC BY|CC BY-SA|Public domain|PD)", re.I)
UA = {"User-Agent": "NdakuDemo/1.0 (https://github.com/14juanito/Personal-finance-tracker)"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def main(limit=60):
    os.makedirs(OUT, exist_ok=True)
    credits, seen = {}, set()
    for q in QUERIES:
        params = {"action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": q, "gsrlimit": 30,
                  "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 1200, "format": "json"}
        data = json.loads(get(API + "?" + urllib.parse.urlencode(params)))
        for p in data.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata", {})
            lic = meta.get("LicenseShortName", {}).get("value", "")
            if (ii.get("mime") not in ("image/jpeg",) or not FREE.match(lic) or ii.get("width", 0) < 900
                    or ii.get("width", 0) < ii.get("height", 1) or p["title"] in seen):
                continue
            seen.add(p["title"])
            name = f"kin{len(credits):03d}.jpg"
            try:
                with open(os.path.join(OUT, name), "wb") as f:
                    f.write(get(ii["thumburl"]))
            except Exception as e:  # noqa: BLE001
                print("skip", p["title"], e)
                continue
            credits[name] = {"title": p["title"], "license": lic, "page": ii.get("descriptionurl"),
                             "author": re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", "?"))}
            print(name, lic, p["title"])
            if len(credits) >= limit:
                break
        if len(credits) >= limit:
            break
    with open(os.path.join(OUT, "credits.json"), "w") as f:
        json.dump(credits, f, ensure_ascii=False, indent=1)
    print(f"{len(credits)} photos → {OUT}. Vérifiez-les visuellement (certaines peuvent ne pas être des maisons) avant seed.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 60)
