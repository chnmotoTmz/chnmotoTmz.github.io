const fs = require('fs');
const path = require('path');

const POSTS_DIR = path.join(__dirname, '../posts');
const DIST_DIR = path.join(__dirname, '../'); // Root for GitHub Pages
const BASE_URL = 'https://chnmotoTmz.github.io';

// HTML Wrapper Template for individual posts
const POST_WRAPPER = (title, content, date, description, category, rootPath) => `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title} | Humanoid Media Factory</title>
    <meta name="description" content="${description}">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="${rootPath}assets/style.css">
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
          <a href="${rootPath}index.html" style="color: var(--accent); font-weight: 700;">← PORTAL HOME</a>
        </div>
      </div>
    </div>

    <main class="wrapper">
        <article>
            <header>
                <h1>${title}</h1>
                <div class="post-meta">
                    <time>${date}</time> &nbsp;|&nbsp; <span>${category || 'Uncategorized'}</span>
                </div>
            </header>
            <div class="content">
                ${content}
            </div>
        </article>
        
        <aside class="sidebar" style="margin-top: 40px; border-top: 1px solid var(--border); padding-top: 24px;">
           <div class="sidebar-box">
             <h3 class="sidebar-title">📰 最新のニュース</h3>
             <ul class="ranking-list" style="margin-left: 0; padding-left: 0;">
                <li style="list-style: none; padding-left: 0;"><a href="${rootPath}index.html">Humanoid Media Factory トップページへ戻る</a></li>
             </ul>
           </div>
        </aside>
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
  return clean.substring(0, 120) + '...'; // Shorter excerpt for denser MSN layout
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
  const color = category === 'humanoid' ? '#d60000' : category === 'music' ? '#1c7a34' : '#4a4a46';
  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f0f2f5"/>
      <stop offset="100%" stop-color="#e2e2e2"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="675" fill="url(#g)"/>
  <rect x="24" y="24" width="1152" height="627" fill="none" stroke="${color}" stroke-opacity="0.3" stroke-width="4"/>
  <text x="60" y="380" fill="#999" font-family="sans-serif" font-size="64" font-weight="800">Media Factory</text>
  <text x="60" y="470" fill="${color}" font-family="sans-serif" font-size="42" font-weight="700">${label}</text>
</svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function renderCard(post, options = {}) {
  const isHero = Boolean(options.hero);
  const dateText = post.date || '';
  const category = categoryLabel(post.category);
  const categoryKey = normalizeCategory(post.category);
  const badgeClass = categoryBadgeClass(post.category);
  let thumb = normalizeThumbnailUrl(post.thumbnail) || placeholderSvgDataUri(post.category);

  // Fix paths so they resolve well in root index.html
  if (thumb && !thumb.startsWith('http') && !thumb.startsWith('data:')) {
    thumb = thumb; // keep relative
  }
  const placeholder = placeholderSvgDataUri(post.category);

  if (isHero) {
    return `
<article class="card card--hero" data-category="${categoryKey}">
  <a class="card__link" href="${post.url}" aria-label="${post.title}">
    <div class="card__thumb">
      <img src="${thumb}" alt="${post.title}" loading="lazy" onerror="this.src='${placeholder}'">
      <span class="card__badge ${badgeClass}">${category}</span>
    </div>
    <div class="card__body">
      <h2 class="card__title">${post.title}</h2>
      <p class="card__excerpt">${post.excerpt}</p>
      <footer class="card__meta">
        <time>${dateText}</time>
        <span class="card__ai-label">✦ Gemini Report</span>
      </footer>
    </div>
  </a>
</article>`;
  }

  // Regular Card with excerpt for dense reading
  return `
<article class="card" data-category="${categoryKey}">
  <a class="card__link" href="${post.url}" aria-label="${post.title}">
    <div class="card__thumb">
      <img src="${thumb}" alt="${post.title}" loading="lazy" onerror="this.src='${placeholder}'">
      <span class="card__badge ${badgeClass}">${category}</span>
    </div>
    <div class="card__body">
      <h2 class="card__title">${post.title}</h2>
      <p class="card__excerpt">${post.excerpt}</p>
      <footer class="card__meta">
        <time>${dateText}</time>
      </footer>
    </div>
  </a>
