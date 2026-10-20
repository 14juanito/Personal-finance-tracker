"""Ndaku — marketplace immobilière (location & vente), style Airbnb."""
import json
import os
import secrets
import time
import uuid

from flask import Flask, abort, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

import antifraud as af
import db as dbm

CITIES = {
    "Kinshasa": ["Gombe", "Limete", "Ngaliema", "Bandalungwa", "Lemba", "Kintambo", "Matete", "Masina",
                 "Kalamu", "Lingwala", "Mont-Ngafula", "Ngaba", "Kasa-Vubu", "Barumbu", "Selembao", "N'djili"],
    "Lubumbashi": ["Lubumbashi", "Golf", "Kenya", "Kamalondo", "Katuba", "Ruashi"],
    "Goma": ["Goma", "Himbi", "Katindo", "Les Volcans", "Mugunga"],
    "Kolwezi": ["Manika", "Dilala"],
    "Matadi": ["Matadi", "Mvuzi"],
    "Kisangani": ["Makiso", "Tshopo"],
    "Bukavu": ["Ibanda", "Kadutu", "Bagira"],
    "Mbuji-Mayi": ["Diulu", "Muya"],
}
DEALS = ("location", "vente")
PTYPES = ("maison", "appartement", "villa", "studio", "terrain")
AMENITIES = ("Eau courante", "Électricité", "Groupe électrogène", "Parking", "Clôture", "Gardien",
             "Climatisation", "Internet", "Jardin", "Citerne", "Cuisine équipée", "Panneaux solaires")
MAX_IMAGES, MIN_IMAGES = 10, 3
MAX_LISTINGS_PER_DAY = 5
LOCK_AFTER, LOCK_SECONDS = 5, 900
REPORTS_TO_HIDE = 3


