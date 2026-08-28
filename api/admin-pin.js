// Vercel serverless function — POST /api/admin-pin
// Pins or unpins ANY existing article (bot-written or admin-published) as
// the homepage hero for N days, and/or toggles its "Sponsored" badge.
// Only one article can be pinned at a time — pinning a new one automatically
// un-pins whatever was pinned before. Expiry is just a date comparison the
// homepage does at render time (see index.html) — nothing to "un-pin" later.
import { requireAuth } from './_lib/auth.js';
import { getFile, putFile } from './_lib/github.js';
import { setArticleFlags } from './_lib/articlesData.js';

export default async function handler(req, res) {
  if (!requireAuth(req, res)) return;
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed.' });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  body = body || {};
  const id = (body.id || '').toString();
  if (!id) return res.status(400).json({ error: 'Missing id.' });

  const unpin = !!body.unpin;
  const days = body.days ? Math.max(1, Math.min(90, parseInt(body.days, 10) || 0)) : null;
  if (!unpin && !days) return res.status(400).json({ error: 'Provide days (1-90) or unpin:true.' });

  const pinnedUntil = unpin ? null : new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);
  const flags = { pinnedUntil };
  if (typeof body.sponsored === 'boolean') flags.sponsored = body.sponsored;

  try {
    const file = await getFile('articles-data.js');
    if (!file) throw new Error('articles-data.js not found on GitHub.');
    const { content, found } = setArticleFlags(file.content, id, flags);
    if (!found) return res.status(404).json({ error: `Article id "${id}" not found.` });
    await putFile(
      'articles-data.js',
      content,
      unpin ? `Admin: unpin ${id}` : `Admin: pin ${id} until ${pinnedUntil}`
    );
    return res.status(200).json({ ok: true, id, pinnedUntil });
  } catch (err) {
    console.error('admin-pin.js error', err);
    return res.status(502).json({ error: 'Pin update failed: ' + err.message });
  }
}
