// Vercel serverless function — /api/admin-draft
// GET: list drafts. POST: create/update a draft (upsert by id). DELETE: remove a draft.
// Drafts are stored in Supabase (table "drafts" — see the SQL in the setup notes)
// so the author can save work-in-progress and preview it before it ever touches
// the live site / GitHub.
import { requireAuth } from './_lib/auth.js';
import { slugify } from './_lib/template.js';

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

function sbHeaders(extra) {
  return {
    apikey: SERVICE_KEY,
    Authorization: `Bearer ${SERVICE_KEY}`,
    'Content-Type': 'application/json',
    ...extra,
  };
}

export default async function handler(req, res) {
  if (!requireAuth(req, res)) return;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    return res.status(500).json({ error: 'Supabase is not configured (SUPABASE_URL / SUPABASE_SERVICE_KEY).' });
  }

  if (req.method === 'GET') {
    try {
      const r = await fetch(`${SUPABASE_URL}/rest/v1/drafts?select=*&order=updated_at.desc`, {
        headers: sbHeaders(),
      });
      const data = await r.json().catch(() => []);
      if (!r.ok) return res.status(502).json({ error: 'Could not list drafts.', detail: data });
      return res.status(200).json({ drafts: data });
    } catch (e) {
      return res.status(502).json({ error: 'Could not reach Supabase (check SUPABASE_URL).', detail: String(e && e.message || e) });
    }
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  body = body || {};

  if (req.method === 'DELETE') {
    const id = (body.id || '').toString();
    if (!id) return res.status(400).json({ error: 'Missing id.' });
    try {
      const r = await fetch(`${SUPABASE_URL}/rest/v1/drafts?id=eq.${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: sbHeaders(),
      });
      return res.status(r.ok ? 200 : 502).json({ ok: r.ok });
    } catch (e) {
      return res.status(502).json({ error: 'Could not reach Supabase (check SUPABASE_URL).', detail: String(e && e.message || e) });
    }
  }

  if (req.method === 'POST') {
    const title = (body.title || '').toString().trim().slice(0, 200);
    const excerpt = (body.excerpt || '').toString().trim().slice(0, 500);
    const bodyHtml = (body.bodyHtml || '').toString().slice(0, 60000);
    const cat = (body.cat || '').toString().trim();
    const tag = (body.tag || '').toString().trim();
    const imageDataUrl = (body.imageDataUrl || '').toString().slice(0, 6_000_000); // ~4.5MB decoded cap
    const author = (body.author || 'Anna').toString().trim().slice(0, 60);
    const pinDays = body.pinDays ? Math.max(1, Math.min(90, parseInt(body.pinDays, 10) || 0)) : null;
    const sponsored = !!body.sponsored;
    const products = Array.isArray(body.products)
      ? body.products
          .filter((p) => p && p.name && p.url)
          .slice(0, 6)
          .map((p) => ({
            name: String(p.name).slice(0, 200),
            desc: String(p.desc || '').slice(0, 300),
            url: String(p.url).slice(0, 500),
          }))
      : [];

    if (!title || !excerpt || !bodyHtml || !cat || !tag) {
      return res.status(400).json({ error: 'Missing required fields (title, excerpt, bodyHtml, cat, tag).' });
    }

    let id = (body.id || '').toString().trim();
    if (!id) id = slugify(title);

    const payload = {
      id,
      title,
      excerpt,
      body_html: bodyHtml,
      cat,
      tag,
      image_data_url: imageDataUrl || null,
      author,
      pin_days: pinDays,
      sponsored,
      products,
      status: 'draft',
      updated_at: new Date().toISOString(),
    };

    try {
      const r = await fetch(`${SUPABASE_URL}/rest/v1/drafts?on_conflict=id`, {
        method: 'POST',
        headers: sbHeaders({ Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify(payload),
      });
      const data = await r.json().catch(() => null);
      if (!r.ok) return res.status(502).json({ error: 'Could not save draft.', detail: data });
      return res.status(200).json({ ok: true, draft: Array.isArray(data) ? data[0] : data });
    } catch (e) {
      return res.status(502).json({ error: 'Could not reach Supabase (check SUPABASE_URL).', detail: String(e && e.message || e) });
    }
  }

  res.setHeader('Allow', 'GET, POST, DELETE');
  return res.status(405).json({ error: 'Method not allowed.' });
}
