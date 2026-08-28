// Vercel serverless function — GET /api/admin-articles
// Returns the live ARTICLES + CHECKLISTS arrays as JSON, straight from
// GitHub main, so the admin panel always shows what's actually live —
// articles written by the daily scheduled task and ones published from
// this admin panel both live in the same articles-data.js file.
import { requireAuth } from './_lib/auth.js';
import { getFile } from './_lib/github.js';

export default async function handler(req, res) {
  if (!requireAuth(req, res)) return;
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Method not allowed.' });
  }

  let file;
  try {
    file = await getFile('articles-data.js');
  } catch (err) {
    console.error('admin-articles.js: GitHub error', err);
    return res.status(502).json({ error: 'Could not read articles-data.js from GitHub.' });
  }
  if (!file) return res.status(404).json({ error: 'articles-data.js not found.' });

  let ARTICLES = [];
  let CHECKLISTS = [];
  try {
    // articles-data.js is our own trusted, bot/admin-authored file — it only
    // ever declares `const ARTICLES = [...]` and `const CHECKLISTS = [...]`.
    const fn = new Function(`${file.content}\nreturn { ARTICLES, CHECKLISTS };`);
    ({ ARTICLES, CHECKLISTS } = fn());
  } catch (err) {
    console.error('admin-articles.js: parse error', err);
    return res.status(500).json({ error: 'Failed to parse articles-data.js: ' + err.message });
  }

  return res.status(200).json({ articles: ARTICLES, checklists: CHECKLISTS });
}
