import crypto from 'node:crypto';

export const config = { api: { bodyParser: false } };

const PRODUCTS = {
  'pri_01m848rvyejfhvee0regfhsta2': {
    slug: 'anxiety-calm',
    title: 'Anxiety & Calm Journal',
    object: 'anxiety-calm.pdf',
    filename: 'Anxiety-and-Calm-Journal.pdf',
  },
  'pri_01m848r6jm0vmqp2wn7a4940km': {
    slug: 'dream-sleep',
    title: 'Dream & Sleep Journal',
    object: 'dream-sleep.pdf',
    filename: 'Dream-and-Sleep-Journal.pdf',
  },
  'pri_01m848qh67tydym3j4vch1cyrb': {
    slug: 'focus-productivity',
    title: 'Focus & Productivity Journal',
    object: 'focus-productivity.pdf',
    filename: 'Focus-and-Productivity-Journal.pdf',
  },
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const BUCKET = 'journal-downloads';
const FROM = 'Calm Veritas <journals@calm-veritas.com>';

function readRaw(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > 1024 * 1024) {
        reject(new Error('Payload too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function verifySignature(rawBody, header, secret) {
  if (!header || !secret) return false;
  const parts = Object.fromEntries(
    header.split(';').map((part) => part.trim().split('=', 2)).filter((p) => p.length === 2),
  );
  const ts = Number(parts.ts);
  if (!Number.isFinite(ts) || Math.abs(Date.now() / 1000 - ts) > 300 || !parts.h1) return false;
  const expected = crypto.createHmac('sha256', secret).update(String(ts) + ':').update(rawBody).digest();
  let received;
  try { received = Buffer.from(parts.h1, 'hex'); } catch { return false; }
  return received.length === expected.length && crypto.timingSafeEqual(received, expected);
}

function getPriceIds(data) {
  const fromItems = Array.isArray(data.items)
    ? data.items.map((item) => item && item.price && item.price.id).filter(Boolean)
    : [];
  const fromLineItems = data.details && Array.isArray(data.details.line_items)
    ? data.details.line_items.map((item) => item && (item.price_id || (item.price && item.price.id))).filter(Boolean)
    : [];
  return [...new Set([...fromItems, ...fromLineItems])];
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

async function supabaseRequest(path, method, key, body, extraHeaders) {
  const response = await fetch(process.env.SUPABASE_URL + path, {
    method,
    headers: {
      apikey: key,
      Authorization: 'Bearer ' + key,
      'Content-Type': 'application/json',
      ...(extraHeaders || {}),
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

async function updateOrder(key, transactionId, patch) {
  await supabaseRequest(
    '/rest/v1/journal_orders?transaction_id=eq.' + encodeURIComponent(transactionId),
    'PATCH',
    key,
    patch,
    { Prefer: 'return=minimal' },
  );
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed.' });
  }
  if (!process.env.PADDLE_WEBHOOK_SECRET || !process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY || !process.env.RESEND_API_KEY) {
    console.error('Paddle fulfillment environment is incomplete.');
    return res.status(503).json({ error: 'Fulfillment is not configured.' });
  }

  let rawBody;
  try { rawBody = await readRaw(req); } catch (error) {
    return res.status(error.message === 'Payload too large' ? 413 : 400).json({ error: 'Invalid request body.' });
  }
  if (!verifySignature(rawBody, req.headers['paddle-signature'], process.env.PADDLE_WEBHOOK_SECRET)) {
    return res.status(401).json({ error: 'Invalid signature.' });
  }

  let event;
  try { event = JSON.parse(rawBody.toString('utf8')); } catch {
    return res.status(400).json({ error: 'Invalid JSON.' });
  }
  if (event.event_type !== 'transaction.completed') return res.status(200).json({ ok: true });
  const data = event.data || {};
  if (data.status !== 'completed' || !data.id) return res.status(200).json({ ok: true });

  const products = getPriceIds(data).map((priceId) => PRODUCTS[priceId]).filter(Boolean);
  if (!products.length) return res.status(200).json({ ok: true });
  const email = String(
    (data.customer && data.customer.email) ||
    (data.custom_data && (data.custom_data.delivery_email || data.custom_data.email)) ||
    '',
  ).trim().toLowerCase();
  if (!EMAIL_RE.test(email)) {
    console.error('Completed transaction is missing a valid delivery email.', data.id);
    return res.status(422).json({ error: 'Delivery email is missing.' });
  }

  const key = process.env.SUPABASE_SERVICE_KEY;
  const transactionId = String(data.id);
  let existing;
  try {
    existing = await supabaseRequest(
      '/rest/v1/journal_orders?transaction_id=eq.' + encodeURIComponent(transactionId) + '&select=status,updated_at',
      'GET',
      key,
    );
  } catch (error) {
    console.error('Could not read order state.', error.message);
    return res.status(503).json({ error: 'Could not read order state.' });
  }
  if (Array.isArray(existing) && existing[0] && existing[0].status === 'sent') {
    return res.status(200).json({ ok: true, duplicate: true });
  }
  if (Array.isArray(existing) && existing[0] && existing[0].status === 'processing') {
    const updatedAt = Date.parse(existing[0].updated_at || '');
    if (Number.isFinite(updatedAt) && Date.now() - updatedAt < 5 * 60 * 1000) {
      return res.status(200).json({ ok: true, processing: true });
    }
  }

  try {
    if (Array.isArray(existing) && existing[0]) {
      await updateOrder(key, transactionId, {
        status: 'processing',
        event_id: event.event_id || null,
        email,
        product_slugs: products.map((product) => product.slug),
        updated_at: new Date().toISOString(),
      });
    } else {
      await supabaseRequest(
        '/rest/v1/journal_orders',
        'POST',
        key,
        {
          transaction_id: transactionId,
          event_id: event.event_id || null,
          email,
          product_slugs: products.map((product) => product.slug),
          status: 'processing',
        },
        { Prefer: 'return=minimal' },
      );
    }
  } catch (error) {
    if (String(error.message).includes('409')) return res.status(200).json({ ok: true, duplicate: true });
    console.error('Could not claim order.', error.message);
    return res.status(503).json({ error: 'Could not claim order.' });
  }

  try {
    const downloadable = await Promise.all(products.map(async (product) => ({
      ...product,
      url: await signedDownload(product, key),
    })));
    const resend = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + process.env.RESEND_API_KEY,
        'Content-Type': 'application/json',
        'Idempotency-Key': 'calm-veritas-' + transactionId,
      },
      body: JSON.stringify({
        from: FROM,
        to: [email],
        reply_to: 'calmveritas@gmail.com',
        subject: products.length === 1
          ? 'Your ' + products[0].title + ' is ready'
          : 'Your Calm Veritas journals are ready',
        html: emailMarkup(data.customer && data.customer.name, downloadable),
        text: emailText(data.customer && data.customer.name, downloadable),
      }),
    });
    if (!resend.ok) {
      const errorText = await resend.text().catch(() => '');
      console.error('Resend fulfillment error.', resend.status, errorText.slice(0, 300));
      throw new Error('Email provider rejected the message.');
    }
    await updateOrder(key, transactionId, {
      status: 'sent',
      sent_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    return res.status(200).json({ ok: true });
  } catch (error) {
    try {
      await updateOrder(key, transactionId, {
        status: 'failed',
        updated_at: new Date().toISOString(),
      });
    } catch {}
    console.error('Fulfillment failed.', error.message);
    return res.status(500).json({ error: 'Fulfillment failed; Paddle may retry.' });
  }
}
