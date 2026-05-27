# Calm Veritas

Ambient video scenes + wellness blog.

## Structure

```
/
├── index.html          # Main ambient player
├── blog/
│   └── index.html      # Blog listing (Sleep, Anxiety, Focus, Stoicism)
├── checklists/         # PDF checklists (add here)
├── music/              # Ambient MP3s (add here)
└── vercel.json         # Vercel config
```

## Deploy to Vercel

```bash
git init
git add .
git commit -m "Initial commit"
```

Then connect this folder to Vercel via vercel.com → New Project → Import Git Repository.

## Adding a blog post

Create a new file in `blog/`, e.g. `blog/sleep-truth.html`.
Then add an entry to the `ARTICLES` array in `blog/index.html`.

## Adding music

1. Download royalty-free MP3 from pixabay.com/music/
2. Put in `music/` folder
3. Reference in `CATEGORIES` in `index.html`
