const fs = require('fs');
const path = require('path');

const POSTS_DIR = path.join(__dirname, '../posts');
const DIST_DIR = path.join(__dirname, '../'); // Root for GitHub Pages
const BASE_URL = 'https://chnmotoTmz.github.io';

// HTML Wrapper Template for individual posts
const POST_WRAPPER = (title, content, date, description, category) => `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title} | Humanoid Media Factory</title>
    <meta name="description" content="${description}">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Sans+JP:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <div class="topbar">
      <div class="topbar-inner">
        <div class="topbar-left">
          <span>Vol.08 No.${Math.floor(Math.random() * 900) + 100}</span>
          <span>${new Date(date).toLocaleDateString('ja-JP', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' })}</span>
          <span>${category || 'Automated Content Pipeline'}</span>
        </div>
        <div class="topbar-right">
          <a href="index.html" style="color: var(--accent); font-weight: 600;">← PORTAL HOME</a>
        </div>
      </div>
    </div>

    <main class="wrapper">
        <article>
            <header>
                <h1>${title}</h1>
                <div class="post-meta">
                    <time>${date}</time> | <span>${category || 'Uncategorized'}</span>
                </div>
            </header>
            <div class="content">
                ${content}
            </div>
        </article>
    </main>

    <footer>
      <div class="footer-bottom">
        <span>© 2026 chnmotoTmz · Humanoid Media Factory</span>
        <span>Powered by Gemini × LINE × GitHub</span>
      </div>
    </footer>
</body>
</html>
`;

function extractMetadata(content) {
    const meta = {};
    const match = content.match(/<!--([\s\S]*?)-->/);
    if (match) {
        const lines = match[1].trim().split('\n');
        lines.forEach(line => {
            const part = line.split(':');
            if (part.length >= 2) {
                meta[part[0].trim().toLowerCase()] = part.slice(1).join(':').trim();
            }
        });
    }
    return meta;
}

