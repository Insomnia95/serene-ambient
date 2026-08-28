// Shared helper — read/write files in the site's GitHub repo via the
// Contents API. Same technique the daily content-engine scheduled task
// uses (see push_github.py), reused here so the admin panel writes
// through the exact same trusted path instead of touching git directly.
const REPO = 'Insomnia95/serene-ambient';
const API = 'https://api.github.com';

function ghHeaders(extra) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw new Error('GITHUB_TOKEN is not set');
  return {
    Authorization: `token ${token}`,
    Accept: 'application/vnd.github.v3+json',
    ...extra,
  };
}

// Returns { sha, content(utf-8 string) } or null if the file doesn't exist.
export async function getFile(path) {
  const res = await fetch(`${API}/repos/${REPO}/contents/${path}`, { headers: ghHeaders() });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GitHub GET ${path} failed: ${res.status} ${await res.text().catch(() => '')}`);
  const data = await res.json();
  return { sha: data.sha, content: Buffer.from(data.content, 'base64').toString('utf-8') };
}

// Returns { sha, buffer(Buffer) } or null if the file doesn't exist. Use for binary files (images).
export async function getFileBuffer(path) {
  const res = await fetch(`${API}/repos/${REPO}/contents/${path}`, { headers: ghHeaders() });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GitHub GET ${path} failed: ${res.status} ${await res.text().catch(() => '')}`);
  const data = await res.json();
  return { sha: data.sha, buffer: Buffer.from(data.content, 'base64') };
}

// Creates or updates a file. `contentBuffer` may be a Buffer (binary) or a utf-8 string.
export async function putFile(path, contentBuffer, message) {
  const buf = Buffer.isBuffer(contentBuffer) ? contentBuffer : Buffer.from(contentBuffer, 'utf-8');
  let sha;
  try {
    const existing = await getFile(path);
    sha = existing ? existing.sha : undefined;
  } catch {
    sha = undefined;
  }
  const body = { message, content: buf.toString('base64') };
  if (sha) body.sha = sha;
  const res = await fetch(`${API}/repos/${REPO}/contents/${path}`, {
    method: 'PUT',
    headers: ghHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`GitHub PUT ${path} failed: ${res.status} ${await res.text().catch(() => '')}`);
  }
  return res.json();
}
