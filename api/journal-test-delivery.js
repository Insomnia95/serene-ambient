import crypto from 'node:crypto';

const RECIPIENT = 'annacranberry66@gmail.com';
const BUCKET = 'journal-downloads';
const FROM = 'Calm Veritas <journals@calm-veritas.com>';
const PRODUCTS = [
  { slug: 'anxiety-calm', title: 'Anxiety & Calm Journal', object: 'anxiety-calm.pdf', filename: 'Anxiety-and-Calm-Journal.pdf' },
  { slug: 'dream-sleep', title: 'Dream & Sleep Journal', object: 'dream-sleep.pdf', filename: 'Dream-and-Sleep-Journal.pdf' },
  { slug: 'focus-productivity', title: 'Focus & Productivity Journal', object: 'focus-productivity.pdf', filename: 'Focus-and-Productivity-Journal.pdf' },
  { slug: 'plan-reflect', title: 'Plan & Reflect Journal', object: 'plan-reflect.pdf', filename: 'Plan-and-Reflect-Journal.pdf' },
];

function authorized(req) {
  const expected = process.env.JOURNAL_TEST_TOKEN || '';
  const supplied = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
  const a = Buffer.from(supplied);
  const b = Buffer.from(expected);
  return expected && a.length === b.length && crypto.timingSafeEqual(a, b);
}

function htmlEscape(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

function emailMarkup(name, products) {
  const greeting = name ? 'Hello ' + htmlEscape(name) + ',' : 'Hello,';
  const cards = products.map((product, index) =>
    '<tr><td style="padding:' + (index ? '18px' : '0 0 18px') + ';border-bottom:1px solid #e9e2d7;">' +
      '<div style="font:600 12px Arial,sans-serif;letter-spacing:1.8px;text-transform:uppercase;color:#9c7b4c;margin:0 0 8px;">Your journal</div>' +
      '<div style="font:24px Georgia,serif;color:#20201d;margin:0 0 15px;">' + htmlEscape(product.title) + '</div>' +
      '<a href="' + htmlEscape(product.url) + '" style="display:inline-block;background:#c9a56b;color:#171715;text-decoration:none;font:700 12px Arial,sans-serif;letter-spacing:1.3px;text-transform:uppercase;padding:15px 20px;">Download your journal&nbsp; →</a>' +
    '</td></tr>',
  ).join('');
  return '<!doctype html><html><body style="margin:0;background:#f3f1ec;padding:28px 12px;">' +
    '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:620px;margin:0 auto;background:#fff;">' +
    '<tr><td style="background:#181816;padding:28px 36px;border-bottom:3px solid #c9a56b;">' +
    '<div style="font:600 13px Arial,sans-serif;letter-spacing:4px;text-transform:uppercase;color:#d2b47f;">Calm Veritas</div>' +
    '<div style="font:13px Arial,sans-serif;color:#b9b7b0;margin-top:7px;letter-spacing:1px;">JOURNALS</div></td></tr>' +
    '<tr><td style="padding:38px 36px 12px;">' +
    '<div style="font:34px/1.15 Georgia,serif;color:#20201d;margin:0 0 15px;">A quieter moment starts here.</div>' +
    '<p style="font:15px/1.8 Arial,sans-serif;color:#575750;margin:0 0 24px;">' + greeting +
    ' Thank you for choosing a Calm Veritas journal. Your digital edition is ready below.</p>' +
    '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">' + cards + '</table>' +
    '<p style="font:12px/1.7 Arial,sans-serif;color:#77756f;margin:22px 0 0;">Your secure download link is available for 7 days. You can save the PDF to your device after downloading.</p>' +
    '<p style="font:12px/1.7 Arial,sans-serif;color:#77756f;margin:20px 0 0;">Need help? Reply to this email and we’ll be glad to assist.</p>' +
    '</td></tr><tr><td style="padding:22px 36px;background:#f7f5f1;color:#8a8881;font:11px/1.6 Arial,sans-serif;">' +
    'Calm Veritas · Thoughtful pages for calmer days.<br>Digital purchase delivered securely by Calm Veritas.</td></tr>' +
    '</table></body></html>';
}

function emailText(name, products) {
  return 'Calm Veritas Journals\n\n' +
    (name ? 'Hello ' + name + ',\n\n' : 'Hello,\n\n') +
    'Thank you for choosing a Calm Veritas journal. Your digital edition is ready:\n\n' +
    products.map((product) => product.title + '\n' + product.url).join('\n\n') +
    '\n\nYour secure download link is available for 7 days. Save the PDF to your device after downloading.\n\n' +
    'Need help? Reply to this email.\n\nCalm Veritas';
}

async function supabaseRequest(path, method, key, body) {
  const response = await fetch(process.env.SUPABASE_URL + path, {
    method,
    headers: {
      apikey: key,
      Authorization: 'Bearer ' + key,
      'Content-Type': 'application/json',
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const text = await response.text();
  let parsed = null;
  try { parsed = text ? JSON.parse(text) : null; } catch {}
  if (!response.ok) throw new Error('Supabase request failed: ' + response.status);
  return parsed;
}

async function signedDownload(product, key) {
  const result = await supabaseRequest(
    '/storage/v1/object/sign/' + BUCKET + '/' + encodeURIComponent(product.object),
    'POST',
    key,
    { expiresIn: 604800, download: product.filename },
  );
  const signed = result && (result.signedURL || result.signedUrl);
  if (!signed) throw new Error('Could not create a signed download link.');
  return signed.startsWith('http') ? signed : process.env.SUPABASE_URL + '/storage/v1' + signed;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed.' });
  }
  if (!authorized(req)) return res.status(401).json({ error: 'Unauthorized.' });
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY || !process.env.RESEND_API_KEY) {
    return res.status(503).json({ error: 'Email fulfillment is not configured.' });
  }
  const runId = String((req.body && req.body.runId) || '');
  if (!/^[a-f0-9]{32}$/.test(runId)) return res.status(400).json({ error: 'Invalid run id.' });

  try {
    const key = process.env.SUPABASE_SERVICE_KEY;
    const stored = await supabaseRequest('/storage/v1/object/list/' + BUCKET, 'POST', key, {
      prefix: '', limit: 100, offset: 0, sortBy: { column: 'name', order: 'asc' },
    });
    const names = new Set(Array.isArray(stored) ? stored.map((entry) => entry.name) : []);
    const missing = PRODUCTS.filter((product) => !names.has(product.object)).map((product) => product.slug);
    if (missing.length) return res.status(409).json({ error: 'Missing uploaded journal PDFs.', missing });

    const sent = [];
    for (const product of PRODUCTS) {
      const delivery = { ...product, url: await signedDownload(product, key) };
      const response = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + process.env.RESEND_API_KEY,
          'Content-Type': 'application/json',
          'Idempotency-Key': 'calm-veritas-test-' + runId + '-' + product.slug,
        },
        body: JSON.stringify({
          from: FROM,
          to: [RECIPIENT],
          reply_to: 'calmveritas@gmail.com',
          subject: 'Your ' + product.title + ' is ready',
          html: emailMarkup('Anna', [delivery]),
          text: emailText('Anna', [delivery]),
        }),
      });
      const providerResult = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error('Resend rejected ' + product.slug + ': ' + response.status);
      sent.push({ product: product.slug, email_id: providerResult.id || null });
    }
    return res.status(200).json({ ok: true, sent });
  } catch (error) {
    console.error('Test fulfillment failed.', error.message);
    return res.status(500).json({ error: 'Test fulfillment failed.' });
  }
}
