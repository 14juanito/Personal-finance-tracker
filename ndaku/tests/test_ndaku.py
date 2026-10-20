import io
import os
import sys

import pytest
from PIL import Image, ImageOps

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import antifraud as af  # noqa: E402
import seed  # noqa: E402


def jpeg(img, q=90):
    b = io.BytesIO()
    img.save(b, "JPEG", quality=q)
    return b.getvalue()


def fp_of(img):
    return af.fingerprint(af.load_image(jpeg(img)))


def stored(fp):
    return {"sha": fp["sha"], "dhash": f"{fp['dhash']:x}", "phash": f"{fp['phash']:x}"}


BASE = seed.render_house(1)


@pytest.mark.parametrize("name,variant", [
    ("recompressée", lambda i: Image.open(io.BytesIO(jpeg(i, 40)))),
    ("redimensionnée", lambda i: i.resize((800, 533))),
    ("miroir", ImageOps.mirror),
    ("recadrée légèrement", lambda i: i.crop((10, 8, 1190, 790))),
])
def test_same_photo_variants_are_detected(name, variant):
    assert af.match_image(fp_of(variant(BASE)), stored(fp_of(BASE))), name


def test_different_photos_pass():
    fps = [fp_of(seed.render_house(s)) for s in range(1, 25)]
    for i, a in enumerate(fps):
        for b in fps[i + 1:]:
            assert not af.match_image(a, stored(b))


def test_bad_images_rejected():
    with pytest.raises(af.ImageRejected):
        af.load_image(b"not an image")
    with pytest.raises(af.ImageRejected):
        af.load_image(jpeg(Image.new("RGB", (100, 100), "red")))
    with pytest.raises(af.ImageRejected):
        af.load_image(jpeg(Image.new("RGB", (800, 600), "white")))


@pytest.mark.parametrize("t", ["Appelez-moi au +243 812 345 678", "ecrire a bob@mail.com", "contact whatsapp",
                               "voir www.arnaque.com"])
def test_contact_info_blocked(t):
    assert af.find_contact_info(t)


def test_clean_text_not_flagged():
    assert not af.find_contact_info("Maison de 180 m², 3 chambres, avenue de la Justice 12")


def test_price_anomaly():
    comps = [(1000, 100), (1100, 100), (900, 100)]
    assert af.price_anomaly(200, 100, comps)
    assert af.price_anomaly(1000, 100, comps) is None


# ------------------------------------------------------------------- API
@pytest.fixture()
def client(tmp_path, monkeypatch):
    import db as dbm
    monkeypatch.setattr(dbm, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(dbm, "UPLOADS", str(tmp_path / "up"))
    import app as appmod
    c = appmod.create_app(str(tmp_path / "t.db")).test_client()
    c.environ_base["HTTP_X_NDAKU"] = "1"
    return c


def signup(c, email, role):
    r = c.post("/api/register", json={"name": "Test User", "email": email, "password": "Motdepasse1", "role": role})
    assert r.status_code == 201, r.json


def form(seed_ids, **over):
    f = {"title": "Belle maison familiale", "description": "x" * 70, "deal": "location", "ptype": "maison",
         "city": "Kinshasa", "commune": "Gombe", "address": "Avenue Test 1", "price": "800", "bedrooms": "3",
         "bathrooms": "2", "surface": "150", **over}
    f["images"] = [(io.BytesIO(jpeg(seed.render_house(s))), f"p{s}.jpg") for s in seed_ids]
    return f


def test_csrf_header_required(client):
    del client.environ_base["HTTP_X_NDAKU"]
    assert client.post("/api/login", json={}).status_code == 403


def test_role_and_flow(client):
    signup(client, "h@x.com", "host")
    r = client.post("/api/listings", data=form([1, 2, 3]), content_type="multipart/form-data")
    assert r.status_code == 201 and r.json["status"] == "active" or r.json["status"] == "pending"
    # même photo (exacte) dans une autre annonce → refusée
    r = client.post("/api/listings", data=form([3, 4, 5], address="Avenue Autre 2"), content_type="multipart/form-data")
    assert r.status_code == 422 and r.json["problems"][0]["file"] == "p3.jpg"
    # même adresse → refusée
    r = client.post("/api/listings", data=form([6, 7, 8]), content_type="multipart/form-data")
    assert r.status_code == 409
    # coordonnées interdites
    r = client.post("/api/listings", data=form([6, 7, 8], address="Avenue B 3", description="Appelez le 0812345678 " + "x" * 60),
                    content_type="multipart/form-data")
    assert r.status_code == 400
    # doublon dans le même envoi
    f = form([9, 10]); f["images"].append((io.BytesIO(jpeg(seed.render_house(9))), "dup.jpg"))
    r = client.post("/api/listings", data={**f, "address": "Avenue C 4"}, content_type="multipart/form-data")
    assert r.status_code == 422 and r.json["problems"][0]["file"] == "dup.jpg"


def test_client_cannot_post_and_review_requires_inquiry(client):
    signup(client, "c@x.com", "client")
    assert client.post("/api/listings", data=form([1, 2, 3]), content_type="multipart/form-data").status_code == 403
    assert client.post("/api/listings/1/reviews", json={"rating": 5, "comment": "super bien" * 3}).status_code == 403
