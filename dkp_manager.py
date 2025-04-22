import streamlit as st
from tinydb import TinyDB, Query
from hashlib import sha256
from datetime import datetime
import pandas as pd

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

def create_user(username, password, is_admin=False, ingame_name=""):
    if users_table.contains(Query().username == username):
        return False
    users_table.insert({
        'username': username,
        'password_hash': hash_password(password),
        'is_admin': is_admin,
        'ingame_name': ingame_name
    })
    dkp_table.insert({
        'username': username,
        'points': 0,
        'history': []
    })
    return True

def update_password(username, new_password):
    users_table.update({'password_hash': hash_password(new_password)}, Query().username == username)

def update_ingame_name(username, new_ingame_name):
    users_table.update({'ingame_name': new_ingame_name}, Query().username == username)

def delete_user(username):
    users_table.remove(Query().username == username)
    dkp_table.remove(Query().username == username)

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

# 🛠️ Initial Setup - Admin anlegen, falls keine User existieren
if len(users_table) == 0:
    st.title("🚀 Erst-Setup: Admin-Account anlegen")
    admin_user = st.text_input("Admin Benutzername")
    admin_pass = st.text_input("Admin Passwort", type="password")
    if st.button("Admin erstellen"):
        if create_user(admin_user, admin_pass, is_admin=True):
            st.success("Admin erfolgreich angelegt. Jetzt einloggen!")
            st.stop()
        else:
            st.error("Benutzer existiert bereits")
    st.stop()

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

# Navigation
pages = ["Ranking"]
if user['is_admin']:
    pages.append("Admin")
selected_page = st.sidebar.radio("🔍 Navigation", pages)

st.title("🛡️ DKP System - Throne & Liberty")

# Passwort & Ingame-Namen ändern
with st.expander("🔑 Einstellungen"):
    new_pw = st.text_input("Neues Passwort", type="password")
    if st.button("Passwort ändern"):
        update_password(user['username'], new_pw)
        st.success("Passwort aktualisiert")

    new_ingame = st.text_input("Neuer Ingame-Name")
    if st.button("Ingame-Name ändern"):
        update_ingame_name(user['username'], new_ingame)
        st.success("Ingame-Name aktualisiert")

# Seiteninhalt
if selected_page == "Ranking":
    st.header("📋 Mein DKP")
    my_dkp = get_dkp(user['username'])
    my_ingame = get_user(user['username']).get("ingame_name", "")
    st.write(f"💠 Aktueller Stand: **{my_dkp['points']} DKP**")
    if my_ingame:
        st.write(f"🎮 Ingame-Name: **{my_ingame}**")

    st.header("📊 DKP Rangliste")
    dkp_list = dkp_table.all()
    user_dict = {u['username']: u.get('ingame_name', '') for u in users_table.all()}
    df = pd.DataFrame([{ "Benutzer": d["username"], "Ingame-Name": user_dict.get(d["username"], "-"), "DKP": d["points"] } for d in dkp_list])
    df = df.sort_values(by="DKP", ascending=False).reset_index(drop=True)
    df.index += 1

    highlight_index = df[df["Benutzer"] == user["username"]].index[0] + 1
    st.markdown(f"🏅 **Dein Rang:** Platz {highlight_index} von {len(df)}")
    st.dataframe(df, use_container_width=True)

    st.subheader("📜 Verlauf")
    for entry in reversed(my_dkp['history'][-20:]):
        ts = datetime.fromisoformat(entry['timestamp']).strftime('%d.%m.%Y %H:%M')
        st.write(f"[{ts}] {entry['by']} -> {entry['points']} Punkte ({'vergeben' if entry['points'] >= 0 else 'abgezogen'})")

elif selected_page == "Admin" and user['is_admin']:
    st.header("👑 Admin Panel")
    new_user = st.text_input("Neuen Nutzer anlegen")
    new_pass = st.text_input("Standardpasswort")
    new_ingame = st.text_input("Ingame-Name")
    new_admin = st.checkbox("Als Admin anlegen")
    if st.button("Nutzer erstellen"):
        if create_user(new_user, new_pass, new_admin, new_ingame):
            st.success(f"Nutzer '{new_user}' mit Ingame-Name '{new_ingame}' angelegt")
        else:
            st.warning(f"Nutzer '{new_user}' existiert bereits")

    st.subheader("🔧 DKP Verwalten")
    all_users = [u['username'] for u in users_table.all() if u['username'] != user['username']]
    target_user = st.selectbox("Spieler auswählen", all_users)
    points = st.number_input("Punkte (positiv/negativ)", value=0, key="dkp_change")
    if st.button("Anwenden", key="change_dkp"):
        update_dkp(target_user, points, user['username'])
        st.success(f"{points} Punkte bei {target_user} geändert")

    st.subheader("🔁 Passwort zurücksetzen & 🗑️ Spieler löschen")
    reset_pass = st.text_input("Neues Passwort für Spieler", key="reset_pass")
    if st.button("Passwort zurücksetzen"):
        update_password(target_user, reset_pass)
        st.success(f"Passwort von '{target_user}' zurückgesetzt")

    if st.checkbox("⚠️ Spieler wirklich löschen?"):
        if st.button("❌ Spieler löschen"):
            delete_user(target_user)
            st.success(f"Spieler '{target_user}' gelöscht")
            st.experimental_rerun()
