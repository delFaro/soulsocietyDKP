import streamlit as st
from tinydb import TinyDB, Query
from hashlib import sha256
from datetime import datetime
import pandas as pd
import random
import string

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
        'ingame_name': ingame_name,
        'class': '',
        'gearscore': ''
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

def update_class_and_gearscore(username, new_class, new_score):
    users_table.update({'class': new_class, 'gearscore': new_score}, Query().username == username)

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

def generate_password(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Session Management
if 'user' not in st.session_state:
    st.session_state.user = None

# Delfaro einmalig zum Superadmin machen
if users_table.contains(Query().username == 'delfaro'):
    users_table.update({'is_admin': True}, Query().username == 'delfaro')
    st.info("✅ 'delfaro' wurde einmalig zum Superadmin ernannt.")
