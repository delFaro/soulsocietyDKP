import streamlit as st
from tinydb import TinyDB, Query
from hashlib import sha256
from datetime import datetime

# Datenbank-Datei
DB_FILE = 'dkp_tinydb.json'
db = TinyDB(DB_FILE)
users_table = db.table('users')
dkp_table = db.table('dkp')

# Hilfsfunktionen

def hash_password(password):
    return sha256(password.encode()).hexdigest()

def authenticate(username, password):
    user = users_table.get(Query().username == username)
    if user and user['password_hash'] == hash_password(password):
        return user
    return None

def create_user(username, password, is_admin=False):
    if users_table.contains(Query().username == username):
        return False
    users_table.insert({
        'username': username,
        'password_hash': hash_password(password),
        'is_admin': is_admin
    })
    dkp_table.insert({
        'username': username,
        'points': 0,
        'history': []
    })
    return True

def update_password(username, new_password):
    users_table.update({'password_hash': hash_password(new_password)}, Query().username == username)

def get_user(username):
    return users_table.get(Query().username == username)

def get_dkp(username):
    return dkp_table.get(Query().username == username)

def update_dkp(username, amount, by_user):
    record = get_dkp(username)
    record['points'] += amount
    record['history'].append({
        'action': 'award' if amount >= 0 else 'spend',
        'points': amount,
        'by': by_user,
        'timestamp': datetime.now().isoformat()
    })
    dkp_table.update(record, Query().username == username)

# Session Management
if 'user' not in st.session_state:
    st.session_state.user = None

# Login
if not st.session_state.user:
    st.title("🔐 DKP Login")
    username = st.text_input("Benutzername")
    password = st.text_input("Passwort", type="password")
    if st.button("Einloggen"):
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Willkommen, {username}!")
        else:
            st.error("Login fehlgeschlagen")
    st.stop()

# App nach Login
user = st.session_state.user
st.sidebar.write(f"👋 Eingeloggt als: {user['username']} ({'Admin' if user['is_admin'] else 'Spieler'})")
if st.sidebar.button("🔓 Logout"):
    st.session_state.user = None
    st.experimental_rerun()

st.title("🛡️ DKP System - Throne & Liberty")

# Passwort ändern
with st.expander("🔑 Passwort ändern"):
    new_pw = st.text_input("Neues Passwort", type="password")
    if st.button("Passwort ändern"):
        update_password(user['username'], new_pw)
        st.success("Passwort aktualisiert")

# Admin-Bereich
if user['is_admin']:
    st.header("👑 Admin Panel")
    new_user = st.text_input("Neuen Nutzer anlegen")
    new_pass = st.text_input("Standardpasswort")
    new_admin = st.checkbox("Als Admin anlegen")
    if st.button("Nutzer erstellen"):
        if create_user(new_user, new_pass, new_admin):
            st.success(f"Nutzer '{new_user}' angelegt")
        else:
            st.warning(f"Nutzer '{new_user}' existiert bereits")

    st.subheader("🔧 DKP Verwalten")
    all_users = [u['username'] for u in users_table.all()]
    target_user = st.selectbox("Spieler auswählen", all_users)
    points = st.number_input("Punkte (positiv/negativ)", value=0)
    if st.button("Anwenden"):
        update_dkp(target_user, points, user['username'])
        st.success(f"{points} Punkte bei {target_user} geändert")

# Spieleransicht
st.header("📋 Mein DKP")
my_dkp = get_dkp(user['username'])
st.write(f"💠 Aktueller Stand: **{my_dkp['points']} DKP**")

st.subheader("📜 Verlauf")
for entry in reversed(my_dkp['history'][-20:]):
    ts = datetime.fromisoformat(entry['timestamp']).strftime('%d.%m.%Y %H:%M')
    st.write(f"[{ts}] {entry['by']} -> {entry['points']} Punkte ({'vergeben' if entry['points'] >= 0 else 'abgezogen'})")
