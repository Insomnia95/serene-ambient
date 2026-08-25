// Vercel serverless function — POST /api/contact
// Sends the "Contact & Advertise" form (contact.html) to annacranberry66@gmail.com
// via the Resend REST API (https://resend.com). No npm dependency needed: Vercel's
// Node runtime has global fetch built in.
//
// ── SETUP (one-time, in the Vercel dashboard) ──────────────────────────────
// 1. Create a free account at https://resend.com and grab an API key
//    (Dashboard → API Keys → Create API Key).
// 2. In your Vercel project: Settings → Environment Variables → add
//       RESEND_API_KEY = re_xxxxxxxx
//    for the Production (and Preview) environment, then redeploy.
// 3. That's it — this works immediately using Resend's shared "onboarding@resend.dev"
//    sender, which does not require verifying a domain.
// 4. Optional upgrade later: verify calm-veritas.com in Resend (Domains → Add Domain,
//    add the DNS records it gives you), then change FROM_ADDRESS below to something
//    like "Calm Veritas <contact@calm-veritas.com>" for better deliverability/branding.
// ─────────────────────────────────────────────────────────────────────────

const TO_ADDRESS = 'calmveritas@gmail.com';
const FROM_ADDRESS = 'Calm Veritas <onboarding@resend.dev>';
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

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

  const name = (body.name || '').toString().trim().slice(0, 200);
  const email = (body.email || '').toString().trim().slice(0, 200);
  const reason = (body.reason || 'General').toString().trim().slice(0, 60);
  const message = (body.message || '').toString().trim().slice(0, 5000);
  const honeypot = (body.hp_confirm_2026 || '').toString().trim();

  // Honeypot: real visitors never see or fill this field. Silently accept
  // so bots don't learn their submission was rejected.
  if (honeypot) {
    return res.status(200).json({ ok: true });
  }

  if (!name || !email || !message) {
    return res.status(400).json({ error: 'Please fill in your name, email, and message.' });
  }
  if (!EMAIL_RE.test(email)) {
    return res.status(400).json({ error: 'Please enter a valid email address.' });
  }

  const RESEND_API_KEY = process.env.RESEND_API_KEY;
  if (!RESEND_API_KEY) {
    console.error('contact.js: RESEND_API_KEY is not set.');
    return res.status(500).json({ error: 'The server is not configured to send email yet.' });
  }

  const subject = `[${reason}] New message from ${name} — Calm Veritas contact form`;
  const text = `Reason: ${reason}\nName: ${name}\nEmail: ${email}\n\nMessage:\n${message}`;
  const html = `
    <p><strong>Reason:</strong> ${escapeHtml(reason)}</p>
    <p><strong>Name:</strong> ${escapeHtml(name)}</p>
    <p><strong>Email:</strong> ${escapeHtml(email)}</p>
    <p><strong>Message:</strong></p>
    <p>${escapeHtml(message).replace(/\n/g, '<br>')}</p>
  `;

  try {
    const resendRes = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: FROM_ADDRESS,
        to: [TO_ADDRESS],
        reply_to: email,
        subject,
        text,
        html,
      }),
    });

    if (!resendRes.ok) {
      const errBody = await resendRes.text().catch(() => '');
      console.error('contact.js: Resend API error', resendRes.status, errBody);
      return res.status(502).json({ error: 'Could not send your message right now. Please try again later.' });
    }

    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('contact.js: unexpected error', err);
    return res.status(500).json({ error: 'Something went wrong. Please try again.' });
  }
}