</article>`;
}

function normalizePostContent(html) {
  if (!html) return '';
  let clean = html;

  // 1. Unwrap POST_WRAPPER if it exists to prevent infinite nesting
  const contentMatch = clean.match(/<div class="content">([\s\S]*?)<\/div>\s*<\/article>/i);
  if (contentMatch && contentMatch[1]) {
    clean = contentMatch[1];
  } else {
    const bodyMatch = clean.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    if (bodyMatch && bodyMatch[1]) {
      clean = bodyMatch[1];
    }
  }

  // 2. Remove inner <header> and <h1> elements (generated by LLM) to avoid duplicates with our own wrapper
  clean = clean.replace(/<header[^>]*>[\s\S]*?<\/header>/gi, '');
  clean = clean.replace(/<h1[^>]*>[\s\S]*?<\/h1>/gi, '');

  // 3. Remove boilerplate tags
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
  console.log('🚀 Synchronizing Humanoid Media Factory Portal (MSN Design)...');

  if (!fs.existsSync(POSTS_DIR)) {
    console.error('Error: Posts directory not found');
    return;
  }

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

    let pathRelativeToRoot = path.relative(DIST_DIR, filePath).replace(/\\/g, '/');
    let dirRelativeToRoot = path.relative(DIST_DIR, path.dirname(filePath)).replace(/\\/g, '/');
    let rootPath = '';
    if (dirRelativeToRoot && dirRelativeToRoot !== '.') {
      const depth = dirRelativeToRoot.split('/').length;
      rootPath = '../'.repeat(depth);
    } else {
      rootPath = './';
    }

    const relativePath = path.relative(POSTS_DIR, filePath);
    const pathParts = relativePath.split(path.sep);
    const dirCategory = pathParts.length > 1 ? pathParts[0] : null;

    const post = {
      title: meta.title || 'Untitled',
      date: meta.date || new Date().toISOString().split('T')[0],
      description: meta.description || '',
      category: meta.category || dirCategory || '雑記',
      emoji: meta.emoji || '🦾',
      excerpt: getExcerpt(normalizedContent),
      thumbnail: getThumbnailFromContent(normalizedContent),
      slug: slug,
      url: pathRelativeToRoot  // "posts/category/file.html"
    };

    // Output full page using wrapper
    const fullContent = POST_WRAPPER(post.title, normalizedContent, post.date, post.description, post.category, rootPath);
    fs.writeFileSync(filePath, fullContent); // Overwrite post with correct template

    posts.push(post);
    // console.log(`- Refined ${slug}`);
  });

  // Sort descending by date
  posts.sort((a, b) => new Date(b.date) - new Date(a.date));

  // Data for templates
  const featured = posts[0] || null;
  const heroSide1 = posts[1] || null;
  const heroSide2 = posts[2] || null;
  // Main feed posts
  const gridPosts = posts.slice(3);

  // Top 5 posts for ranking sidebar (fake ranking logic: just the newest or most clicked)
  const rankingPosts = posts.slice(2, 7);

  // Ticker text
  const tickerText = posts.slice(0, 5).map(p => p.title).join('  &nbsp;|&nbsp;  ');

  const categories = [...new Set(posts.map(p => p.category))];

  const indexHtml = `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Humanoid Media Factory - MSN Style News</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>

<div class="ticker-strip" role="status" aria-live="polite">
  <div class="ticker-strip__inner">
    <span class="ticker-strip__live">BREAKING NEWS</span>
    <div class="ticker-strip__track">
      <div class="ticker-strip__content">${tickerText} &nbsp;|&nbsp; ${tickerText}</div>
    </div>
  </div>
</div>

<header class="site-header">
  <div class="site-header__inner">
    <a class="brand" href="index.html">Humanoid <span>Media</span> Factory</a>
    <nav class="header-nav" aria-label="カテゴリー">
      <button class="tab is-active" data-filter="all">トップ</button>
      <button class="tab" data-filter="humanoid">ロボット・AI</button>
      <button class="tab" data-filter="music">音楽</button>
      <button class="tab" data-filter="zatsuki">社会・コラム</button>
    </nav>
    <div class="header-tools">
      <input class="search" id="searchInput" type="search" placeholder="ニュースを検索..." aria-label="記事を検索">
    </div>
  </div>
</header>

<main class="portal">
  <div class="portal-layout">
    <div class="portal-main">
      
      <section class="hero-grid">
        ${featured ? renderCard(featured, { hero: true }) : ''}
        <div class="hero-side">
          <h3 class="hero-side-title">🔥 注目のニュース</h3>
          ${heroSide1 ? renderCard(heroSide1) : ''}
          ${heroSide2 ? renderCard(heroSide2) : ''}
        </div>
      </section>

      <div class="section-header">
        <h2 class="section-label">最新記事・コラム</h2>
        <a href="#" class="section-link">もっと見る ›</a>
      </div>

      <section class="cards-grid" id="cardsGrid">
        ${gridPosts.map(p => renderCard(p)).join('')}
      </section>
      
    </div>
    
    <aside class="sidebar">
      <div class="sidebar-box">
        <h3 class="sidebar-title">📈 人気のニュース</h3>
        <ul class="ranking-list">
          ${rankingPosts.map(p => `<li><a href="${p.url}">${p.title}</a></li>`).join('')}
        </ul>
      </div>
      
      <div class="sidebar-box">
        <h3 class="sidebar-title">🤖 編集部のPick up</h3>
        <ul class="ranking-list" style="counter-reset:none;">
          ${posts.slice(5, 8).map(p => `<li style="padding-left:0;"><a href="${p.url}">${p.title}</a></li>`).join('')}
        </ul>
      </div>
      
      <div class="sidebar-ad">
        ADVERTISEMENT
      </div>
    </aside>
  </div>
</main>

<footer>
  <div class="footer-inner">
    <div>
      <div class="footer-title">Humanoid <span>Media</span> Factory 🦾</div>
      <p class="footer-desc">AIとロボットが紡ぐ、次世代ニュースポータル。<br>最新のテクノロジー、社会情勢、知見を休むことなく配信中。</p>
    </div>
    <div>
      <div class="footer-col-title">カテゴリー</div>
      <ul class="footer-links">
        <li><a href="#">トップニュース</a></li>
        <li><a href="#">テクノロジー・AI</a></li>
        <li><a href="#">政治・社会</a></li>
        <li><a href="#">経済・ビジネス</a></li>
        <li><a href="#">エンタメ・音楽</a></li>
      </ul>
    </div>
    <div>
      <div class="footer-col-title">サービス</div>
      <ul class="footer-links">
        <li>📝 運営方針</li>
        <li>🐙 開発者向けAPI</li>
        <li>📱 公式アプリ(未定)</li>
        <li>🔗 RSSフィード</li>
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

  // 2. RSS Feed (feed.xml)
  const rss = `<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Humanoid Media Factory</title>
  <link>${BASE_URL}</link>
  <description>AI-Synthesized News Portal</description>
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

  console.log('✅ Build Complete: MSN Portal structure successfully generated.');
}

build().catch(err => {
  console.error('Build failed:', err);
  process.exit(1);
});
