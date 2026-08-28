// Vercel serverless function — POST /api/admin-publish
// Takes a saved draft (by id) and publishes it exactly the way the daily
// content-engine publishes its own articles: writes blog/{slug}.html and
// images/pin-{slug}.jpg, prepends an entry to articles-data.js, adds a
// sitemap.xml row — all via the GitHub Contents API. If the draft has a
// pinDays value, the new entry is pinned (hero-featured) immediately.
import { requireAuth } from './_lib/auth.js';
import { getFile, putFile } from './_lib/github.js';
import { renderArticleHTML, escJsString } from './_lib/template.js';
import { insertArticleEntry } from './_lib/articlesData.js';

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

async function loadDraft(id) {
  const r = await fetch(
    `${SUPABASE_URL}/rest/v1/drafts?id=eq.${encodeURIComponent(id)}&select=*&limit=1`,
    { headers: sbHeaders() }
  );
  const data = await r.json().catch(() => []);
  if (!r.ok || !Array.isArray(data) || !data.length) return null;
  return data[0];
}

async function markPublished(id) {
  await fetch(`${SUPABASE_URL}/rest/v1/drafts?id=eq.${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: sbHeaders(),
    body: JSON.stringify({ status: 'published', updated_at: new Date().toISOString() }),
  });
}

function humanDate(d) {
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
}

function estimateReadTime(html) {
  const words = String(html || '').replace(/<[^>]+>/g, ' ').trim().split(/\s+/).filter(Boolean).length;
  return `${Math.max(1, Math.round(words / 200))} min read`;
}

export default async function handler(req, res) {
  if (!requireAuth(req, res)) return;
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed.' });
  }
  if (!SUPABASE_URL || !SERVICE_KEY) {
    return res.status(500).json({ error: 'Supabase is not configured.' });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const draftId = ((body || {}).id || '').toString();
  if (!draftId) return res.status(400).json({ error: 'Missing draft id.' });

  const draft = await loadDraft(draftId);
  if (!draft) return res.status(404).json({ error: 'Draft not found.' });

  const slug = draft.id;
  const now = new Date();
  const dateHuman = humanDate(now);
  const dateISO = now.toISOString().slice(0, 10);
  const readTime = estimateReadTime(draft.body_html);
  const pinnedUntil = draft.pin_days
    ? new Date(now.getTime() + draft.pin_days * 86400000).toISOString().slice(0, 10)
    : null;

  try {
    // 1) Image (if provided as a data URL from the browser-side canvas re-encode)
    if (draft.image_data_url) {
      const m = /^data:image\/(png|jpeg);base64,(.+)$/.exec(draft.image_data_url);
      if (!m) throw new Error('image_data_url is not a recognized base64 image.');
      const buf = Buffer.from(m[2], 'base64');
      await putFile(`images/pin-${slug}.jpg`, buf, `Admin publish: image for ${slug}`);
    }

    // 2) Article HTML
    const html = renderArticleHTML({
      title: draft.title,
      excerpt: draft.excerpt,
      tag: draft.tag,
      dateHuman,
      dateISO,
      readTime,
      slug,
      bodyHtml: draft.body_html,
      products: draft.products,
      sponsored: draft.sponsored,
    });
    await putFile(`blog/${slug}.html`, html, `Admin publish: ${draft.title}`);

    // 3) articles-data.js — prepend entry (pinned immediately if requested)
    const dataFile = await getFile('articles-data.js');
    if (!dataFile) throw new Error('articles-data.js not found on GitHub.');
    const fields = [
      `id:'${escJsString(slug)}'`,
      `cat:'${escJsString(draft.cat)}'`,
      `tag:'${escJsString(draft.tag)}'`,
      `featured:false`,
      `title:'${escJsString(draft.title)}'`,
      `excerpt:'${escJsString(draft.excerpt)}'`,
      `date:'${dateHuman}'`,
      `readTime:'${readTime}'`,
      `badge:null`,
      `href:'/blog/${slug}'`,
      `img:'/images/pin-${slug}.jpg'`,
      `author:'${escJsString(draft.author || 'Anna')}'`,
    ];
    if (draft.sponsored) fields.push('sponsored:true');
    if (pinnedUntil) fields.push(`pinnedUntil:'${pinnedUntil}'`);
    const entryLine = `{ ${fields.join(', ')} },`;
    const newDataContent = insertArticleEntry(dataFile.content, entryLine);
    await putFile('articles-data.js', newDataContent, `Admin publish: add ${slug} to articles-data.js`);

    // 4) sitemap.xml
    const sitemapFile = await getFile('sitemap.xml');
    if (sitemapFile) {
      const row = `  <url><loc>https://www.calm-veritas.com/blog/${slug}</loc><lastmod>${dateISO}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>\n`;
      const newSitemap = sitemapFile.content.includes('</urlset>')
        ? sitemapFile.content.replace('</urlset>', row + '</urlset>')
        : sitemapFile.content + row;
      await putFile('sitemap.xml', newSitemap, `Admin publish: sitemap entry for ${slug}`);
    }

    await markPublished(draftId);

    return res.status(200).json({
      ok: true,
      url: `https://www.calm-veritas.com/blog/${slug}`,
      pinnedUntil,
    });
  } catch (err) {
    console.error('admin-publish.js error', err);
    return res.status(502).json({ error: 'Publish failed: ' + err.message });
  }
}
