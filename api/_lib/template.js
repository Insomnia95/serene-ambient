// Shared helper — renders a full blog article HTML page from structured
// fields, matching the exact template used by the daily content-engine
// (same head boilerplate, styles, nav, share bar, footer) so admin-published
// articles look identical to bot-published ones.

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Escapes a string for safe embedding inside a single-quoted JS string literal
// (used when writing entries into articles-data.js).
export function escJsString(str) {
  return String(str || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

export function slugify(title) {
  return String(title || '')
    .toLowerCase()
    .trim()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-+|-+$)/g, '')
    .slice(0, 80) || 'article';
}

// Very small "plain text -> paragraphs" fallback: used when the author writes
// plain text with blank lines between paragraphs instead of raw HTML.
export function autoParagraphs(text) {
  return String(text || '')
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => `<p>${escHtml(block).replace(/\n/g, '<br>')}</p>`)
    .join('\n');
}

function productsBlock(products) {
  const list = Array.isArray(products) ? products.filter((p) => p && p.name && p.url) : [];
  if (!list.length) return '';
  const items = list
    .slice(0, 6)
    .map(
      (p, i) => `
  <div class="product-item">
    <div class="product-num">${String(i + 1).padStart(2, '0')}</div>
    <div>
      <div class="product-name">${escHtml(p.name)}</div>
      ${p.desc ? `<div class="product-desc">${escHtml(p.desc)}</div>` : ''}
      <a class="product-link" href="${escHtml(p.url)}" target="_blank" rel="noopener sponsored">View on Amazon →</a>
    </div>
  </div>`
    )
    .join('');
  return `
<div class="products">
  <div class="products-title">Referenced & Recommended</div>${items}
  <p class="disclosure" style="margin-top:16px;">These are affiliate links — if you purchase, we earn a small commission at no cost to you. We only list products we've researched and believe in. <a href="/disclosure.html" style="color:#bbb">Read our disclosure.</a></p>
</div>`;
}

