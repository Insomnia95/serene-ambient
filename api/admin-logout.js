// Vercel serverless function — POST /api/admin-logout
import { clearSessionCookie } from './_lib/auth.js';

export default async function handler(req, res) {
  res.setHeader('Set-Cookie', clearSessionCookie());
  return res.status(200).json({ ok: true });
}