def create_app(db_path=None):
    app = Flask(__name__, static_folder="static", static_url_path="")
    app.config["DB_PATH"] = db_path or dbm.DB_PATH
    app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024
    key_file = os.path.join(dbm.INSTANCE, "secret.key")
    os.makedirs(dbm.INSTANCE, exist_ok=True)
    if not os.path.exists(key_file):
        with open(key_file, "w") as f:
            f.write(secrets.token_hex(32))
        os.chmod(key_file, 0o600)
    app.secret_key = os.environ.get("NDAKU_SECRET") or open(key_file).read()
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_SECURE=bool(os.environ.get("NDAKU_HTTPS")))
    dbm.init(app.config["DB_PATH"])

    # ------------------------------------------------------------------ infra
    def get_db():
        if "db" not in g:
            g.db = dbm.connect(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(_):
        con = g.pop("db", None)
        if con:
            con.close()

    @app.before_request
    def csrf_guard():
        # Les navigateurs n'ajoutent pas d'en-tête personnalisé aux requêtes cross-site sans CORS.
        if request.method in ("POST", "PATCH", "DELETE", "PUT") and request.headers.get("X-Ndaku") != "1":
            abort(403, "Requête refusée (en-tête de sécurité manquant).")

    @app.after_request
    def headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; frame-ancestors 'none'")
        return resp

    @app.errorhandler(Exception)
    def on_error(e):
        if getattr(e, "response", None) is not None:
            return e.response
        code = getattr(e, "code", 500)
        if not isinstance(code, int):
            code = 500
        if code == 500:
            app.logger.exception(e)
        msg = getattr(e, "description", "Erreur serveur") if code != 500 else "Erreur serveur"
        if request.path.startswith("/api/") or code != 404:
            return jsonify(error=msg), code
        return app.send_static_file("index.html")

    def me():
        uid = session.get("uid")
        if not uid:
            return None
        return get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    def need(*roles):
        u = me()
        if not u:
            abort(401, "Connexion requise.")
        if roles and u["role"] not in roles:
            abort(403, "Action réservée à un autre type de compte.")
        return u

    def body():
        return request.get_json(silent=True) or {}

    def clean(s, n):
        return (s or "").strip()[:n] if isinstance(s, str) else ""

    def public_user(u):
        return {"id": u["id"], "name": u["name"], "role": u["role"], "verified": bool(u["verified"])}

    # ------------------------------------------------------------------- auth
    @app.get("/api/me")
    def api_me():
        u = me()
        return jsonify(user=public_user(u) if u else None)

    @app.post("/api/register")
    def register():
        d = body()
        name, email = clean(d.get("name"), 80), clean(d.get("email"), 120).lower()
        pw, role = d.get("password") or "", d.get("role")
        if len(name) < 2 or "@" not in email or "." not in email.split("@")[-1]:
            abort(400, "Nom ou e-mail invalide.")
        if role not in ("client", "host"):
            abort(400, "Choisissez un type de compte : client ou hôte.")
        if len(pw) < 8 or pw.lower() == pw or not any(c.isdigit() for c in pw):
            abort(400, "Mot de passe : 8 caractères minimum, avec majuscule et chiffre.")
        con = get_db()
        if con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            abort(409, "Un compte existe déjà avec cet e-mail.")
        cur = con.execute("INSERT INTO users(name,email,pw_hash,role,phone,created_at) VALUES(?,?,?,?,?,?)",
                          (name, email, generate_password_hash(pw), role, clean(d.get("phone"), 30), time.time()))
        con.commit()
        session.clear()
        session["uid"] = cur.lastrowid
        return jsonify(user=public_user(me())), 201

    @app.post("/api/login")
    def login():
        d = body()
        email, pw = clean(d.get("email"), 120).lower(), d.get("password") or ""
        con = get_db()
        u = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if u and u["locked_until"] > time.time():
            abort(429, "Trop de tentatives. Réessayez dans quelques minutes.")
        if not u or not check_password_hash(u["pw_hash"], pw):
            if u:
                fails = u["failed_logins"] + 1
                con.execute("UPDATE users SET failed_logins=?, locked_until=? WHERE id=?",
                            (0 if fails >= LOCK_AFTER else fails,
                             time.time() + LOCK_SECONDS if fails >= LOCK_AFTER else 0, u["id"]))
                con.commit()
            abort(401, "E-mail ou mot de passe incorrect.")
        con.execute("UPDATE users SET failed_logins=0, locked_until=0 WHERE id=?", (u["id"],))
        con.commit()
        session.clear()
        session["uid"] = u["id"]
        return jsonify(user=public_user(u))

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(ok=True)

    # ---------------------------------------------------------------- annonces
    SCORE_SQL = """
      ROUND((3*3.5 + COALESCE((SELECT SUM(rating) FROM reviews r WHERE r.listing_id=l.id),0))
            / (3 + (SELECT COUNT(*) FROM reviews r WHERE r.listing_id=l.id))
            + 0.05*(SELECT COUNT(*) FROM favorites f WHERE f.listing_id=l.id)
            + CASE WHEN u.verified THEN 0.3 ELSE 0 END, 2)"""
    BASE_SQL = f"""
      SELECT l.*, u.name AS host_name, u.verified AS host_verified, {SCORE_SQL} AS score,
        (SELECT ROUND(AVG(rating),2) FROM reviews r WHERE r.listing_id=l.id) AS rating,
        (SELECT COUNT(*) FROM reviews r WHERE r.listing_id=l.id) AS reviews_count,
        (SELECT filename FROM images i WHERE i.listing_id=l.id ORDER BY position LIMIT 1) AS cover
      FROM listings l JOIN users u ON u.id=l.owner_id"""

    def card(r, favs=()):
        return {"id": r["id"], "title": r["title"], "deal": r["deal"], "ptype": r["ptype"], "city": r["city"],
                "commune": r["commune"], "price": r["price"], "bedrooms": r["bedrooms"],
                "bathrooms": r["bathrooms"], "surface": r["surface"], "furnished": bool(r["furnished"]),
                "status": r["status"], "rating": r["rating"], "reviews_count": r["reviews_count"],
                "score": r["score"], "cover": r["cover"], "host_verified": bool(r["host_verified"]),
                "favorite": r["id"] in favs}

    def my_favs():
        u = me()
        if not u:
            return set()
        return {x[0] for x in get_db().execute("SELECT listing_id FROM favorites WHERE user_id=?", (u["id"],))}

    @app.get("/api/meta")
    def meta():
        rows = get_db().execute("SELECT city, deal, COUNT(*) n FROM listings WHERE status='active' GROUP BY 1,2")
        return jsonify(cities=CITIES, deals=DEALS, ptypes=PTYPES, amenities=AMENITIES,
                       min_images=MIN_IMAGES, max_images=MAX_IMAGES,
                       counts=[dict(r) for r in rows])

    @app.get("/api/listings")
    def list_listings():
        a, where, args = request.args, ["l.status='active'"], []
        for key in ("city", "commune", "deal", "ptype"):
            if a.get(key):
                where.append(f"l.{key}=?")
                args.append(a[key])
        for key, col, op in (("min_price", "price", ">="), ("max_price", "price", "<="),
                             ("bedrooms", "bedrooms", ">=")):
            try:
                if a.get(key):
                    where.append(f"l.{col}{op}?")
                    args.append(float(a[key]))
            except ValueError:
                abort(400, "Filtre numérique invalide.")
        if a.get("furnished") == "1":
            where.append("l.furnished=1")
        if a.get("q"):
            where.append("(l.title LIKE ? OR l.description LIKE ? OR l.address LIKE ?)")
            args += [f"%{a['q'][:60]}%"] * 3
        order = {"new": "l.created_at DESC", "price_asc": "l.price ASC", "price_desc": "l.price DESC"}.get(
            a.get("sort"), "score DESC, l.created_at DESC")
        try:
            limit, offset = min(int(a.get("limit", 24)), 60), max(int(a.get("offset", 0)), 0)
        except ValueError:
            abort(400, "Pagination invalide.")
        sql = f"{BASE_SQL} WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?"
        rows = get_db().execute(sql, args + [limit, offset]).fetchall()
        total = get_db().execute(f"SELECT COUNT(*) FROM listings l WHERE {' AND '.join(where)}", args).fetchone()[0]
        favs = my_favs()
        return jsonify(items=[card(r, favs) for r in rows], total=total)

    @app.get("/api/listings/<int:lid>")
    def get_listing(lid):
        con, u = get_db(), me()
        r = con.execute(f"{BASE_SQL} WHERE l.id=?", (lid,)).fetchone()
        if not r:
            abort(404, "Annonce introuvable.")
        is_staff = bool(u and (u["role"] == "admin" or u["id"] == r["owner_id"]))
        if r["status"] != "active" and not is_staff:
            abort(404, "Annonce introuvable.")
        d = card(r, my_favs())
        d.update(description=r["description"], address=r["address"], amenities=json.loads(r["amenities"]),
                 created_at=r["created_at"], host={"id": r["owner_id"], "name": r["host_name"],
                                                   "verified": bool(r["host_verified"])},
                 images=[x["filename"] for x in con.execute(
                     "SELECT filename FROM images WHERE listing_id=? ORDER BY position", (lid,))],
                 reviews=[dict(x) for x in con.execute(
                     "SELECT r.rating, r.comment, r.created_at, u.name FROM reviews r JOIN users u ON u.id=r.user_id "
                     "WHERE r.listing_id=? ORDER BY r.created_at DESC", (lid,))])
        if is_staff:
            d["risk_score"], d["risk_reasons"] = r["risk_score"], json.loads(r["risk_reasons"])
        if u:
            d["can_review"] = bool(
                u["id"] != r["owner_id"]
                and con.execute("SELECT 1 FROM inquiries WHERE listing_id=? AND user_id=?", (lid, u["id"])).fetchone()
                and not con.execute("SELECT 1 FROM reviews WHERE listing_id=? AND user_id=?", (lid, u["id"])).fetchone())
        return jsonify(d)

    def parse_listing(f):
        title, desc = clean(f.get("title"), 120), clean(f.get("description"), 3000)
        city, commune = f.get("city"), f.get("commune")
        deal, ptype = f.get("deal"), f.get("ptype")
        address = clean(f.get("address"), 160)
        if deal not in DEALS or ptype not in PTYPES:
            abort(400, "Type d'offre ou de bien invalide.")
        if city not in CITIES or commune not in CITIES[city]:
            abort(400, "Localisation invalide (ville / commune).")
        if len(title) < 8 or len(address) < 5:
            abort(400, "Titre (8+ caractères) et adresse (5+) requis.")
        if len(desc) < 60:
            abort(400, "Description trop courte (60 caractères minimum) : décrivez le bien précisément.")
        try:
            price = float(f.get("price"))
            bedrooms, bathrooms = int(f.get("bedrooms", 0)), int(f.get("bathrooms", 0))
            surface = int(f.get("surface"))
        except (TypeError, ValueError):
            abort(400, "Prix, chambres, salles de bain et surface doivent être des nombres.")
        lo, hi = (20, 20_000) if deal == "location" else (3_000, 20_000_000)
        if not lo <= price <= hi:
            abort(400, f"Prix hors limites réalistes ({lo}–{hi} USD).")
        if not 9 <= surface <= 50_000 or not 0 <= bedrooms <= 20 or not 0 <= bathrooms <= 20:
            abort(400, "Surface ou nombre de pièces irréaliste.")
        if ptype != "terrain" and bedrooms and surface / bedrooms < 8:
            abort(400, "Incohérence : surface trop petite pour ce nombre de chambres.")
        am = [x for x in f.getlist("amenities") if x in AMENITIES]
        return dict(title=title, description=desc, deal=deal, ptype=ptype, city=city, commune=commune,
                    address=address, price=price, bedrooms=bedrooms, bathrooms=bathrooms, surface=surface,
                    furnished=1 if f.get("furnished") in ("1", "true", "on") else 0, amenities=am)

    def check_images(con, files, ignore_listing=None):
        """Retourne [(jpeg_bytes, fingerprint)] ou lève 422 avec le détail par fichier."""
        files = [f for f in files if f and f.filename]
        if not MIN_IMAGES <= len(files) <= MAX_IMAGES:
            abort(400, f"Ajoutez entre {MIN_IMAGES} et {MAX_IMAGES} photos.")
        stored = con.execute("SELECT i.sha, i.dhash, i.phash, i.listing_id, l.owner_id FROM images i "
                             "JOIN listings l ON l.id=i.listing_id").fetchall()
        out, problems = [], []
        for f in files:
            try:
                img = af.load_image(f.read())
                fp = af.fingerprint(img)
            except af.ImageRejected as e:
                problems.append({"file": f.filename, "reason": str(e)})
                continue
            clash = next(((m, s) for s in stored if (m := af.match_image(fp, s))), None)
            if clash:
                same_owner = clash[1]["owner_id"] == session.get("uid")
                problems.append({"file": f.filename, "reason": (
                    "Photo déjà utilisée dans " + ("l'une de vos annonces." if same_owner else "une autre annonce.")
                ) + (" (copie exacte)" if clash[0] == "exact" else " (image quasi identique : recadrage, miroir ou retouche)")})
                continue
            twin = next((o for o in out if af.match_image(fp, {"sha": o[1]["sha"], "dhash": f"{o[1]['dhash']:x}",
                                                               "phash": f"{o[1]['phash']:x}"})), None)
            if twin:
                problems.append({"file": f.filename, "reason": "Cette photo apparaît deux fois dans votre envoi."})
                continue
            out.append((af.to_jpeg(img), fp))
        if problems:
            resp = jsonify(error="Certaines photos sont refusées par le contrôle anti-fraude.", problems=problems)
            resp.status_code = 422
            abort(resp)
        return out

    @app.post("/api/listings")
    def create_listing():
        u = need("host")
        con = get_db()
        recent = con.execute("SELECT COUNT(*) FROM listings WHERE owner_id=? AND created_at>?",
                             (u["id"], time.time() - 86400)).fetchone()[0]
        if recent >= MAX_LISTINGS_PER_DAY:
            abort(429, f"Limite de {MAX_LISTINGS_PER_DAY} annonces par 24 h atteinte.")
        data = parse_listing(request.form)

        # Règles bloquantes : coordonnées hors-plateforme (arnaque classique)
        for field in ("title", "description"):
            hit = af.find_contact_info(data[field])
            if hit:
                abort(400, f"Coordonnées interdites dans « {field} » ({hit}). Les échanges doivent rester sur Ndaku.")
        key = af.addr_key(data["city"], data["commune"], data["address"])
        clash = con.execute("SELECT owner_id FROM listings WHERE addr_key=? AND status IN ('active','pending') "
                            "AND deal=?", (key, data["deal"])).fetchall()
        if any(r["owner_id"] != u["id"] for r in clash):
            abort(409, "Ce bien est déjà publié par un autre hôte à cette adresse. Contactez le support si c'est une erreur.")
        if clash:
            abort(409, "Vous avez déjà une annonce active pour cette adresse.")
        images = check_images(con, request.files.getlist("images"))

        # Score de risque (règles souples → modération manuelle)
        score, reasons = 0, []
        comps = con.execute("SELECT price, surface FROM listings WHERE status='active' AND city=? AND deal=? "
                            "AND ptype=?", (data["city"], data["deal"], data["ptype"])).fetchall()
        why = af.price_anomaly(data["price"], data["surface"], [(c["price"], c["surface"]) for c in comps])
        if why:
            score += 45
            reasons.append(why)
        sh = af.shingles(data["description"])
        for o in con.execute("SELECT owner_id, description FROM listings WHERE status IN ('active','pending')"):
            if o["owner_id"] != u["id"] and af.jaccard(sh, af.shingles(o["description"])) >= 0.6:
                score += 50
                reasons.append("Description quasi identique à celle d'une annonce d'un autre hôte")
                break
        if time.time() - (con.execute("SELECT created_at FROM users WHERE id=?", (u["id"],)).fetchone()[0]) < 3600:
            score += 10
            reasons.append("Compte créé il y a moins d'une heure")
        if not u["verified"]:
            score += 10
            reasons.append("Hôte non vérifié")
        status = "pending" if score >= af.RISK_PENDING_THRESHOLD else "active"

        cur = con.execute(
            "INSERT INTO listings(owner_id,title,description,deal,ptype,city,commune,address,price,bedrooms,bathrooms,"
            "surface,furnished,amenities,status,risk_score,risk_reasons,addr_key,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (u["id"], data["title"], data["description"], data["deal"], data["ptype"], data["city"], data["commune"],
             data["address"], data["price"], data["bedrooms"], data["bathrooms"], data["surface"], data["furnished"],
             json.dumps(data["amenities"]), status, score, json.dumps(reasons), key, time.time()))
        lid = cur.lastrowid
        saved = []
        try:
            for pos, (jpeg, fp) in enumerate(images):
                name = uuid.uuid4().hex + ".jpg"
                with open(os.path.join(dbm.UPLOADS, name), "wb") as fh:
                    fh.write(jpeg)
                saved.append(name)
                con.execute("INSERT INTO images(listing_id,filename,sha,dhash,phash,position) VALUES(?,?,?,?,?,?)",
                            (lid, name, fp["sha"], f"{fp['dhash']:016x}", f"{fp['phash']:016x}", pos))
            con.commit()
        except Exception as e:  # course critique : la contrainte UNIQUE(sha) rattrape un doublon concurrent
            con.rollback()
            for n in saved:
                try:
                    os.remove(os.path.join(dbm.UPLOADS, n))
                except OSError:
                    pass
            if "UNIQUE" in str(e):
                abort(422, "Une de ces photos vient d'être utilisée par une autre annonce.")
            raise
        return jsonify(id=lid, status=status, reasons=reasons), 201

    @app.patch("/api/listings/<int:lid>")
    def patch_listing(lid):
        u, con = need(), get_db()
        r = con.execute("SELECT * FROM listings WHERE id=?", (lid,)).fetchone()
        if not r or (r["owner_id"] != u["id"] and u["role"] != "admin"):
            abort(404, "Annonce introuvable.")
        status = body().get("status")
        if status not in ("closed", "active") or r["status"] in ("pending", "rejected"):
            abort(400, "Changement de statut non autorisé.")
        con.execute("UPDATE listings SET status=? WHERE id=?", (status, lid))
        con.commit()
        return jsonify(ok=True)

    @app.delete("/api/listings/<int:lid>")
    def delete_listing(lid):
        u, con = need(), get_db()
        r = con.execute("SELECT * FROM listings WHERE id=?", (lid,)).fetchone()
        if not r or (r["owner_id"] != u["id"] and u["role"] != "admin"):
            abort(404, "Annonce introuvable.")
        if r["status"] == "rejected":  # les annonces rejetées restent en base : leurs photos restent bannies
            abort(400, "Une annonce rejetée par la modération est conservée.")
        names = [x[0] for x in con.execute("SELECT filename FROM images WHERE listing_id=?", (lid,))]
        con.execute("DELETE FROM listings WHERE id=?", (lid,))
        con.commit()
        for n in names:
            try:
                os.remove(os.path.join(dbm.UPLOADS, n))
            except OSError:
                pass
        return jsonify(ok=True)

    @app.get("/api/my/listings")
    def my_listings():
        u = need("host")
        rows = get_db().execute(f"{BASE_SQL} WHERE l.owner_id=? ORDER BY l.created_at DESC", (u["id"],)).fetchall()
        out = []
        for r in rows:
            c = card(r)
            c["risk_reasons"] = json.loads(r["risk_reasons"])
            c["inquiries"] = get_db().execute("SELECT COUNT(*) FROM inquiries WHERE listing_id=?", (r["id"],)).fetchone()[0]
            out.append(c)
        return jsonify(items=out)

    # ------------------------------------------------- favoris / messages / avis
    @app.post("/api/listings/<int:lid>/favorite")
    def toggle_fav(lid):
        u, con = need(), get_db()
        if not con.execute("SELECT 1 FROM listings WHERE id=? AND status='active'", (lid,)).fetchone():
            abort(404, "Annonce introuvable.")
        if con.execute("DELETE FROM favorites WHERE user_id=? AND listing_id=?", (u["id"], lid)).rowcount:
            fav = False
        else:
            con.execute("INSERT INTO favorites VALUES(?,?)", (u["id"], lid))
            fav = True
        con.commit()
        return jsonify(favorite=fav)

    @app.get("/api/favorites")
    def favorites():
        u = need()
        rows = get_db().execute(f"{BASE_SQL} WHERE l.status='active' AND l.id IN "
                                "(SELECT listing_id FROM favorites WHERE user_id=?)", (u["id"],)).fetchall()
        return jsonify(items=[card(r, {r["id"] for r in rows}) for r in rows])

    @app.post("/api/listings/<int:lid>/inquiries")
    def inquire(lid):
        u, con = need("client"), get_db()
        if not con.execute("SELECT 1 FROM listings WHERE id=? AND status='active'", (lid,)).fetchone():
            abort(404, "Annonce introuvable.")
        d = body()
        msg = clean(d.get("message"), 1000)
        if len(msg) < 10:
            abort(400, "Message trop court.")
        if con.execute("SELECT COUNT(*) FROM inquiries WHERE user_id=? AND created_at>?",
                       (u["id"], time.time() - 3600)).fetchone()[0] >= 10:
            abort(429, "Trop de messages envoyés. Patientez un peu.")
        con.execute("INSERT INTO inquiries(listing_id,user_id,message,preferred_date,created_at) VALUES(?,?,?,?,?)",
                    (lid, u["id"], msg, clean(d.get("preferred_date"), 20), time.time()))
        con.commit()
        return jsonify(ok=True), 201

    @app.get("/api/my/inquiries")
    def my_inquiries():
        u = need()
        if u["role"] == "host":
            sql = ("SELECT q.*, l.title, c.name AS who, c.phone AS who_phone FROM inquiries q "
                   "JOIN listings l ON l.id=q.listing_id JOIN users c ON c.id=q.user_id "
                   "WHERE l.owner_id=? ORDER BY q.created_at DESC")
        else:
            sql = ("SELECT q.*, l.title, h.name AS who, NULL AS who_phone FROM inquiries q "
                   "JOIN listings l ON l.id=q.listing_id JOIN users h ON h.id=l.owner_id "
                   "WHERE q.user_id=? ORDER BY q.created_at DESC")
        return jsonify(items=[dict(r) for r in get_db().execute(sql, (u["id"],))])

    @app.post("/api/listings/<int:lid>/reviews")
    def review(lid):
        u, con = need("client"), get_db()
        if not con.execute("SELECT 1 FROM inquiries WHERE listing_id=? AND user_id=?", (lid, u["id"])).fetchone():
            abort(403, "Seuls les clients ayant contacté l'hôte peuvent laisser un avis vérifié.")
        d = body()
        try:
            rating = int(d.get("rating"))
        except (TypeError, ValueError):
            abort(400, "Note invalide.")
        comment = clean(d.get("comment"), 800)
        if not 1 <= rating <= 5 or len(comment) < 10:
            abort(400, "Note de 1 à 5 et commentaire de 10 caractères minimum.")
        try:
            con.execute("INSERT INTO reviews(listing_id,user_id,rating,comment,created_at) VALUES(?,?,?,?,?)",
                        (lid, u["id"], rating, comment, time.time()))
            con.commit()
        except Exception:
            abort(409, "Vous avez déjà noté cette annonce.")
        return jsonify(ok=True), 201

    @app.post("/api/listings/<int:lid>/report")
    def report(lid):
        u, con = need(), get_db()
        r = con.execute("SELECT owner_id FROM listings WHERE id=? AND status='active'", (lid,)).fetchone()
        if not r or r["owner_id"] == u["id"]:
            abort(404, "Annonce introuvable.")
        reason = clean(body().get("reason"), 300)
        if len(reason) < 5:
            abort(400, "Précisez le motif du signalement.")
        try:
            con.execute("INSERT INTO reports(listing_id,user_id,reason,created_at) VALUES(?,?,?,?)",
                        (lid, u["id"], reason, time.time()))
        except Exception:
            abort(409, "Vous avez déjà signalé cette annonce.")
        n = con.execute("SELECT COUNT(*) FROM reports WHERE listing_id=?", (lid,)).fetchone()[0]
        if n >= REPORTS_TO_HIDE:  # masquage automatique en attendant la modération
            con.execute("UPDATE listings SET status='pending', risk_score=risk_score+50, risk_reasons=? WHERE id=?",
                        (json.dumps([f"{n} signalements d'utilisateurs"]), lid))
        con.commit()
        return jsonify(ok=True)

    # -------------------------------------------------------------- modération
    @app.get("/api/admin/queue")
    def queue():
        need("admin")
        rows = get_db().execute(f"{BASE_SQL} WHERE l.status='pending' ORDER BY l.risk_score DESC").fetchall()
        out = []
        for r in rows:
            c = card(r)
            c.update(risk_score=r["risk_score"], risk_reasons=json.loads(r["risk_reasons"]), host=r["host_name"],
                     reports=[x[0] for x in get_db().execute("SELECT reason FROM reports WHERE listing_id=?", (r["id"],))])
            out.append(c)
        return jsonify(items=out)

    @app.post("/api/admin/listings/<int:lid>/decision")
    def decide(lid):
        need("admin")
        act = body().get("action")
        if act not in ("approve", "reject"):
            abort(400, "Action invalide.")
        con = get_db()
        cur = con.execute("UPDATE listings SET status=? WHERE id=? AND status='pending'",
                          ("active" if act == "approve" else "rejected", lid))
        if act == "approve":
            con.execute("DELETE FROM reports WHERE listing_id=?", (lid,))
        con.commit()
        if not cur.rowcount:
            abort(404, "Annonce non en attente.")
        return jsonify(ok=True)

    @app.post("/api/admin/users/<int:uid>/verify")
    def verify_user(uid):
        need("admin")
        con = get_db()
        con.execute("UPDATE users SET verified=1 WHERE id=?", (uid,))
        con.commit()
        return jsonify(ok=True)

    @app.get("/uploads/<path:name>")
    def uploads(name):
        resp = send_from_directory(dbm.UPLOADS, name)
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=bool(os.environ.get("NDAKU_DEBUG")))
