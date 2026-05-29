#!/usr/bin/env python3
"""
Calm Veritas — Панель администратора
Запуск: python3 admin.py
Открыть: http://localhost:8080
"""
import json, os, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request, urllib.error

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JS  = os.path.join(REPO_DIR, 'articles-data.js')
BLOG_DIR = os.path.join(REPO_DIR, 'blog')
CFG_FILE = os.path.join(REPO_DIR, 'admin-config.json')
PORT     = 8080

DEFAULT_CFG = {
    'supabase_url': 'https://bywoxbrugnrhcomrqats.supabase.co',
    'supabase_anon': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ5d294YnJ1Z25yaGNvbXJxYXRzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk4OTk2MzQsImV4cCI6MjA5NTQ3NTYzNH0.8mr5NCxzS3AM26ZvJK_la0NXswObvYKyXDfgS2zg2s4',
    'supabase_service': ''
}

# ── Config ──────────────────────────────────────────────────────────────

def load_cfg():
    if os.path.exists(CFG_FILE):
        with open(CFG_FILE) as f:
            d = json.load(f)
        return {**DEFAULT_CFG, **d}
    return dict(DEFAULT_CFG)

def save_cfg(cfg):
    with open(CFG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

# ── Articles data ────────────────────────────────────────────────────────

NODE_BIN = '/usr/local/bin/node'  # полный путь — работает и в launchd, и в терминале

def read_data():
    script = (
        "const fs=require('fs');"
        "const code=fs.readFileSync(" + json.dumps(DATA_JS) + ",'utf8');"
        "const fn=new Function(code+';return {ARTICLES,CHECKLISTS};');"
        "process.stdout.write(JSON.stringify(fn()));"
    )
    r = subprocess.run([NODE_BIN, '-e', script], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    d = json.loads(r.stdout)
    return {'articles': d['ARTICLES'], 'checklists': d['CHECKLISTS']}

def write_data(articles, checklists):
    def val(v):
        if v is None: return 'null'
        if isinstance(v, bool): return 'true' if v else 'false'
        return "'" + str(v).replace('\\', '\\\\').replace("'", "\\'") + "'"

    def obj(d):
        return '{ ' + ', '.join(f"{k}:{val(v)}" for k, v in d.items()) + ' }'

    lines = [
        '/* ─────────────────────────────────────────────────────────────',
        '   CALM VERITAS — Single source of truth for all articles',
        '   Loaded by: /index.html and /blog/index.html',
        '',
        '   When adding new content (daily task):',
        '     1. Add new article entries to the ARTICLES array below',
        '     2. Add new PDF entries to the CHECKLISTS array below',
        '     3. Commit and push — both pages update automatically',
        '   ───────────────────────────────────────────────────────────── */',
        '',
        'const ARTICLES = ['
    ]
    for a in articles:
        lines.append(f'  {obj(a)},')
    lines += ['];', '', 'const CHECKLISTS = [']
    for c in checklists:
        lines.append(f'  {obj(c)},')
    lines += ['];', '']
    with open(DATA_JS, 'w') as f:
        f.write('\n'.join(lines))

# ── Supabase ─────────────────────────────────────────────────────────────

def supabase_req(method, path, key_type='anon', body=None):
    cfg = load_cfg()
    url = cfg.get('supabase_url', '').rstrip('/')
    if key_type == 'service':
        key = cfg.get('supabase_service', '')
        if not key:
            return {'error': 'Service Role Key не задан. Добавь в Настройки.'}
    else:
        key = cfg.get('supabase_anon', '')
    if not url or not key:
        return {'error': 'Supabase не настроен'}
    full = url + '/rest/v1/' + path
    headers = {
        'apikey': key,
        'Authorization': 'Bearer ' + key,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(full, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            txt = resp.read().decode()
            return json.loads(txt) if txt.strip() else {'ok': True}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try: return json.loads(err)
        except: return {'error': err}

# ── HTTP handler ─────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass  # suppress logs

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        n = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)
        path = p.path
        qs   = parse_qs(p.query)

        if path == '/':
            self.send_html(DASHBOARD_HTML)

        elif path == '/api/data':
            try:    self.send_json(read_data())
            except Exception as e: self.send_json({'error': str(e)}, 500)

        elif path == '/api/settings':
            cfg = load_cfg()
            self.send_json({'supabase_url': cfg.get('supabase_url',''),
                            'supabase_anon': cfg.get('supabase_anon',''),
                            'supabase_service': cfg.get('supabase_service','')})

        elif path == '/api/forum/threads':
            d = supabase_req('GET',
                'threads?order=created_at.desc&limit=200&select=*',
                key_type='anon')
            self.send_json(d)

        elif path == '/api/forum/posts':
            tid = qs.get('thread_id', [''])[0]
            d = supabase_req('GET',
                f'posts?thread_id=eq.{tid}&order=created_at.asc&select=*',
                key_type='anon')
            self.send_json(d)

        elif path == '/api/subscribers':
            d = supabase_req('GET',
                'subscribers?order=subscribed_at.desc&limit=1000',
                key_type='service')
            self.send_json(d)

        elif path.startswith('/api/file/'):
            slug = path[len('/api/file/'):]
            fp = os.path.join(BLOG_DIR, slug + '.html')
            if os.path.exists(fp):
                with open(fp, 'r') as f: self.send_json({'content': f.read()})
            else:
                self.send_json({'error': 'Файл не найден'}, 404)

        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        body = self.read_body()

        if path == '/api/data':
            try:
                write_data(body['articles'], body['checklists'])
                self.send_json({'ok': True})
            except Exception as e:
                self.send_json({'error': str(e)}, 500)

        elif path == '/api/settings':
            cfg = load_cfg()
            cfg.update({k: v for k, v in body.items() if k in ('supabase_url','supabase_anon','supabase_service')})
            save_cfg(cfg)
            self.send_json({'ok': True})

        elif path == '/api/file':
            slug    = body.get('slug', '')
            content = body.get('content', '')
            if not slug: self.send_json({'error': 'slug required'}, 400); return
            fp = os.path.join(BLOG_DIR, slug + '.html')
            with open(fp, 'w') as f: f.write(content)
            self.send_json({'ok': True})

        elif path == '/api/git-push':
            try:
                subprocess.run(['git','add','-A'], cwd=REPO_DIR, check=True)
                msg = body.get('message', 'Admin update')
                r2 = subprocess.run(['git','commit','-m', msg], cwd=REPO_DIR,
                                    capture_output=True, text=True)
                r3 = subprocess.run(['git','push','origin','main'], cwd=REPO_DIR,
                                    capture_output=True, text=True)
                out = (r2.stdout + r3.stdout + r3.stderr).strip()
                self.send_json({'ok': True, 'output': out})
            except Exception as e:
                self.send_json({'error': str(e)}, 500)

        else:
            self.send_response(404); self.end_headers()

    def do_DELETE(self):
        path = urlparse(self.path).path

        if path.startswith('/api/forum/threads/'):
            tid = path.split('/')[-1]
            # Delete posts first, then thread (cascade should handle it, but just in case)
            supabase_req('DELETE', f'posts?thread_id=eq.{tid}', key_type='service')
            d = supabase_req('DELETE', f'threads?id=eq.{tid}', key_type='service')
            self.send_json({'ok': True} if 'error' not in d else d)

        elif path.startswith('/api/forum/posts/'):
            pid = path.split('/')[-1]
            d = supabase_req('DELETE', f'posts?id=eq.{pid}', key_type='service')
            self.send_json({'ok': True} if 'error' not in d else d)

        elif path.startswith('/api/file/'):
            slug = path[len('/api/file/'):]
            fp = os.path.join(BLOG_DIR, slug + '.html')
            if os.path.exists(fp):
                os.remove(fp)
                self.send_json({'ok': True})
            else:
                self.send_json({'error': 'Файл не найден'}, 404)

        else:
            self.send_response(404); self.end_headers()


# ── Dashboard HTML ───────────────────────────────────────────────────────

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin — Calm Veritas</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Montserrat',sans-serif;background:#f5f5f3;color:#1a1a1a;display:flex;flex-direction:column;min-height:100vh}
/* Header */
#hdr{background:#111;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 28px;height:52px;flex-shrink:0}
.hdr-logo{font-size:12px;font-weight:500;letter-spacing:.16em;text-transform:uppercase}
.hdr-logo span{opacity:.35}
.hdr-right{display:flex;align-items:center;gap:16px}
.hdr-saved{font-size:11px;color:rgba(255,255,255,.3);letter-spacing:.04em}
.btn{font-family:'Montserrat',sans-serif;font-size:10px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;padding:7px 14px;border:none;cursor:pointer;transition:background .15s}
.btn-ghost{background:transparent;color:rgba(255,255,255,.5);border:1px solid rgba(255,255,255,.18)}
.btn-ghost:hover{color:#fff;border-color:rgba(255,255,255,.45)}
/* Layout */
#layout{display:flex;flex:1;overflow:hidden}
/* Sidebar */
#sidebar{width:188px;background:#fff;border-right:1px solid #e8e8e6;flex-shrink:0;padding:20px 0;overflow-y:auto}
.nav-section{font-size:9px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:#ccc;padding:4px 18px 8px}
.nav-section:not(:first-child){margin-top:14px}
.nav-item{display:flex;align-items:center;justify-content:space-between;padding:9px 18px;font-size:12px;font-weight:400;color:#666;cursor:pointer;border-left:2px solid transparent;transition:all .12s}
.nav-item:hover{color:#1a1a1a;background:#f5f5f3}
.nav-item.active{color:#1a1a1a;font-weight:500;border-left-color:#1a1a1a;background:#f5f5f3}
.nav-badge{font-size:10px;color:#bbb;background:#f0f0ee;padding:1px 6px;border-radius:2px}
/* Content */
#content{flex:1;padding:28px 32px;overflow:auto}
.page{display:none}.page.active{display:block}
.page-title{font-size:11px;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:#555;margin-bottom:22px}
/* Table */
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e8e8e6}
th{font-size:10px;font-weight:500;letter-spacing:.12em;text-transform:uppercase;color:#aaa;padding:10px 14px;border-bottom:1px solid #e8e8e6;text-align:left;background:#fafaf8}
td{font-size:13px;color:#333;padding:11px 14px;border-bottom:1px solid #f0f0ee;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:#fafafa}
/* Badges */
.badge{font-size:9px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;padding:2px 7px;display:inline-block;border-radius:2px}
.b-sleep{background:#e8f0fe;color:#3d5afe}.b-anxiety{background:#fce4ec;color:#c62828}
.b-focus{background:#e8f5e9;color:#2e7d32}.b-stoicism{background:#fbe9e7;color:#bf360c}
.b-health{background:#f3e5f5;color:#6a1b9a}.b-books{background:#fff8e1;color:#f57f17}
.b-checklist{background:#e0f7fa;color:#006064}.b-guide{background:#f1f8e9;color:#33691e}
/* Action buttons */
.ab{font-family:'Montserrat',sans-serif;font-size:9px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;padding:5px 9px;border:none;cursor:pointer;margin-right:3px}
.ab-edit{background:#1a1a1a;color:#fff}.ab-edit:hover{background:#333}
.ab-html{background:#555;color:#fff}.ab-html:hover{background:#333}
.ab-del{background:#e53935;color:#fff}.ab-del:hover{background:#c62828}
.ab-view{background:#888;color:#fff}.ab-view:hover{background:#555}
/* Modal */
#mo{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:100;align-items:center;justify-content:center}
#mo.open{display:flex}
#mbox{background:#fff;width:720px;max-width:96vw;max-height:92vh;overflow-y:auto;display:flex;flex-direction:column}
.mhdr{background:#111;color:#fff;padding:15px 22px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.mhdr-title{font-size:11px;font-weight:500;letter-spacing:.14em;text-transform:uppercase}
.mclose{background:none;border:none;color:rgba(255,255,255,.45);cursor:pointer;font-size:22px;line-height:1;padding:0}
.mbody{padding:22px;flex:1;overflow-y:auto}
.mfoot{padding:14px 22px;border-top:1px solid #e8e8e6;display:flex;justify-content:flex-end;gap:10px;flex-shrink:0}
.form-row{margin-bottom:14px}
.form-row label{display:block;font-size:10px;font-weight:500;letter-spacing:.12em;text-transform:uppercase;color:#aaa;margin-bottom:5px}
.form-row input,.form-row select,.form-row textarea{width:100%;font-family:'Montserrat',sans-serif;font-size:13px;color:#1a1a1a;border:1px solid #e0e0e0;padding:9px 11px;background:#fff;outline:none;transition:border-color .12s}
.form-row input:focus,.form-row select:focus,.form-row textarea:focus{border-color:#1a1a1a}
.form-row textarea{resize:vertical;min-height:80px}
.form-row textarea.code{min-height:480px;font-family:monospace;font-size:12px;line-height:1.5}
.form-check{display:flex;align-items:center;gap:8px;font-size:13px;color:#555}
.form-check input{width:auto}
.btn-save{font-family:'Montserrat',sans-serif;font-size:10px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;background:#1a1a1a;color:#fff;border:none;padding:9px 22px;cursor:pointer}
.btn-save:hover{background:#333}
.btn-cancel{font-family:'Montserrat',sans-serif;font-size:10px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;background:#f5f5f3;color:#666;border:1px solid #e0e0e0;padding:9px 22px;cursor:pointer}
/* Toast */
#toast{position:fixed;bottom:22px;right:22px;background:#1a1a1a;color:#fff;padding:11px 18px;font-size:12px;letter-spacing:.04em;display:none;z-index:200;max-width:340px}
/* Forum */
.thread-row{background:#fff;border:1px solid #e8e8e6;padding:13px 16px;margin-bottom:2px;display:flex;align-items:start;justify-content:space-between;gap:12px}
.thread-ttl{font-size:14px;font-weight:400;color:#1a1a1a;line-height:1.4;margin-bottom:4px;cursor:pointer;display:inline-block}
.thread-ttl:hover{text-decoration:underline}
.thread-meta{font-size:11px;color:#bbb;letter-spacing:.01em;margin-top:3px}
.posts-area{margin-top:10px;display:none}.posts-area.open{display:block}
.post-row{background:#f9f9f7;border:1px solid #e8e8e6;border-left:3px solid #ddd;padding:10px 14px;margin-bottom:2px;display:flex;justify-content:space-between;align-items:start;gap:10px}
.post-row.op{border-left-color:#1a1a1a}
.post-auth{font-size:11px;color:#bbb;margin-bottom:5px}
.post-body{font-size:13px;color:#333;line-height:1.7}
/* Settings */
.settings-card{background:#fff;border:1px solid #e8e8e6;padding:22px;max-width:480px;margin-bottom:20px}
.settings-card-title{font-size:10px;font-weight:500;letter-spacing:.16em;text-transform:uppercase;color:#aaa;margin-bottom:18px;padding-bottom:10px;border-bottom:1px solid #f0f0ee}
/* Empty / loader */
.empty{font-size:13px;color:#bbb;padding:32px 0;text-align:center;letter-spacing:.04em}
.loader{font-size:11px;color:#bbb;padding:20px 0;letter-spacing:.1em;text-transform:uppercase}
/* Stats */
.stats{display:flex;gap:14px;margin-bottom:28px;flex-wrap:wrap}
.stat{background:#fff;border:1px solid #e8e8e6;padding:18px 22px;flex:1;min-width:100px}
.stat-n{font-size:26px;font-weight:300;letter-spacing:-.02em;color:#1a1a1a}
.stat-l{font-size:9px;font-weight:500;letter-spacing:.16em;text-transform:uppercase;color:#bbb;margin-top:4px}
</style>
</head>
<body>

<div id="hdr">
  <div class="hdr-logo">Calm Veritas <span>/ Администратор</span></div>
  <div class="hdr-right">
    <span class="hdr-saved" id="last-saved"></span>
    <button class="btn btn-ghost" onclick="gitPush()">Push to GitHub</button>
  </div>
</div>

<div id="layout">
  <nav id="sidebar">
    <div class="nav-section">Контент</div>
    <div class="nav-item active" data-page="articles" onclick="nav('articles')">Статьи <span class="nav-badge" id="nb-articles">—</span></div>
    <div class="nav-item" data-page="pdfs" onclick="nav('pdfs')">PDF <span class="nav-badge" id="nb-pdfs">—</span></div>
    <div class="nav-section">Сообщество</div>
    <div class="nav-item" data-page="forum" onclick="nav('forum')">Форум <span class="nav-badge" id="nb-forum">—</span></div>
    <div class="nav-item" data-page="subs" onclick="nav('subs')">Подписчики <span class="nav-badge" id="nb-subs">—</span></div>
    <div class="nav-section">Система</div>
    <div class="nav-item" data-page="settings" onclick="nav('settings')">Настройки</div>
  </nav>

  <main id="content">

    <!-- ARTICLES -->
    <div class="page active" id="page-articles">
      <div class="page-title">Статьи</div>
      <div id="art-wrap"><div class="loader">Загрузка...</div></div>
    </div>

    <!-- PDFS -->
    <div class="page" id="page-pdfs">
      <div class="page-title">PDF — чеклисты и гайды</div>
      <div id="pdf-wrap"><div class="loader">Загрузка...</div></div>
    </div>

    <!-- FORUM -->
    <div class="page" id="page-forum">
      <div class="page-title">Форум — Модерация</div>
      <div id="forum-wrap"><div class="loader">Загрузка...</div></div>
    </div>

    <!-- SUBSCRIBERS -->
    <div class="page" id="page-subs">
      <div class="page-title">Подписчики</div>
      <div id="subs-wrap"><div class="loader">Загрузка...</div></div>
    </div>

    <!-- SETTINGS -->
    <div class="page" id="page-settings">
      <div class="page-title">Настройки</div>
      <div class="settings-card">
        <div class="settings-card-title">Supabase</div>
        <div class="form-row"><label>URL проекта</label><input type="text" id="cfg-url" placeholder="https://xxx.supabase.co"></div>
        <div class="form-row"><label>Anon Key (чтение форума)</label><input type="text" id="cfg-anon"></div>
        <div class="form-row"><label>Service Role Key (удаление / подписчики)</label><input type="password" id="cfg-svc" placeholder="eyJhbGci..."></div>
        <button class="btn-save" onclick="saveSettings()">Сохранить</button>
      </div>
    </div>

  </main>
</div>

<!-- Modal -->
<div id="mo">
  <div id="mbox">
    <div class="mhdr">
      <span class="mhdr-title" id="m-title">Редактировать</span>
      <button class="mclose" onclick="closeMo()">×</button>
    </div>
    <div class="mbody" id="m-body"></div>
    <div class="mfoot">
      <button class="btn-cancel" onclick="closeMo()">Отмена</button>
      <button class="btn-save" onclick="saveMo()">Сохранить</button>
    </div>
  </div>
</div>

<!-- Toast -->
<div id="toast"></div>

<script>
'use strict';
let DATA = {articles:[], checklists:[]};
let saveFn = null;

const CAT_RU = {sleep:'Сон',anxiety:'Тревога',focus:'Фокус',stoicism:'Стоицизм',health:'Здоровье',books:'Книги'};
const CAT_BADGE = {sleep:'b-sleep',anxiety:'b-anxiety',focus:'b-focus',stoicism:'b-stoicism',health:'b-health',books:'b-books'};

// ── Init ─────────────────────────────────────────────
async function init() {
  await loadData();
  loadSettings();
}

async function loadData() {
  const r = await fetch('/api/data');
  if (!r.ok) { toast('Ошибка загрузки данных'); return; }
  DATA = await r.json();
  document.getElementById('nb-articles').textContent = DATA.articles.length;
  document.getElementById('nb-pdfs').textContent = DATA.checklists.length;
  renderArticles();
  renderPDFs();
}

// ── Navigation ────────────────────────────────────────
function nav(page) {
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.page === page));
  document.querySelectorAll('.page').forEach(el => el.classList.toggle('active', el.id === 'page-'+page));
  if (page === 'forum') loadForum();
  if (page === 'subs') loadSubs();
}

// ── Articles ─────────────────────────────────────────
function renderArticles() {
  const wrap = document.getElementById('art-wrap');
  if (!DATA.articles.length) { wrap.innerHTML = '<div class="empty">Нет статей</div>'; return; }
  const rows = DATA.articles.map((a,i) => `
    <tr>
      <td><span class="badge ${CAT_BADGE[a.cat]||''}">${CAT_RU[a.cat]||a.cat}</span></td>
      <td style="max-width:300px">
        <div style="font-size:13px;line-height:1.4;font-weight:400">${e(a.title)}</div>
        <div style="font-size:11px;color:#bbb;margin-top:2px">${e(a.href)}</div>
      </td>
      <td style="white-space:nowrap">${e(a.date||'—')}</td>
      <td style="white-space:nowrap">${e(a.readTime||'—')}</td>
      <td style="white-space:nowrap">
        <button class="ab ab-edit" onclick="editArt(${i})">Ред.</button>
        <button class="ab ab-html" onclick="editHTML(${i})">HTML</button>
        <button class="ab ab-del"  onclick="delArt(${i})">Удал.</button>
      </td>
    </tr>`).join('');
  wrap.innerHTML = `<table>
    <thead><tr><th>Кат.</th><th>Заголовок</th><th>Дата</th><th>Чтение</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function editArt(i) {
  const a = DATA.articles[i];
  openMo('Редактировать статью', `
    <div class="form-row"><label>Заголовок</label><input id="f0" value="${e(a.title)}"></div>
    <div class="form-row"><label>Excerpt</label><textarea id="f1">${e(a.excerpt)}</textarea></div>
    <div class="form-row"><label>Категория</label><select id="f2">
      ${Object.entries(CAT_RU).map(([v,l])=>`<option value="${v}"${a.cat===v?' selected':''}>${l}</option>`).join('')}
    </select></div>
    <div class="form-row"><label>Дата</label><input id="f3" value="${e(a.date||'')}"></div>
    <div class="form-row"><label>Время чтения</label><input id="f4" value="${e(a.readTime||'')}"></div>
    <div class="form-row"><label>URL (/blog/slug)</label><input id="f5" value="${e(a.href)}"></div>
    <div class="form-row"><label class="form-check"><input type="checkbox" id="f6"${a.featured?' checked':''}> Featured</label></div>
  `, () => {
    DATA.articles[i] = {...a,
      title: g('f0'), excerpt: g('f1'), cat: g('f2'),
      date: g('f3'), readTime: g('f4'), href: g('f5'),
      featured: document.getElementById('f6').checked
    };
    saveData(); renderArticles();
  });
}

async function editHTML(i) {
  const a = DATA.articles[i];
  const slug = a.href.replace('/blog/','');
  openMo('HTML: ' + slug, '<div class="loader">Загрузка файла...</div>', null);
  document.querySelector('.mfoot .btn-save').style.display = 'none';
  const r = await fetch('/api/file/' + slug);
  const d = await r.json();
  if (d.error) {
    document.getElementById('m-body').innerHTML = `<div class="empty">${e(d.error)}</div>`;
    return;
  }
  document.getElementById('m-body').innerHTML =
    `<div class="form-row"><textarea class="code" id="fhtml">${e(d.content)}</textarea></div>`;
  document.querySelector('.mfoot .btn-save').style.display = '';
  saveFn = async () => {
    const content = document.getElementById('fhtml').value;
    await fetch('/api/file', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug,content})});
    closeMo(); toast('HTML сохранён');
  };
}

function delArt(i) {
  if (!confirm(`Удалить статью?\n"${DATA.articles[i].title}"`)) return;
  const slug = DATA.articles[i].href.replace('/blog/','');
  DATA.articles.splice(i, 1);
  document.getElementById('nb-articles').textContent = DATA.articles.length;
  saveData();
  if (confirm('Удалить HTML файл с диска тоже?'))
    fetch('/api/file/' + slug, {method:'DELETE'});
  renderArticles();
}

// ── PDFs ──────────────────────────────────────────────
function renderPDFs() {
  const wrap = document.getElementById('pdf-wrap');
  if (!DATA.checklists.length) { wrap.innerHTML = '<div class="empty">Нет PDF</div>'; return; }
  const rows = DATA.checklists.map((c,i) => {
    const bc = c.tag === 'Guide' ? 'b-guide' : 'b-checklist';
    return `<tr>
      <td><span class="badge ${bc}">${e(c.tag)}</span></td>
      <td style="max-width:300px">${e(c.title)}</td>
      <td>${e(c.readTime||'—')}</td>
      <td style="font-size:11px;color:#bbb">${e(c.href)}</td>
      <td style="white-space:nowrap">
        <button class="ab ab-edit" onclick="editPDF(${i})">Ред.</button>
        <button class="ab ab-del"  onclick="delPDF(${i})">Удал.</button>
      </td>
    </tr>`;
  }).join('');
  wrap.innerHTML = `<table>
    <thead><tr><th>Тип</th><th>Заголовок</th><th>Объём</th><th>URL</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function editPDF(i) {
  const c = DATA.checklists[i];
  openMo('Редактировать PDF', `
    <div class="form-row"><label>Заголовок</label><input id="f0" value="${e(c.title)}"></div>
    <div class="form-row"><label>Описание</label><textarea id="f1">${e(c.excerpt)}</textarea></div>
    <div class="form-row"><label>Тип</label><select id="f2">
      <option${c.tag==='Checklist'?' selected':''}>Checklist</option>
      <option${c.tag==='Guide'?' selected':''}>Guide</option>
    </select></div>
    <div class="form-row"><label>Объём</label><input id="f3" value="${e(c.readTime||'')}"></div>
    <div class="form-row"><label>URL (/checklists/slug.pdf)</label><input id="f4" value="${e(c.href)}"></div>
  `, () => {
    DATA.checklists[i] = {...c,
      title: g('f0'), excerpt: g('f1'), tag: g('f2'), readTime: g('f3'), href: g('f4')
    };
    saveData(); renderPDFs();
  });
}

function delPDF(i) {
  if (!confirm(`Удалить PDF из списка?\n"${DATA.checklists[i].title}"`)) return;
  DATA.checklists.splice(i, 1);
  document.getElementById('nb-pdfs').textContent = DATA.checklists.length;
  saveData(); renderPDFs();
}

// ── Save data ─────────────────────────────────────────
async function saveData() {
  const r = await fetch('/api/data', {method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify({articles: DATA.articles, checklists: DATA.checklists})});
  if (r.ok) {
    const t = new Date().toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'});
    document.getElementById('last-saved').textContent = 'Сохранено в ' + t;
    toast('articles-data.js обновлён');
  } else { toast('Ошибка сохранения'); }
  closeMo();
}

// ── Forum ─────────────────────────────────────────────
async function loadForum() {
  const wrap = document.getElementById('forum-wrap');
  wrap.innerHTML = '<div class="loader">Загрузка...</div>';
  const r = await fetch('/api/forum/threads');
  const d = await r.json();
  if (!r.ok || d.error) { wrap.innerHTML = `<div class="empty">${e(d.error||'Ошибка')}</div>`; return; }
  document.getElementById('nb-forum').textContent = d.length;
  if (!d.length) { wrap.innerHTML = '<div class="empty">Форум пуст</div>'; return; }
  const CAT_F = {general:'Общее',sleep:'Сон',anxiety:'Тревога',focus:'Фокус',stoicism:'Стоицизм',health:'Здоровье',books:'Книги'};
  wrap.innerHTML = d.map(t => `
    <div class="thread-row" id="tr-${t.id}">
      <div style="flex:1;min-width:0">
        <span class="thread-ttl" onclick="togglePosts('${t.id}')">${e(t.title)}</span>
        <div class="thread-meta">
          <span class="badge ${CAT_BADGE[t.category]||''}">${CAT_F[t.category]||t.category}</span>
          · ${fmtD(t.created_at)} · ${t.reply_count||0} отв.
        </div>
        <div class="posts-area" id="posts-${t.id}"></div>
      </div>
      <button class="ab ab-del" onclick="delThread('${t.id}')">Удалить</button>
    </div>`).join('');
}

async function togglePosts(tid) {
  const area = document.getElementById('posts-' + tid);
  if (area.classList.toggle('open')) {
    area.innerHTML = '<div class="loader" style="padding:10px 0">Загрузка ответов...</div>';
    const r = await fetch('/api/forum/posts?thread_id=' + tid);
    const d = await r.json();
    if (!d.length) { area.innerHTML = '<div style="padding:8px 0;font-size:12px;color:#bbb">Нет ответов</div>'; return; }
    area.innerHTML = d.map((p,pi) => `
      <div class="post-row${pi===0?' op':''}">
        <div style="flex:1;min-width:0">
          <div class="post-auth">${fmtD(p.created_at)}</div>
          <div class="post-body">${e(p.body)}</div>
        </div>
        <button class="ab ab-del" style="flex-shrink:0" onclick="delPost('${p.id}','${tid}')">Удал.</button>
      </div>`).join('');
  }
}

async function delThread(id) {
  if (!confirm('Удалить тред и все ответы?')) return;
  const r = await fetch('/api/forum/threads/'+id, {method:'DELETE'});
  const d = await r.json();
  if (d.ok !== false) { document.getElementById('tr-'+id)?.remove(); toast('Тред удалён'); }
  else toast('Ошибка: ' + (d.error||''));
}

async function delPost(pid, tid) {
  if (!confirm('Удалить ответ?')) return;
  const r = await fetch('/api/forum/posts/'+pid, {method:'DELETE'});
  const d = await r.json();
  if (d.ok !== false) {
    const area = document.getElementById('posts-'+tid);
    area.classList.remove('open');
    await togglePosts(tid);
    toast('Ответ удалён');
  } else toast('Ошибка: ' + (d.error||''));
}

// ── Subscribers ───────────────────────────────────────
async function loadSubs() {
  const wrap = document.getElementById('subs-wrap');
  wrap.innerHTML = '<div class="loader">Загрузка...</div>';
  const r = await fetch('/api/subscribers');
  const d = await r.json();
  if (d.error) { wrap.innerHTML = `<div class="empty">${e(d.error)}</div>`; return; }
  document.getElementById('nb-subs').textContent = d.length;
  if (!d.length) { wrap.innerHTML = '<div class="empty">Нет подписчиков</div>'; return; }
  wrap.innerHTML = `<div style="margin-bottom:10px;font-size:12px;color:#888">${d.length} подписчиков</div>
    <table><thead><tr><th>Email</th><th>Дата подписки</th></tr></thead>
    <tbody>${d.map(s=>`<tr><td>${e(s.email)}</td><td>${fmtD(s.subscribed_at)}</td></tr>`).join('')}</tbody></table>`;
}

// ── Settings ──────────────────────────────────────────
async function loadSettings() {
  const r = await fetch('/api/settings');
  const d = await r.json();
  document.getElementById('cfg-url').value  = d.supabase_url  || '';
  document.getElementById('cfg-anon').value = d.supabase_anon || '';
  document.getElementById('cfg-svc').value  = d.supabase_service || '';
}

async function saveSettings() {
  const body = {
    supabase_url:     document.getElementById('cfg-url').value,
    supabase_anon:    document.getElementById('cfg-anon').value,
    supabase_service: document.getElementById('cfg-svc').value
  };
  const r = await fetch('/api/settings', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if (r.ok) toast('Настройки сохранены');
}

// ── Git Push ──────────────────────────────────────────
async function gitPush() {
  const msg = prompt('Commit message:', 'Admin: content update ' + new Date().toISOString().slice(0,10));
  if (!msg) return;
  toast('Pushing...');
  const r = await fetch('/api/git-push',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
  const d = await r.json();
  toast(d.ok ? '✓ Pushed: ' + (d.output||'').split('\\n')[0] : 'Ошибка: ' + d.error);
}

// ── Modal ─────────────────────────────────────────────
function openMo(title, body, fn) {
  document.getElementById('m-title').textContent = title;
  document.getElementById('m-body').innerHTML = body;
  document.querySelector('.mfoot .btn-save').style.display = '';
  saveFn = fn;
  document.getElementById('mo').classList.add('open');
}
function closeMo() { document.getElementById('mo').classList.remove('open'); saveFn = null; }
function saveMo()  { if (saveFn) saveFn(); }
document.getElementById('mo').addEventListener('click', ev => { if (ev.target.id==='mo') closeMo(); });

// ── Utils ─────────────────────────────────────────────
function e(s) { return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function g(id) { return document.getElementById(id)?.value ?? ''; }
function fmtD(s) { if (!s) return '—'; return new Date(s).toLocaleDateString('ru',{day:'numeric',month:'short',year:'numeric'}); }
function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg; el.style.display = 'block';
  clearTimeout(toast._t); toast._t = setTimeout(()=>el.style.display='none', 3500);
}

init();
</script>
</body>
</html>'''

# ── Main ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    server = HTTPServer(('localhost', PORT), Handler)
    print(f'\n  Calm Veritas Admin Panel')
    print(f'  Открыть: http://localhost:{PORT}\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  Остановлен.')
