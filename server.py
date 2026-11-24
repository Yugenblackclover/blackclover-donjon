#!/usr/bin/env python3
"""
Black Clover Dungeon Registration
Un seul site : les admins voient des outils supplémentaires après connexion.
"""

import http.server
import socketserver
import json
import hashlib
import secrets
import urllib.parse
from datetime import datetime
from pathlib import Path

PORT = 8765
DATA_FILE = Path(__file__).parent / "data" / "registrations.json"
MAX_TOTAL = 24
MAX_PER_GROUP = 12

ADMINS = {
    "empereur mage": "CloverEmpire#2026",
    "conseillère": "MagicKnight@24"
}

sessions = {}

def load_data():
    if not DATA_FILE.exists():
        return {
            "registrations_open": True,
            "players": [],
            "group1": [],
            "group2": [],
            "created_at": datetime.now().isoformat()
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

ADMIN_HASHES = {u: hash_password(p) for u, p in ADMINS.items()}

def get_page(data, admin_user=None, message=None, error=None, show_login=False):
    players = data.get("players", [])
    open_reg = data.get("registrations_open", True)
    remaining = MAX_TOTAL - len(players)
    g1 = data.get("group1", [])
    g2 = data.get("group2", [])
    assigned = set(g1 + g2)
    unassigned = [p["pseudo"] for p in players if p["pseudo"] not in assigned]

    if not open_reg:
        status_html = '<div class="banner closed">🔒 Les inscriptions sont actuellement fermées</div>'
    elif remaining <= 0:
        status_html = '<div class="banner full">⚔️ Les 24 places sont prises !</div>'
    else:
        status_html = f'<div class="banner open">✨ {remaining} place(s) restante(s) — Inscriptions ouvertes</div>'

    msg_html = ""
    if message:
        msg_html = f'<div class="alert success">{message}</div>'
    if error:
        msg_html = f'<div class="alert error">{error}</div>'

    if open_reg and remaining > 0 and not admin_user:
        form_html = """
            <form method="POST" action="/register" class="register-form">
                <input type="text" name="pseudo" placeholder="Ton nom RP uniquement" required maxlength="32"
                       pattern="[A-Za-zÀ-ÿ0-9_\\- ]{2,32}" title="2 à 32 caractères">
                <button type="submit" class="btn primary">Rejoindre l'aventure</button>
            </form>
            <p class="hint">⚠️ Utilise uniquement ton <strong>nom RP</strong>.</p>
        """
    elif admin_user:
        form_html = "<p class='hint'>Tu es connecté en admin. Les joueurs s'inscrivent normalement.</p>"
    else:
        form_html = "<p class='disabled-msg'>Les inscriptions sont fermées ou complètes.</p>"

    players_list = ""
    if players:
        players_list = "<ul class='player-list'>" + "".join(f"<li>☘️ {p['pseudo']}</li>" for p in players) + "</ul>"
    else:
        players_list = "<p class='empty'>Aucun inscrit pour le moment...</p>"

    groups_public = f"""
        <div class="groups">
            <div class="group">
                <h3>Groupe 1 <span>({len(g1)}/12)</span></h3>
                <ul>{"".join(f"<li>{p}</li>" for p in g1) or "<li class='empty'>—</li>"}</ul>
            </div>
            <div class="group">
                <h3>Groupe 2 <span>({len(g2)}/12)</span></h3>
                <ul>{"".join(f"<li>{p}</li>" for p in g2) or "<li class='empty'>—</li>"}</ul>
            </div>
        </div>
    """

    admin_section = ""
    if admin_user:
        players_admin = ""
        for p in players:
            players_admin += f'''
                <li>
                    ☘️ {p["pseudo"]}
                    <form method="POST" action="/admin/remove" style="display:inline">
                        <input type="hidden" name="pseudo" value="{p["pseudo"]}">
                        <button type="submit" class="btn-icon" title="Supprimer" onclick="return confirm('Supprimer {p["pseudo"]} ?')">✕</button>
                    </form>
                </li>'''
        if not players_admin:
            players_admin = "<li class='empty'>Aucun inscrit</li>"

        unassigned_html = "".join(f'<div class="drag-item" draggable="true" data-name="{name}">{name}</div>' for name in unassigned)
        g1_html = "".join(f'<div class="drag-item in-group" draggable="true" data-name="{name}">{name}</div>' for name in g1)
        g2_html = "".join(f'<div class="drag-item in-group" draggable="true" data-name="{name}">{name}</div>' for name in g2)

        admin_section = f"""
        <section class="card admin-panel">
            <h2>🛠️ Panel Admin — {admin_user}</h2>
            <div class="controls">
                <form method="POST" action="/admin/toggle" style="display:inline">
                    <button type="submit" class="btn {'danger' if open_reg else 'primary'}">
                        {"🔒 Fermer les inscriptions" if open_reg else "🔓 Ouvrir les inscriptions"}
                    </button>
                </form>
                <form method="POST" action="/admin/reset" style="display:inline" onsubmit="return confirm('Vraiment tout réinitialiser ?')">
                    <button type="submit" class="btn danger">🗑️ Tout réinitialiser</button>
                </form>
                <a href="/logout" class="btn small danger">Déconnexion</a>
            </div>
            <h3 style="margin-top:1.5rem;color:var(--green-light)">Inscrits (suppression individuelle)</h3>
            <ul class="player-list admin-list">{players_admin}</ul>
            <h3 style="margin-top:1.8rem;color:var(--green-light)">Formation des groupes (glisser-déposer)</h3>
            <p class="hint">Glisse les noms. Max 12 par groupe. Puis sauvegarde.</p>
            <div class="drag-container">
                <div class="drop-zone" data-group="unassigned">
                    <h3>Non assignés <span id="count-unassigned">({len(unassigned)})</span></h3>
                    <div class="drop-area" id="list-unassigned">
                        {unassigned_html or '<div class="empty-drop">Aucun</div>'}
                    </div>
                </div>
                <div class="drop-zone" data-group="group1">
                    <h3>Groupe 1 <span id="count-group1">({len(g1)}/12)</span></h3>
                    <div class="drop-area" id="list-group1">
                        {g1_html or '<div class="empty-drop">Glisse ici</div>'}
                    </div>
                </div>
                <div class="drop-zone" data-group="group2">
                    <h3>Groupe 2 <span id="count-group2">({len(g2)}/12)</span></h3>
                    <div class="drop-area" id="list-group2">
                        {g2_html or '<div class="empty-drop">Glisse ici</div>'}
                    </div>
                </div>
            </div>
            <form method="POST" action="/admin/groups" id="groups-form">
                <input type="hidden" name="group1" id="input-group1" value="{','.join(g1)}">
                <input type="hidden" name="group2" id="input-group2" value="{','.join(g2)}">
                <button type="submit" class="btn primary" style="margin-top:1.2rem">💾 Sauvegarder les groupes</button>
            </form>
        </section>
        <script>
        let dragged = null;
        document.querySelectorAll('.drag-item').forEach(item => {{
            item.addEventListener('dragstart', e => {{
                dragged = item;
                e.dataTransfer.effectAllowed = 'move';
                setTimeout(() => item.classList.add('dragging'), 0);
            }});
            item.addEventListener('dragend', () => {{
                item.classList.remove('dragging');
                dragged = null;
            }});
        }});
        document.querySelectorAll('.drop-area').forEach(area => {{
            area.addEventListener('dragover', e => {{ e.preventDefault(); area.classList.add('drag-over'); }});
            area.addEventListener('dragleave', () => area.classList.remove('drag-over'));
            area.addEventListener('drop', e => {{
                e.preventDefault();
                area.classList.remove('drag-over');
                if (!dragged) return;
                const zone = area.closest('.drop-zone');
                const group = zone.dataset.group;
                if (group !== 'unassigned') {{
                    const current = area.querySelectorAll('.drag-item').length;
                    if (current >= 12) {{ alert('Maximum 12 joueurs par groupe !'); return; }}
                }}
                const empty = area.querySelector('.empty-drop');
                if (empty) empty.remove();
                area.appendChild(dragged);
                updateCounts();
                updateHiddenInputs();
            }});
        }});
        function updateCounts() {{
            const u = document.querySelectorAll('#list-unassigned .drag-item').length;
            const g1 = document.querySelectorAll('#list-group1 .drag-item').length;
            const g2 = document.querySelectorAll('#list-group2 .drag-item').length;
            document.getElementById('count-unassigned').textContent = '(' + u + ')';
            document.getElementById('count-group1').textContent = '(' + g1 + '/12)';
            document.getElementById('count-group2').textContent = '(' + g2 + '/12)';
        }}
        function updateHiddenInputs() {{
            const g1 = [...document.querySelectorAll('#list-group1 .drag-item')].map(el => el.dataset.name);
            const g2 = [...document.querySelectorAll('#list-group2 .drag-item')].map(el => el.dataset.name);
            document.getElementById('input-group1').value = g1.join(',');
            document.getElementById('input-group2').value = g2.join(',');
        }}
        updateHiddenInputs();
        </script>
        """

    login_section = ""
    if show_login and not admin_user:
        login_section = """
        <section class="card" style="max-width:400px;margin:1.5rem auto">
            <h2>Connexion Admin</h2>
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="Nom de compte" required style="width:100%;margin-bottom:0.6rem;padding:0.7rem;border-radius:8px;border:1px solid rgba(0,200,83,0.3);background:rgba(0,20,0,0.5);color:#e8f5e9">
                <input type="password" name="password" placeholder="Mot de passe" required style="width:100%;margin-bottom:0.8rem;padding:0.7rem;border-radius:8px;border:1px solid rgba(0,200,83,0.3);background:rgba(0,20,0,0.5);color:#e8f5e9">
                <button type="submit" class="btn primary" style="width:100%">Se connecter</button>
            </form>
            <p style="margin-top:0.8rem;text-align:center"><a href="/" style="color:var(--green)">← Annuler</a></p>
        </section>
        """

    header_extra = ""
    if admin_user:
        header_extra = f'<p class="admin-badge">Connecté en tant que : <strong>{admin_user}</strong></p>'
    else:
        header_extra = '<p><a href="/login" class="admin-link">Connexion Admin</a></p>'

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Black Clover • Inscriptions Donjons</title>
    <link rel="stylesheet" href="/static/style.css">
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Rajdhani:wght@400;600&display=swap" rel="stylesheet">
</head>
<body>
    <div class="bg-overlay"></div>
    <div class="clover-particles" id="particles"></div>
    <header>
        <div class="logo">
            <svg class="clover-icon" viewBox="0 0 100 100" width="60" height="60">
                <path d="M50 10 C35 10 25 25 25 40 C25 50 30 55 50 70 C70 55 75 50 75 40 C75 25 65 10 50 10 Z" fill="#00c853"/>
                <path d="M50 30 C40 30 30 40 30 55 C30 65 40 75 50 90 C60 75 70 65 70 55 C70 40 60 30 50 30 Z" fill="#00e676"/>
                <circle cx="50" cy="50" r="8" fill="#1b5e20"/>
            </svg>
            <h1>BLACK CLOVER</h1>
            <p class="subtitle">Inscriptions aux Donjons • Royaume de Clover</p>
            {header_extra}
        </div>
    </header>
    <main>
        {status_html}
        {msg_html}
        {login_section}
        <section class="card register-card">
            <h2>⚔️ S'inscrire pour le prochain Donjon</h2>
            {form_html}
        </section>
        <section class="card list-card">
            <h2>📜 Liste des Inscrits ({len(players)}/24)</h2>
            {players_list}
        </section>
        <section class="card groups-card">
            <h2>🗡️ Groupes formés</h2>
            {groups_public}
        </section>
        {admin_section}
    </main>
    <footer><p>☘️ Royaume de Clover</p></footer>
    <audio id="bgm" loop preload="none"><source src="/static/music.mp3" type="audio/mpeg"></audio>
    <button id="music-toggle" class="music-btn" title="Musique">🎵</button>
    <script src="/static/main.js"></script>
</body>
</html>"""

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def get_session_user(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            if "session=" in part:
                sid = part.split("=")[1].strip()
                return sessions.get(sid)
        return None

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        data = load_data()
        user = self.get_session_user()

        if path == "/" or path == "/index.html":
            self.send_html(get_page(data, admin_user=user))
        elif path == "/login":
            if user:
                self.redirect("/")
            else:
                self.send_html(get_page(data, show_login=True))
        elif path == "/logout":
            cookie = self.headers.get("Cookie", "")
            for part in cookie.split(";"):
                if "session=" in part:
                    sid = part.split("=")[1].strip()
                    if sid in sessions:
                        del sessions[sid]
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "session=; Path=/; Max-Age=0")
            self.end_headers()
        elif path.startswith("/static/"):
            super().do_GET()
        else:
            self.send_error(404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        form = urllib.parse.parse_qs(body)
        data = load_data()
        user = self.get_session_user()

        if path == "/register":
            self.handle_register(form, data)
        elif path == "/login":
            self.handle_login(form)
        elif path == "/admin/toggle":
            if not user: return self.redirect("/")
            data["registrations_open"] = not data.get("registrations_open", True)
            save_data(data)
            self.redirect("/")
        elif path == "/admin/reset":
            if not user: return self.redirect("/")
            save_data({"registrations_open": True, "players": [], "group1": [], "group2": [], "created_at": datetime.now().isoformat()})
            self.redirect("/")
        elif path == "/admin/remove":
            if not user: return self.redirect("/")
            pseudo = form.get("pseudo", [""])[0].strip()
            data["players"] = [p for p in data["players"] if p["pseudo"] != pseudo]
            data["group1"] = [p for p in data["group1"] if p != pseudo]
            data["group2"] = [p for p in data["group2"] if p != pseudo]
            save_data(data)
            self.redirect("/")
        elif path == "/admin/groups":
            if not user: return self.redirect("/")
            g1 = [x.strip() for x in form.get("group1", [""])[0].split(",") if x.strip()][:MAX_PER_GROUP]
            g2 = [x.strip() for x in form.get("group2", [""])[0].split(",") if x.strip()][:MAX_PER_GROUP]
            g2 = [p for p in g2 if p not in g1]
            data["group1"] = g1
            data["group2"] = g2
            save_data(data)
            self.redirect("/")
        else:
            self.send_error(404)

    def handle_register(self, form, data):
        if not data.get("registrations_open", True):
            return self.send_html(get_page(data, error="Les inscriptions sont fermées."))
        if len(data["players"]) >= MAX_TOTAL:
            return self.send_html(get_page(data, error="Plus de places disponibles (24/24)."))
        pseudo = form.get("pseudo", [""])[0].strip()
        if not pseudo or len(pseudo) < 2 or len(pseudo) > 32:
            return self.send_html(get_page(data, error="Nom RP invalide (2-32 caractères)."))
        if pseudo.lower() in [p["pseudo"].lower() for p in data["players"]]:
            return self.send_html(get_page(data, error="Ce nom RP est déjà inscrit."))
        data["players"].append({"pseudo": pseudo, "registered_at": datetime.now().isoformat()})
        save_data(data)
        self.send_html(get_page(data, message=f"Bienvenue {pseudo} ! Tu es inscrit(e)."))

    def handle_login(self, form):
        username = form.get("username", [""])[0].strip().lower()
        password = form.get("password", [""])[0]
        matched = None
        for name, hashed in ADMIN_HASHES.items():
            if name.lower() == username and hash_password(password) == hashed:
                matched = name
                break
        if matched:
            sid = secrets.token_hex(16)
            sessions[sid] = matched
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", f"session={sid}; Path=/; HttpOnly")
            self.end_headers()
        else:
            data = load_data()
            self.send_html(get_page(data, error="Identifiants incorrects.", show_login=True))

    def send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(html.encode("utf-8")))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

if __name__ == "__main__":
    import os
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        save_data(load_data())

    port = int(os.environ.get("PORT", 8765))

    print("=" * 55)
    print("  ☘️  BLACK CLOVER - Inscriptions Donjons")
    print("=" * 55)
    print(f"  Port : {port}")
    print("  Comptes admin :")
    for u, p in ADMINS.items():
        print(f"    • {u}  /  {p}")
    print("=" * 55)

    with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")
