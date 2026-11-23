import { requireAuth } from './_lib/auth.js';

const PRODUCTS = {
  'anxiety-calm': 'anxiety-calm.pdf',
  'dream-sleep': 'dream-sleep.pdf',
  'focus-productivity': 'focus-productivity.pdf',
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed.' });
  }
  if (!requireAuth(req, res)) return;

  const body = req.body || {};
  const objectName = PRODUCTS[String(body.product || '')];
  if (!objectName) return res.status(400).json({ error: 'Unknown journal.' });
  if (typeof body.file !== 'string' || body.file.length > 5000000) {
    return res.status(400).json({ error: 'Choose a PDF under 3 MB.' });
  }

  const encoded = body.file.replace(/^data:application\/pdf;base64,/i, '');
  let bytes;
  try { bytes = Buffer.from(encoded, 'base64'); } catch {
    return res.status(400).json({ error: 'The PDF could not be read.' });
  }
  if (!bytes.length || bytes.length > 3 * 1024 * 1024 || bytes.subarray(0, 5).toString() !== '%PDF-') {
    return res.status(400).json({ error: 'The selected file is not a valid PDF under 3 MB.' });
  }
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY) {
    return res.status(503).json({ error: 'File storage is not configured.' });
  }

  try {
    const response = await fetch(process.env.SUPABASE_URL + '/storage/v1/object/journal-downloads/' + objectName, {
      method: 'POST',
      headers: {
        apikey: process.env.SUPABASE_SERVICE_KEY,
        Authorization: 'Bearer ' + process.env.SUPABASE_SERVICE_KEY,
        'Content-Type': 'application/pdf',
        'x-upsert': 'true',
      },
      body: bytes,
    });
    if (!response.ok) {
      const detail = await response.text().catch(() => '');
      console.error('Journal file upload failed.', response.status, detail.slice(0, 300));
      return res.status(502).json({ error: 'Could not save the PDF securely.' });
    }
    return res.status(200).json({ ok: true, product: body.product });
  } catch (error) {
    console.error('Journal upload failed.', error.message);
    return res.status(502).json({ error: 'Could not save the PDF securely.' });
  }
}