export function renderArticleHTML({
  title,
  excerpt,
  tag,
  dateHuman,
  dateISO,
  readTime,
  slug,
  bodyHtml,
  products,
  sponsored,
}) {
  const t = escHtml(title);
  const desc = escHtml(excerpt);
  const imgPath = `/images/pin-${slug}.jpg`;
  const canonical = `https://www.calm-veritas.com/blog/${slug}`;
  const sponsoredNote = sponsored
    ? `<p class="disclosure" style="margin:-24px 0 32px;">This is sponsored content. <a href="/disclosure.html" style="color:#bbb">Read our disclosure.</a></p>`
    : '';

  return `<!DOCTYPE html>
<html lang="en">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-DJE2HJVD6N"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-DJE2HJVD6N');
</script>
<meta charset="UTF-8">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${t} — Calm Veritas</title>
<meta name="description" content="${desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500&display=optional" rel="stylesheet">
<style>
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Montserrat',sans-serif; background:#f5f5f3; color:#1a1a1a; -webkit-font-smoothing:antialiased; }
#header { background:#111; padding:0 40px; }
.header-top { display:flex; align-items:center; justify-content:space-between; padding:20px 0; border-bottom:1px solid rgba(255,255,255,.08); }
.logo { text-decoration:none; display:flex; align-items:center; }
.logo img { height:48px; display:block; }
.header-nav { display:flex; gap:24px; align-items:center; }
.header-nav a { font-size:12px; font-weight:400; letter-spacing:.08em; text-transform:uppercase; color:rgba(255,255,255,.5); text-decoration:none; transition:color .15s; }
.header-nav a:hover { color:#fff; }
article { max-width:720px; margin:56px auto; padding:0 40px 80px; }
.art-tag { font-size:10px; font-weight:500; letter-spacing:.16em; text-transform:uppercase; color:#999; margin-bottom:14px; }
h1 { font-size:32px; font-weight:400; letter-spacing:-.02em; line-height:1.25; color:#1a1a1a; margin-bottom:14px; }
.art-meta { font-size:11px; font-weight:300; letter-spacing:.06em; color:#bbb; margin-bottom:40px; text-transform:uppercase; }
p { font-size:15px; font-weight:300; letter-spacing:.02em; line-height:1.9; color:#333; margin-bottom:22px; }
h2 { font-size:18px; font-weight:500; letter-spacing:-.01em; color:#1a1a1a; margin:40px 0 14px; }
h3 { font-size:15px; font-weight:500; letter-spacing:.01em; color:#444; margin:28px 0 10px; }
.aff-link { color:#1a1a1a; border-bottom:1px solid #ccc; text-decoration:none; }
.aff-link:hover { border-bottom-color:#1a1a1a; }
.products { background:#fff; border:1px solid #e8e8e6; padding:28px 32px; margin:40px 0; }
.products-title { font-size:11px; font-weight:500; letter-spacing:.14em; text-transform:uppercase; color:#999; margin-bottom:20px; }
.product-item { display:flex; align-items:flex-start; gap:16px; padding:14px 0; border-bottom:1px solid #f0f0ee; }
.product-item:last-child { border-bottom:none; padding-bottom:0; }
.product-num { font-size:11px; font-weight:500; color:#bbb; flex-shrink:0; padding-top:2px; }
.product-name { font-size:14px; font-weight:400; color:#1a1a1a; margin-bottom:4px; }
.product-desc { font-size:12px; font-weight:300; color:#888; line-height:1.6; }
.product-link { display:inline-block; margin-top:8px; font-size:11px; font-weight:500; letter-spacing:.06em; text-transform:uppercase; color:#1a1a1a; border-bottom:1px solid #1a1a1a; text-decoration:none; }
.disclosure { font-size:11px; font-weight:300; color:#bbb; letter-spacing:.02em; margin-top:8px; }
.back-link { display:inline-block; font-size:11px; font-weight:400; letter-spacing:.1em; text-transform:uppercase; color:#999; text-decoration:none; margin-bottom:32px; }
.back-link:hover { color:#1a1a1a; }
footer { text-align:center; padding:24px; border-top:1px solid #e8e8e6; font-size:9px; font-weight:300; letter-spacing:.08em; color:#bbb; }
footer a { color:#888; text-decoration:none; margin:0 8px; }
.burger { display:none; flex-direction:column; gap:5px; cursor:pointer; padding:4px; background:none; border:none; }
.burger span { display:block; width:22px; height:2px; background:rgba(255,255,255,.7); transition:all .25s; }
.burger.open span:nth-child(1) { transform:translateY(7px) rotate(45deg); }
.burger.open span:nth-child(2) { opacity:0; }
.burger.open span:nth-child(3) { transform:translateY(-7px) rotate(-45deg); }
@media (max-width:680px) {
  #header { padding:0 20px; }
  .burger { display:flex; }
  .header-nav { display:none; flex-direction:column; gap:0; position:absolute; top:100%; left:0; right:0; background:#111; border-top:1px solid rgba(255,255,255,.08); z-index:100; }
  .header-nav.open { display:flex; }
  .header-nav a { padding:14px 20px; border-bottom:1px solid rgba(255,255,255,.06); font-size:12px; letter-spacing:.1em; }
  #header { position:relative; }
}
.share-bar { display:flex; align-items:center; gap:10px; margin:24px 0 32px; flex-wrap:wrap; }
.share-label { font-size:10px; font-weight:500; letter-spacing:.14em; text-transform:uppercase; color:#bbb; margin-right:4px; }
.share-btn { display:inline-flex; align-items:center; gap:6px; padding:7px 12px; border:1px solid #e0e0de; background:#fff; color:#555; text-decoration:none; font-size:11px; font-weight:400; letter-spacing:.04em; cursor:pointer; font-family:'Montserrat',sans-serif; transition:border-color .15s, color .15s; }
.share-btn:hover { border-color:#999; color:#1a1a1a; }
.share-copy .copy-done { display:none; }
.share-copy.copied .copy-label { display:none; }
.share-copy.copied .copy-done { display:inline; color:#1a1a1a; }
/* NAV SEARCH */
.nav-search { display:flex; align-items:center; position:relative; }
.nav-search input { background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.16); border-radius:20px; padding:6px 12px 6px 30px; font-family:'Montserrat',sans-serif; font-size:11px; font-weight:300; letter-spacing:.02em; color:#fff; width:110px; transition:width .2s ease, background .2s ease; }
.nav-search input::placeholder { color:rgba(255,255,255,.35); }
.nav-search input:focus { width:160px; background:rgba(255,255,255,.13); outline:none; border-color:rgba(255,255,255,.32); }
.nav-search svg { position:absolute; left:10px; width:12px; height:12px; pointer-events:none; }
@media (max-width:680px) {
  .header-nav .nav-search { padding:14px 20px; }
  .header-nav .nav-search input { width:100%; }
}
.art-img { margin:36px auto; max-width:360px; display:block; aspect-ratio:2/3; background:#f0f0ee; }
.art-img img { width:100%; height:100%; display:block; border-radius:2px; object-fit:cover; }
@media(max-width:600px){article{padding:0 18px 60px;margin:32px auto;}h1{font-size:24px;}p{font-size:14px;}}
</style>
<link rel="canonical" href="${canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="${t}">
<meta property="og:description" content="${desc}">
<meta property="og:url" content="${canonical}">
<meta property="og:image" content="https://www.calm-veritas.com${imgPath}">
<meta property="og:site_name" content="Calm Veritas">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${t}">
<meta name="twitter:description" content="${desc}">
<meta name="twitter:image" content="https://www.calm-veritas.com${imgPath}">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "${t}",
  "description": "${desc}",
  "url": "${canonical}",
  "datePublished": "${dateISO}",
  "dateModified": "${dateISO}",
  "author": {"@type": "Organization", "name": "Calm Veritas"},
  "publisher": {
    "@type": "Organization",
    "name": "Calm Veritas",
    "logo": {"@type": "ImageObject", "url": "https://www.calm-veritas.com/logo-dark.png"}
  },
  "image": "https://www.calm-veritas.com${imgPath}",
  "mainEntityOfPage": {"@type": "WebPage", "@id": "${canonical}"}
}
</script>
</head>
<body>
<header id="header">
  <div class="header-top">
    <a class="logo" href="/"><img src="/logo-dark.png" alt="Calm Veritas" style="filter:invert(1);"></a>
    <nav class="header-nav" id="hn">
      <a href="/">Home</a>
      <a href="/blog/">Blog</a>
      <a href="/downloads/">Downloads</a>
      <a href="/forum.html">Community</a>
    <form class="nav-search" action="/blog/" method="get">
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.4)" stroke-width="2.4" stroke-linecap="round"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.2" y2="16.2"></line></svg>
  <input type="text" name="q" placeholder="Search" autocomplete="off">
</form>
</nav>
    <button class="burger" id="burger" aria-label="Menu" onclick="var n=document.getElementById('hn');var b=document.getElementById('burger');n.classList.toggle('open');b.classList.toggle('open');"><span></span><span></span><span></span></button>
  </div>
</header>
<article>
  <a class="back-link" href="/blog/">← Back to blog</a>
  <div class="art-tag">${escHtml(tag)}</div>
  <h1>${t}</h1>
  <div class="art-meta">${escHtml(dateHuman)} · ${escHtml(readTime)}</div>
${sponsoredNote}
<div class="share-bar">
  <span class="share-label">Share</span>
  <a class="share-btn" id="share-x" href="#" target="_blank" rel="noopener" aria-label="Share on X">
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.737-8.835L1.254 2.25H8.08l4.253 5.622 5.911-5.622Zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
  </a>
  <a class="share-btn" id="share-fb" href="#" target="_blank" rel="noopener" aria-label="Share on Facebook">
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
  </a>
  <a class="share-btn" id="share-pin" href="#" target="_blank" rel="noopener" aria-label="Share on Pinterest">
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12c0 5.084 3.163 9.426 7.627 11.174-.105-.949-.2-2.405.042-3.441.218-.937 1.407-5.965 1.407-5.965s-.359-.719-.359-1.782c0-1.668.967-2.914 2.171-2.914 1.023 0 1.518.769 1.518 1.69 0 1.029-.655 2.568-.994 3.995-.283 1.194.599 2.169 1.777 2.169 2.133 0 3.772-2.249 3.772-5.495 0-2.873-2.064-4.882-5.012-4.882-3.414 0-5.418 2.561-5.418 5.207 0 1.031.397 2.138.893 2.738a.36.36 0 0 1 .083.345l-.333 1.36c-.053.22-.174.267-.402.161-1.499-.698-2.436-2.889-2.436-4.649 0-3.785 2.75-7.262 7.929-7.262 4.163 0 7.398 2.967 7.398 6.931 0 4.136-2.607 7.464-6.227 7.464-1.216 0-2.359-.632-2.75-1.378l-.748 2.853c-.271 1.043-1.002 2.35-1.492 3.146C9.57 23.812 10.763 24 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0z"/></svg>
  </a>
  <button class="share-btn share-copy" id="share-copy" aria-label="Copy link" onclick="navigator.clipboard.writeText(window.location.href).then(()=>{this.classList.add('copied');setTimeout(()=>this.classList.remove('copied'),2000)})">
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
    <span class="copy-label">Copy</span>
    <span class="copy-done">Copied!</span>
  </button>
</div>
<script>
(function(){
  var url = encodeURIComponent(window.location.href);
  var title = encodeURIComponent(document.title.replace(' — Calm Veritas',''));
  var img = encodeURIComponent(document.querySelector('meta[property="og:image"]')?.content || '');
  document.getElementById('share-x').href = 'https://twitter.com/intent/tweet?url='+url+'&text='+title;
  document.getElementById('share-fb').href = 'https://www.facebook.com/sharer/sharer.php?u='+url;
  document.getElementById('share-pin').href = 'https://pinterest.com/pin/create/button/?url='+url+'&media='+img+'&description='+title;
})();
</script>

<figure class="art-img">
  <img src="${imgPath}" alt="${t}" loading="lazy">
</figure>

${bodyHtml}
${productsBlock(products)}
</article>
<footer>
  <a href="/">Home</a> · <a href="/blog/">Blog</a> · <a href="/downloads/">Downloads</a> · <a href="/disclosure.html">Disclosure</a> · <a href="/privacy-policy.html">Privacy</a>
  <div style="margin-top:12px;display:flex;align-items:center;justify-content:center;gap:16px;">
    <span>© 2026 Calm Veritas · No fluff. Just truth.</span>
    <a href="https://www.youtube.com/@Calm-Veritas" target="_blank" rel="noopener" aria-label="YouTube" style="display:inline-flex;align-items:center;color:#bbb;text-decoration:none;transition:color .15s;" onmouseover="this.style.color='#FF0000'" onmouseout="this.style.color='#bbb'"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg></a>
  </div>
</footer>
</body>
</html>`;
}
