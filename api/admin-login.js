// Vercel serverless function — POST /api/admin-login
// Checks the admin password (ADMIN_PASSWORD env var) and, if correct, issues
// a signed HttpOnly session cookie. The password and the signing secret are
// two separate env vars on purpose — never hardcode either in this file.
import crypto from 'node:crypto';
import { createSessionCookie } from './_lib/auth.js';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed.' });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  body = body || {};
  const password = (body.password || '').toString();

  const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD;
  const ADMIN_SESSION_SECRET = process.env.ADMIN_SESSION_SECRET;
  if (!ADMIN_PASSWORD || !ADMIN_SESSION_SECRET) {
    console.error('admin-login.js: ADMIN_PASSWORD or ADMIN_SESSION_SECRET is not set.');
    return res.status(500).json({ error: 'Admin panel is not configured yet.' });
  }

  const a = Buffer.from(password);
  const b = Buffer.from(ADMIN_PASSWORD);
  const ok = a.length === b.length && crypto.timingSafeEqual(a, b);
  if (!ok) {
    return res.status(401).json({ error: 'Wrong password.' });
  }

  res.setHeader('Set-Cookie', createSessionCookie());
  return res.status(200).json({ ok: true });
}
