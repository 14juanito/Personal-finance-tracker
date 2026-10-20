import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.join(BASE, "instance")
UPLOADS = os.path.join(INSTANCE, "uploads")
DB_PATH = os.environ.get("NDAKU_DB", os.path.join(INSTANCE, "ndaku.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
  pw_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('client','host','admin')),
  phone TEXT, verified INTEGER NOT NULL DEFAULT 0,
  failed_logins INTEGER NOT NULL DEFAULT 0, locked_until REAL NOT NULL DEFAULT 0,
  created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS listings(
  id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id),
  title TEXT NOT NULL, description TEXT NOT NULL,
  deal TEXT NOT NULL CHECK(deal IN ('location','vente')),
  ptype TEXT NOT NULL, city TEXT NOT NULL, commune TEXT NOT NULL, address TEXT NOT NULL,
  price REAL NOT NULL, bedrooms INTEGER NOT NULL, bathrooms INTEGER NOT NULL,
  surface INTEGER NOT NULL, furnished INTEGER NOT NULL DEFAULT 0, amenities TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL CHECK(status IN ('active','pending','rejected','closed')),
  risk_score INTEGER NOT NULL DEFAULT 0, risk_reasons TEXT NOT NULL DEFAULT '[]',
  addr_key TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_listings_search ON listings(status, city, deal);
CREATE TABLE IF NOT EXISTS images(
  id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  filename TEXT NOT NULL, sha TEXT NOT NULL UNIQUE, dhash TEXT NOT NULL, phash TEXT NOT NULL,
  position INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS favorites(
  user_id INTEGER NOT NULL, listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  PRIMARY KEY(user_id, listing_id));
CREATE TABLE IF NOT EXISTS inquiries(
  id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id), message TEXT NOT NULL, preferred_date TEXT,
  created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS reviews(
  id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id), rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
  comment TEXT NOT NULL, created_at REAL NOT NULL, UNIQUE(listing_id, user_id));
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id), reason TEXT NOT NULL, created_at REAL NOT NULL,
  UNIQUE(listing_id, user_id));
"""


def connect(path=None):
    os.makedirs(UPLOADS, exist_ok=True)
    con = sqlite3.connect(path or DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init(path=None):
    con = connect(path)
    con.executescript(SCHEMA)
    con.commit()
    con.close()
