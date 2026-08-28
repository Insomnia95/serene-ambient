// Shared helper — signed session cookie for the admin panel.
// Files under api/_lib/ are ignored by Vercel's file-based routing
// (any path segment starting with "_" is excluded), so this is safe
// to import from other api/*.js functions without becoming its own endpoint.
import crypto from 'node:crypto';

const COOKIE_NAME = 'cv_admin';
const MAX_AGE_SECONDS = 7 * 24 * 60 * 60; // 7 days

function sign(payloadB64, secret) {
  return crypto.createHmac('sha256', secret).update(payloadB64).digest('hex');
}

export function createSessionCookie() {
  const secret = process.env.ADMIN_SESSION_SECRET;
  if (!secret) throw new Error('ADMIN_SESSION_SECRET is not set');
  const exp = Date.now() + MAX_AGE_SECONDS * 1000;
  const payload = Buffer.from(JSON.stringify({ exp })).toString('base64url');
  const sig = sign(payload, secret);
  return `${COOKIE_NAME}=${payload}.${sig}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${MAX_AGE_SECONDS}`;
}

export function clearSessionCookie() {
  return `${COOKIE_NAME}=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0`;
}

export function isAuthed(req) {
  const secret = process.env.ADMIN_SESSION_SECRET;
  if (!secret) return false;
  const cookieHeader = req.headers.cookie || '';
  const parts = cookieHeader.split(';').map((s) => s.trim());
  const match = parts.find((s) => s.startsWith(`${COOKIE_NAME}=`));
  if (!match) return false;
  const value = match.slice(COOKIE_NAME.length + 1);
  const dot = value.lastIndexOf('.');
  if (dot === -1) return false;
  const payload = value.slice(0, dot);
  const sig = value.slice(dot + 1);
  const expectedSig = sign(payload, secret);
  let sigBuf, expBuf;
  try {
    sigBuf = Buffer.from(sig, 'hex');
    expBuf = Buffer.from(expectedSig, 'hex');
  } catch {
    return false;
  }
  if (sigBuf.length !== expBuf.length || !crypto.timingSafeEqual(sigBuf, expBuf)) return false;
  let data;
  try {
    data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf-8'));
  } catch {
    return false;
  }
  return typeof data.exp === 'number' && data.exp > Date.now();
}

export function requireAuth(req, res) {
  if (!isAuthed(req)) {
    res.status(401).json({ error: 'Not authenticated.' });
    return false;
  }
  return true;
}
