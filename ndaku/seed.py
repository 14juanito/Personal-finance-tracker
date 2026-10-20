"""Données de démonstration : comptes, annonces (photos générées) et avis.

Passe par le même contrôle anti-fraude d'images que l'application réelle.
"""
import io
import json
import os
import random
import time

from PIL import Image, ImageDraw, ImageFilter
from werkzeug.security import generate_password_hash

import antifraud as af
import app as appmod
import db as dbm

DEMO_PASSWORD = "Ndaku2026"
PHOTOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_photos")


def real_photos():
    """Photos réelles (fetch_photos.py) si présentes, sinon None → illustrations procédurales."""
    if not os.path.isdir(PHOTOS):
        return None
    files = sorted(f for f in os.listdir(PHOTOS) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    return [os.path.join(PHOTOS, f) for f in files] or None


def render_house(seed, w=1200, h=800):
    """Illustration procédurale unique (ciel, maison, arbres, bruit) — pas de photos sous licence."""
    r = random.Random(seed)
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    top, bot = (r.randint(90, 170), r.randint(150, 210), r.randint(200, 255)), (255, r.randint(200, 245), r.randint(170, 230))
    for y in range(int(h * 0.7)):
        t = y / (h * 0.7)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
    d.rectangle([0, int(h * 0.7), w, h], fill=(r.randint(60, 130), r.randint(120, 170), r.randint(50, 100)))
    for _ in range(r.randint(1, 4)):  # nuages
        cx, cy = r.randint(0, w), r.randint(20, int(h * 0.35))
        for _ in range(5):
            rx, ry = r.randint(40, 110), r.randint(20, 45)
            ox = cx + r.randint(-80, 80)
            d.ellipse([ox - rx, cy - ry, ox + rx, cy + ry], fill=(255, 255, 255))
    hw, hh = r.randint(int(w * .3), int(w * .6)), r.randint(int(h * .22), int(h * .4))
    x0, y1 = r.randint(30, w - hw - 30), int(h * .85) - r.randint(0, 40)
    y0 = y1 - hh
    wall = tuple(r.randint(120, 245) for _ in range(3))
    d.rectangle([x0, y0, x0 + hw, y1], fill=wall)
    roof = (r.randint(60, 200), r.randint(30, 90), r.randint(20, 80))
    if r.random() < .5:
        d.polygon([(x0 - 25, y0), (x0 + hw // 2, y0 - r.randint(80, 190)), (x0 + hw + 25, y0)], fill=roof)
    else:
        d.rectangle([x0 - 20, y0 - r.randint(25, 60), x0 + hw + 20, y0], fill=roof)
    cols, rows = r.randint(2, 5), r.randint(1, 3)
    for i in range(cols):
        for j in range(rows):
            wx = x0 + 30 + i * (hw - 60) // cols
            wy = y0 + 25 + j * (hh - 50) // rows
            d.rectangle([wx, wy, wx + 42, wy + 52], fill=(r.randint(30, 120), r.randint(90, 190), r.randint(150, 240)),
                        outline=(255, 255, 255), width=4)
    dx = x0 + r.randint(20, hw - 90)
    d.rectangle([dx, y1 - 110, dx + 60, y1], fill=(r.randint(40, 140), r.randint(20, 80), r.randint(10, 60)))
    for _ in range(r.randint(2, 7)):  # arbres
        tx, ts = r.randint(0, w), r.randint(50, 130)
        ty = int(h * .88) + r.randint(-20, 40)
        d.rectangle([tx - 8, ty - ts, tx + 8, ty], fill=(90, 60, 30))
        d.ellipse([tx - ts // 2, ty - ts * 2, tx + ts // 2, ty - ts // 2 + 20], fill=(r.randint(20, 80), r.randint(100, 180), r.randint(20, 80)))
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    px = img.load()
    for _ in range(w * h // 18):  # grain
        x, y = r.randrange(w), r.randrange(h)
        v = r.randint(-18, 18)
        c = px[x, y]
        px[x, y] = (max(0, min(255, c[0] + v)), max(0, min(255, c[1] + v)), max(0, min(255, c[2] + v)))
    return img


# (ville, commune, deal, type, titre, prix, chambres, sdb, m², meublé, adresse)
LISTINGS = [
    ("Kinshasa", "Gombe", "location", "appartement", "Appartement moderne vue sur le fleuve Congo", 1800, 3, 2, 140, 1, "Avenue de la Justice 12"),
    ("Kinshasa", "Ngaliema", "location", "villa", "Villa avec piscine et jardin, quartier calme", 3500, 5, 4, 420, 1, "Avenue Mbakana 45, Ma Campagne"),
    ("Kinshasa", "Limete", "location", "maison", "Maison familiale proche du boulevard Lumumba", 650, 3, 2, 180, 0, "7e rue Limete Industriel 31"),
    ("Kinshasa", "Bandalungwa", "location", "studio", "Studio meublé idéal étudiant ou jeune actif", 220, 1, 1, 32, 1, "Avenue Kasa-Vubu 8"),
    ("Kinshasa", "Mont-Ngafula", "vente", "villa", "Villa neuve à vendre, titre foncier disponible", 185000, 4, 3, 380, 0, "Route de Matadi, Mitendi 2"),
    ("Kinshasa", "Lemba", "vente", "maison", "Maison à vendre près de l'université de Kinshasa", 72000, 4, 2, 250, 0, "Avenue Université 19"),
    ("Kinshasa", "Gombe", "vente", "appartement", "Appartement standing à vendre, immeuble sécurisé", 240000, 3, 2, 165, 0, "Boulevard du 30 Juin 101"),
    ("Lubumbashi", "Golf", "location", "maison", "Maison spacieuse au quartier Golf avec parking", 900, 4, 3, 300, 0, "Avenue Kasai 22"),
    ("Lubumbashi", "Kenya", "vente", "maison", "Maison à vendre, grande parcelle clôturée", 98000, 5, 3, 420, 0, "Avenue Kimbangu 54"),
    ("Lubumbashi", "Lubumbashi", "location", "appartement", "Appartement 2 chambres centre-ville", 480, 2, 1, 85, 1, "Avenue Lumumba 140"),
    ("Goma", "Himbi", "location", "villa", "Villa avec vue sur le lac Kivu", 1500, 4, 3, 330, 1, "Avenue du Lac 9"),
    ("Goma", "Katindo", "vente", "maison", "Maison familiale à vendre, quartier résidentiel", 64000, 3, 2, 210, 0, "Avenue des Aigles 17"),
    ("Kolwezi", "Manika", "location", "maison", "Maison 3 chambres avec groupe électrogène", 520, 3, 2, 160, 0, "Avenue Kolwezi 3"),
    ("Bukavu", "Ibanda", "location", "studio", "Studio lumineux avec balcon près du lac", 190, 1, 1, 30, 1, "Avenue Patrice Lumumba 5"),
]
DESC = ("{t}. Situé à {c}, {v}, ce bien de {s} m² offre {b} chambre(s) et {ba} salle(s) de bain. "
        "Le quartier est calme, bien desservi par les transports, proche des commerces, écoles et services de santé. "
        "Visite possible sur rendez-vous via Ndaku, dossier et documents du bien disponibles sur demande.")
AMS = [["Eau courante", "Électricité", "Parking", "Gardien", "Internet"],
       ["Eau courante", "Groupe électrogène", "Clôture", "Citerne", "Jardin"],
       ["Électricité", "Climatisation", "Cuisine équipée", "Panneaux solaires", "Parking"]]
REVIEWS = ["Très bon contact avec l'hôte, le bien correspond exactement aux photos.",
           "Quartier calme et sécurisé, visite bien organisée, je recommande.",
           "Bien entretenu, annonce honnête. Un peu cher mais l'emplacement est excellent."]


def run(reset=False):
    path = dbm.DB_PATH
    if reset and os.path.exists(path):
        for ext in ("", "-wal", "-shm"):
            if os.path.exists(path + ext):
                os.remove(path + ext)
        for f in os.listdir(dbm.UPLOADS):
            os.remove(os.path.join(dbm.UPLOADS, f))
    dbm.init()
    con = dbm.connect()
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        print("Base déjà peuplée (utilisez --reset).")
        return
    pw, now = generate_password_hash(DEMO_PASSWORD), time.time()
    users = [("Équipe Ndaku", "admin@ndaku.app", "admin", 1), ("Jean Mukendi", "jean@ndaku.app", "host", 1),
             ("Grace Kabila", "grace@ndaku.app", "host", 1), ("Patrick Ilunga", "patrick@ndaku.app", "host", 0),
             ("Aline Tshimanga", "aline@ndaku.app", "client", 0), ("David Mbuyi", "david@ndaku.app", "client", 0)]
    for n, e, r, v in users:
        con.execute("INSERT INTO users(name,email,pw_hash,role,phone,verified,created_at) VALUES(?,?,?,?,?,?,?)",
                    (n, e, pw, r, "", v, now - 90 * 86400))
    hosts = [2, 3, 4]
    r = random.Random(7)
    photos = real_photos()
    for i, (city, com, deal, pt, title, price, bed, bath, m2, furn, addr) in enumerate(LISTINGS):
        owner = hosts[i % 3]
        desc = DESC.format(t=title, c=com, v=r.choice(["à deux pas du centre", "dans une rue résidentielle", "avec accès facile à l'avenue principale"]),
                           s=m2, b=bed, ba=bath)
        cur = con.execute(
            "INSERT INTO listings(owner_id,title,description,deal,ptype,city,commune,address,price,bedrooms,bathrooms,"
            "surface,furnished,amenities,status,addr_key,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (owner, title, desc, deal, pt, city, com, addr, price, bed, bath, m2, furn, json.dumps(r.choice(AMS)),
             "active", af.addr_key(city, com, addr), now - (len(LISTINGS) - i) * 3600 * 7))
        lid, sidx, k = cur.lastrowid, 0, 0
        while k < 4:
            if photos is not None:
                if not photos:
                    raise SystemExit("Pas assez de photos distinctes dans seed_photos/")
                try:
                    img = af.load_image(open(photos.pop(0), "rb").read())
                except af.ImageRejected:
                    continue
            else:
                sidx += 1
                img = render_house(i * 100 + sidx)
            fp = af.fingerprint(img)
            # même contrôle que l'upload : on ne garde que des images distinctes
            if any(af.match_image(fp, o) for o in con.execute("SELECT sha,dhash,phash FROM images")):
                continue
            name = f"seed{i:02d}{k}.jpg"
            with open(os.path.join(dbm.UPLOADS, name), "wb") as fh:
                fh.write(af.to_jpeg(img))
            con.execute("INSERT INTO images(listing_id,filename,sha,dhash,phash,position) VALUES(?,?,?,?,?,?)",
                        (lid, name, fp["sha"], f"{fp['dhash']:016x}", f"{fp['phash']:016x}", k))
            k += 1
        for c, uid in enumerate((5, 6)):
            if r.random() < .8:
                con.execute("INSERT INTO inquiries(listing_id,user_id,message,preferred_date,created_at) VALUES(?,?,?,?,?)",
                            (lid, uid, "Bonjour, ce bien est-il toujours disponible ? Je souhaite le visiter.", "", now - 86400))
                con.execute("INSERT INTO reviews(listing_id,user_id,rating,comment,created_at) VALUES(?,?,?,?,?)",
                            (lid, uid, r.choice([3, 4, 4, 5, 5]), r.choice(REVIEWS), now - 3600 * (c + 1)))
    con.commit()
    con.close()
    print(f"OK — comptes démo (mot de passe : {DEMO_PASSWORD}) : admin@ / jean@ / grace@ (hôtes) / aline@ (client) @ndaku.app")


if __name__ == "__main__":
    import sys
    run(reset="--reset" in sys.argv)
