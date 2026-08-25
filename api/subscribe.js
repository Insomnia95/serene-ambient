// Vercel serverless function — POST /api/subscribe
// Adds an email to a Resend Audience (resend.com/audiences) so newsletter
// signups actually land somewhere instead of disappearing client-side.
//
// ── SETUP (one-time, in the Resend + Vercel dashboards) ────────────────────
// 1. In Resend: go to Audience (left sidebar) → Create Audience. Name it
//    something like "Newsletter". Open it and copy its Audience ID from the
//    URL or the page (looks like a UUID).
// 2. In Vercel: Settings → Environment Variables → add
//       RESEND_AUDIENCE_ID = <the UUID from step 1>
//    for Production (and Preview), then redeploy.
// 3. This reuses the same RESEND_API_KEY already configured for the
//    contact form — no second key needed.
// 4. Once set up, every subscriber will show up in Resend under
//    Audience → Newsletter → Contacts, and you can email them from there
//    (Broadcasts) or export the list any time.
// ─────────────────────────────────────────────────────────────────────────

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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

  const email = (body.email || '').toString().trim().slice(0, 200);

  if (!email || !EMAIL_RE.test(email)) {
    return res.status(400).json({ error: 'Please enter a valid email address.' });
  }

  const RESEND_API_KEY = process.env.RESEND_API_KEY;
  const RESEND_AUDIENCE_ID = process.env.RESEND_AUDIENCE_ID;

  if (!RESEND_API_KEY || !RESEND_AUDIENCE_ID) {
    console.error('subscribe.js: RESEND_API_KEY or RESEND_AUDIENCE_ID is not set.');
    return res.status(500).json({ error: 'The server is not configured to accept subscriptions yet.' });
  }

  try {
    const resendRes = await fetch(`https://api.resend.com/audiences/${RESEND_AUDIENCE_ID}/contacts`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        unsubscribed: false,
      }),
    });

    if (!resendRes.ok) {
      const errBody = await resendRes.text().catch(() => '');
      // Resend returns 409-ish/validation errors for an email already on the
      // list — treat that as a success from the visitor's point of view.
      if (resendRes.status === 400 && /already exists|already added/i.test(errBody)) {
        return res.status(200).json({ ok: true });
      }
      console.error('subscribe.js: Resend API error', resendRes.status, errBody);
      return res.status(502).json({ error: 'Could not subscribe right now. Please try again later.' });
    }

    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('subscribe.js: unexpected error', err);
    return res.status(500).json({ error: 'Something went wrong. Please try again.' });
  }
}