function getExcerpt(html) {
    // Remove style, script, and comments
    let clean = html.replace(/<style[\s\S]*?<\/style>/gi, '');
    clean = clean.replace(/<script[\s\S]*?<\/script>/gi, '');
    clean = clean.replace(/<!--[\s\S]*?-->/g, '');
  // Remove leaked CSS-like fragments even when they are plain text
  clean = clean.replace(/@import\s+url\([^)]*\);?/gi, '');
  clean = clean.replace(/[.#]?[\w\-\s,>]+\{[^{}]*\}/g, '');
  clean = clean.replace(/\b[a-z\-]+\s*:\s*[^;{}]+;/gi, '');
    // Remove tags
    clean = clean.replace(/<[^>]*>/g, '').trim();
    // Decode basic entities if needed or just collapse spaces
    clean = clean.replace(/\s+/g, ' ');
    return clean.substring(0, 160) + '...';
}

function getThumbnailFromContent(html) {
    const imgMatch = html.match(/<img[^>]+src=["']([^"']+)["']/i);
    return imgMatch ? imgMatch[1] : '';
}

function normalizeThumbnailUrl(url) {
  const raw = String(url || '').trim();
  if (!raw) return '';
  if (/^(https?:)?\/\//i.test(raw) || raw.startsWith('data:')) return raw;
  if (raw.startsWith('/')) return `${BASE_URL}${raw}`;

  let normalized = raw;
  if (normalized.startsWith('./')) normalized = normalized.slice(2);
  while (normalized.startsWith('../')) {
    normalized = normalized.slice(3);
  }
  return normalized;
}

function normalizeCategory(category) {
    const val = String(category || '').toLowerCase();
    if (val.includes('humanoid')) return 'humanoid';
    if (val.includes('music')) return 'music';
    if (val.includes('雑記')) return 'zatsuki';
    return 'zatsuki';
}

function categoryLabel(category) {
    const key = normalizeCategory(category);
    if (key === 'humanoid') return 'HUMANOID';
    if (key === 'music') return 'MUSIC';
    return '雑記';
}

function categoryBadgeClass(category) {
    const key = normalizeCategory(category);
    if (key === 'humanoid') return 'badge--humanoid';
    if (key === 'music') return 'badge--music';
    return 'badge--zatsuki';
}

function placeholderSvgDataUri(category) {
    const label = categoryLabel(category);
    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#242420"/>
      <stop offset="100%" stop-color="#1a1a18"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="675" fill="url(#g)"/>
  <rect x="24" y="24" width="1152" height="627" fill="none" stroke="#333330" stroke-width="2"/>
  <text x="60" y="380" fill="#e8e4dc" font-family="IBM Plex Sans JP, sans-serif" font-size="56" font-weight="700">Humanoid Media Factory</text>
  <text x="60" y="450" fill="#888880" font-family="IBM Plex Sans JP, sans-serif" font-size="36">${label}</text>
</svg>`;
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function renderCard(post, options = {}) {
    const isHero = Boolean(options.hero);
    const dateText = post.date || '';
    const category = categoryLabel(post.category);
    const categoryKey = normalizeCategory(post.category);
    const badgeClass = categoryBadgeClass(post.category);
    const thumb = normalizeThumbnailUrl(post.thumbnail) || placeholderSvgDataUri(post.category);
    const placeholder = placeholderSvgDataUri(post.category);

    if (isHero) {
        // Hero card: body positioned as overlay INSIDE the thumb container
        return `
<article class="card card--hero" data-category="${categoryKey}">
  <a class="card__link" href="${post.url}" aria-label="${post.title}">
    <div class="card__thumb">
      <img src="${thumb}" alt="${post.title}" loading="lazy" onerror="this.src='${placeholder}'">
      <span class="card__badge ${badgeClass}">${category}</span>
      <div class="card__body">
        <h2 class="card__title">${post.title}</h2>
        <footer class="card__meta">
          <time>${dateText}</time>
          <span class="card__ai-label">✦ Gemini生成</span>
        </footer>
      </div>
    </div>
  </a>
</article>`;
    }

    return `
<article class="card" data-category="${categoryKey}">
  <a class="card__link" href="${post.url}" aria-label="${post.title}">
    <div class="card__thumb">
      <img src="${thumb}" alt="${post.title}" loading="lazy" onerror="this.src='${placeholder}'">
      <span class="card__badge ${badgeClass}">${category}</span>
    </div>
    <div class="card__body">
      <h2 class="card__title">${post.title}</h2>
      <footer class="card__meta">
        <time>${dateText}</time>
        <span class="card__ai-label">✦ Gemini生成</span>
      </footer>
    </div>
  </a>
</article>`;
}

  function normalizePostContent(html) {
    if (!html) return '';
    let clean = html;

    const bodyMatch = clean.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    if (bodyMatch && bodyMatch[1]) {
      clean = bodyMatch[1];
    }

    clean = clean.replace(/<!DOCTYPE[^>]*>/gi, '');
    clean = clean.replace(/<html[^>]*>/gi, '');
    clean = clean.replace(/<\/html>/gi, '');
    clean = clean.replace(/<head[\s\S]*?<\/head>/gi, '');
    clean = clean.replace(/<body[^>]*>/gi, '');
    clean = clean.replace(/<\/body>/gi, '');
    clean = clean.replace(/<link[^>]*>/gi, '');
    clean = clean.replace(/<style[\s\S]*?<\/style>/gi, '');
    clean = clean.replace(/@import\s+url\([^)]*\);?/gi, '');
    clean = clean.trim();

    return clean;
  }

async function build() {
    console.log('🚀 Synchronizing Humanoid Media Factory Portal...');

    if (!fs.existsSync(POSTS_DIR)) {
        console.error('Error: Posts directory not found');
        return;
    }

    // Handle nested categories if they exist, otherwise just root of posts
    const getFiles = (dir) => {
        let results = [];
        const list = fs.readdirSync(dir);
        list.forEach(file => {
            const filePath = path.join(dir, file);
            const stat = fs.statSync(filePath);
            if (stat && stat.isDirectory()) {
                results = results.concat(getFiles(filePath));
            } else if (file.endsWith('.html')) {
                results.push(filePath);
            }
        });
        return results;
    };

    const allFiles = getFiles(POSTS_DIR);
    const posts = [];

    allFiles.forEach(filePath => {
        const rawContent = fs.readFileSync(filePath, 'utf8');
      const normalizedContent = normalizePostContent(rawContent);
        const meta = extractMetadata(rawContent);
        const fileName = path.basename(filePath);
        const slug = path.basename(fileName, '.html');

        // Determine category from directory structure or metadata
        const relativePath = path.relative(POSTS_DIR, filePath);
        const pathParts = relativePath.split(path.sep);
        const dirCategory = pathParts.length > 1 ? pathParts[0] : null;

        const post = {
            title: meta.title || 'Untitled',
            date: meta.date || new Date().toISOString().split('T')[0],
            description: meta.description || '',
            category: meta.category || dirCategory || '雑記',
            emoji: meta.emoji || '🦾',
            kicker: meta.kicker || 'REPORT',
            excerpt: getExcerpt(normalizedContent),
          thumbnail: getThumbnailFromContent(normalizedContent),
            slug: slug,
            url: `${slug}.html`
        };

        // Wrap the partial HTML into a full page
          const fullContent = POST_WRAPPER(post.title, normalizedContent, post.date, post.description, post.category);
        fs.writeFileSync(path.join(DIST_DIR, `${slug}.html`), fullContent);

        posts.push(post);
        console.log(`- Refined ${slug}.html`);
    });

    // Sort descending
    posts.sort((a, b) => new Date(b.date) - new Date(a.date));

    // Data for templates
    const featured   = posts[0] || null;
    const heroSide1  = posts[1] || null;
    const heroSide2  = posts[2] || null;
    const heroSide3  = posts[3] || null;
    const heroSide4  = posts[4] || null;
    const gridPosts  = posts.slice(5);
    const tickerText = posts.slice(0, 5).map(p => p.title).join('  •  ');

    const categories = [...new Set(posts.map(p => p.category))];
    const catCounts = categories.map(c => ({
        name: c,
        count: posts.filter(p => p.category === c).length
    }));

    const indexHtml = `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Humanoid Media Factory</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Sans+JP:wght@300;400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>

<div class="ticker-strip" role="status" aria-live="polite">
  <div class="ticker-strip__inner">
    <span class="ticker-strip__live">LIVE GENERATE</span>
    <div class="ticker-strip__track">
      <div class="ticker-strip__content">${tickerText} • ${tickerText}</div>
    </div>
  </div>
</div>

<header class="site-header">
  <div class="site-header__inner">
    <a class="brand" href="index.html">Humanoid Media Factory</a>
    <nav class="header-nav" aria-label="カテゴリー">
      <button class="tab is-active" data-filter="all">すべて</button>
      <button class="tab" data-filter="humanoid">HUMANOID</button>
      <button class="tab" data-filter="music">MUSIC</button>
      <button class="tab" data-filter="zatsuki">雑記</button>
    </nav>
    <div class="header-tools">
      <input class="search" id="searchInput" type="search" placeholder="記事を検索..." aria-label="記事を検索">
      <span class="status-badge">${posts.length}本公開</span>
      <span class="status-badge">98%生成率</span>
    </div>
  </div>
</header>

<main class="portal">
  <section class="hero-grid">
    ${featured ? renderCard(featured, { hero: true }) : ''}
    <div class="hero-side">
      ${heroSide1 ? renderCard(heroSide1) : ''}
      ${heroSide2 ? renderCard(heroSide2) : ''}
      ${heroSide3 ? renderCard(heroSide3) : ''}
      ${heroSide4 ? renderCard(heroSide4) : ''}
    </div>
  </section>

  <div class="section-label">最新記事 — ${posts.length}本公開中</div>

  <section class="cards-grid" id="cardsGrid">
    ${gridPosts.map(p => renderCard(p)).join('')}
  </section>
</main>

<footer>
  <div class="footer-inner">
    <div>
      <div class="footer-title">Humanoid <span>Media</span> Factory 🦾</div>
      <p class="footer-desc">AIとロボットが紡ぐ、次世代コンテンツパイプライン。<br>LINEに書いたひとことが、記事になる。毎日自動更新中。</p>
    </div>
    <div>
      <div class="footer-col-title">カテゴリー</div>
      <ul class="footer-links">
        ${categories.slice(0, 5).map(c => `<li>${c}</li>`).join('')}
      </ul>
    </div>
    <div>
      <div class="footer-col-title">メディア</div>
      <ul class="footer-links">
        <li>📝 はてなブログ</li>
        <li>🐙 GitHub Pages</li>
        <li>📱 LINE公式</li>
        <li>🔗 RSS</li>
      </ul>
    </div>
  </div>
  <div class="footer-bottom">
    <span>© 2026 chnmotoTmz · Humanoid Media Factory</span>
    <span>Powered by Gemini × LINE × GitHub</span>
  </div>
</footer>

<script>
(() => {
  const tabs = document.querySelectorAll('.tab[data-filter]');
  const cards = document.querySelectorAll('.card[data-category]');
  const searchInput = document.getElementById('searchInput');
  let activeFilter = 'all';

  const applyFilter = () => {
    const query = (searchInput?.value || '').trim().toLowerCase();
    cards.forEach(card => {
      const category = card.getAttribute('data-category');
      const title = (card.querySelector('.card__title')?.textContent || '').toLowerCase();
      const matchesCategory = activeFilter === 'all' || category === activeFilter;
      const matchesQuery = !query || title.includes(query);
      const visible = matchesCategory && matchesQuery;
      card.classList.toggle('is-hidden', !visible);
    });
  };

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('is-active'));
      tab.classList.add('is-active');
      activeFilter = tab.getAttribute('data-filter') || 'all';
      applyFilter();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', applyFilter);
  }
})();
</script>

</body>
</html>`;

    fs.writeFileSync(path.join(DIST_DIR, 'index.html'), indexHtml);

    // 2. RSS Feed (feed.xml) - Simple version
    const rss = `<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Humanoid Media Factory</title>
  <link>${BASE_URL}</link>
  <description>AI-Synthesized Media Hub</description>
  ${posts.map(p => `
  <item>
    <title>${p.title}</title>
    <link>${BASE_URL}/${p.url}</link>
    <description>${p.description}</description>
    <pubDate>${new Date(p.date).toUTCString()}</pubDate>
  </item>`).join('')}
</channel>
</rss>`;
    fs.writeFileSync(path.join(DIST_DIR, 'feed.xml'), rss);

    // 3. Sitemap
    const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${BASE_URL}/index.html</loc></url>
  ${posts.map(p => `<url><loc>${BASE_URL}/${p.url}</loc></url>`).join('')}
</urlset>`;
    fs.writeFileSync(path.join(DIST_DIR, 'sitemap.xml'), sitemap);

    console.log('✅ Build Complete: Portal successfully synchronized with Humanoid DNA.');
}

build().catch(err => {
    console.error('Build failed:', err);
    process.exit(1);
});
