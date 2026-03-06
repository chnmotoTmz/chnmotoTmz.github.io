const fs = require('fs');
const path = require('path');

const POSTS_DIR = path.join(__dirname, '../posts');
const DIST_DIR = path.join(__dirname, '../'); // Root for GitHub Pages
const BASE_URL = 'https://chnmotoTmz.github.io'; // Change if needed

// HTML Wrapper Template
const POST_WRAPPER = (title, content, date, description, tags) => `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title} | chnmotoTmz Blog</title>
    <meta name="description" content="${description}">
    <meta property="og:title" content="${title}">
    <meta property="og:description" content="${description}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="${BASE_URL}/${path.basename(title)}.html">
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header>
        <h1><a href="index.html">chnmotoTmz Media Factory</a></h1>
    </header>
    <main>
        ${content}
    </main>
    <footer>
        <p>&copy; ${new Date().getFullYear()} chnmotoTmz</p>
    </footer>
</body>
</html>
`;

function extractMetadata(content) {
  const meta = {};
  const match = content.match(/<!--([\s\S]*?)-->/);
  if (match) {
    const lines = match[1].strip ? match[1].strip().split('\n') : match[1].trim().split('\n');
    lines.forEach(line => {
      const part = line.split(':');
      if (part.length >= 2) {
        meta[part[0].trim()] = part.slice(1).join(':').trim();
      }
    });
  }
  return meta;
}

function collectHtmlFiles(dir) {
  let results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results = results.concat(collectHtmlFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      // Skip index files under posts/* to avoid listing category index pages as articles.
      if (entry.name.toLowerCase() === 'index.html') {
        continue;
      }
      results.push(fullPath);
    }
  }
  return results;
}

function extractTitleFromHtml(content) {
  const h1 = content.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
  if (h1 && h1[1]) return h1[1].replace(/<[^>]+>/g, '').trim();

  const title = content.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  if (title && title[1]) return title[1].replace(/<[^>]+>/g, '').trim();

  return '';
}

function extractDescriptionFromHtml(content) {
  const p = content.match(/<p[^>]*>([\s\S]*?)<\/p>/i);
  if (!p || !p[1]) return '';
  return p[1].replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
}

async function build() {
  console.log('🚀 Building Industrial Media Factory...');

  if (!fs.existsSync(POSTS_DIR)) {
    console.error('Error: Posts directory not found');
    return;
  }

  const files = collectHtmlFiles(POSTS_DIR);
  const posts = [];

  files.forEach(filePath => {
    const rawContent = fs.readFileSync(filePath, 'utf8');
    const meta = extractMetadata(rawContent);
    const relativePath = path.relative(POSTS_DIR, filePath).replace(/\\/g, '/');
    const filename = path.basename(filePath);
    const slug = path.basename(filename, '.html');
    const isTopLevelPost = !relativePath.includes('/');
    const dateFromFilename = (filename.match(/^(\d{4}-\d{2}-\d{2})/) || [])[1];

    const post = {
      title: meta.title || extractTitleFromHtml(rawContent) || slug,
      date: meta.date || dateFromFilename || new Date().toISOString().split('T')[0],
      description: meta.description || extractDescriptionFromHtml(rawContent) || '',
      tags: meta.tags ? meta.tags.split(',').map(t => t.trim()) : [],
      slug: slug,
      // Keep backward compatibility for top-level posts,
      // and link nested posts directly under /posts/... (e.g. posts/devlog/...)
      url: isTopLevelPost ? `${slug}.html` : `posts/${relativePath}`
    };

    if (isTopLevelPost) {
      // Wrap only top-level partial HTML into a full page in root.
      const fullContent = POST_WRAPPER(post.title, rawContent, post.date, post.description, post.tags);
      fs.writeFileSync(path.join(DIST_DIR, `${slug}.html`), fullContent);
      console.log(`- Synthesized ${slug}.html`);
    } else {
      console.log(`- Indexed nested post ${relativePath}`);
    }

    posts.push(post);
  });

  // Sort descending
  posts.sort((a, b) => new Date(b.date) - new Date(a.date));

  // 1. index.html
  const featured = posts[0];
  const heroSide1 = posts[1];
  const heroSide2 = posts[2];
  const gridPosts = posts.slice(3, 11);
  const rankingPosts = posts.slice(0, 5);

  function renderCard(p, opts = {}) {
    const hero = opts.hero || false;
    const excerpt = p.description || p.title;
    const getCategory = (p) => {
      const url = p.url || '';
      if (url.includes('/humanoid/')) return 'humanoid';
      if (url.includes('/music/')) return 'music';
      if (url.includes('/tech/')) return 'tech';
      if (url.includes('/rakuten/')) return 'rakuten';
      if (url.includes('/art/')) return 'art';
      if (url.includes('/devlog/')) return 'devlog';
      const tags = (p.tags || []).join(' ').toLowerCase();
      if (tags.includes('humanoid') || tags.includes('robot')) return 'humanoid';
      if (tags.includes('music')) return 'music';
      return 'zatsuki';
    };
    const category = getCategory(p);
    const categoryLabels = { humanoid: 'ロボット・AI', music: '音楽', zatsuki: '社会・コラム', tech: 'テクノロジー', rakuten: '楽天', art: 'アート', devlog: '開発' };
    const label = categoryLabels[category] || 'コラム';
    if (hero) {
      return `<article class="card card--hero" data-category="${category}">
              <div class="card__body">
                <span class="card__cat">${label}</span>
                <h2 class="card__title"><a href="${p.url}">${p.title}</a></h2>
                <p class="card__excerpt">${excerpt}</p>
                <time class="card__date">${p.date}</time>
              </div>
            </article>`;
    }
    return `<article class="card" data-category="${category}">
          <div class="card__body">
            <span class="card__cat">${label}</span>
            <h3 class="card__title"><a href="${p.url}">${p.title}</a></h3>
            <time class="card__date">${p.date}</time>
          </div>
        </article>`;
  }

  const indexHtml = `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Humanoid Media Factory | AI自動生成ニュースポータル</title>
    <meta name="description" content="AI × ロボット × 社会の最前線を配信する自動生成ニュースメディア">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header class="site-header">
  <div class="site-header__inner">
    <a class="brand" href="index.html">Humanoid <span>Media</span> Factory</a>
    <nav class="header-nav" aria-label="カテゴリー">
      <button class="tab is-active" data-filter="all">トップ</button>
      <button class="tab" data-filter="humanoid">ロボット・AI</button>
      <button class="tab" data-filter="music">音楽</button>
      <button class="tab" data-filter="zatsuki">社会・コラム</button>
      <a href="about.html" class="tab" style="text-decoration:none;">About</a>
      <a href="partnership.html" class="tab" style="text-decoration:none; background: linear-gradient(135deg, #1a1a2e, #2d2d5e); color:#a0a0ff;">連絡先</a>
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

<footer class="site-footer">
  <div class="site-footer__inner">
    <div class="newsletter-signup">
      <h3>📬 メールマガジン登録</h3>
      <p>ヒューマノイド・AI・開発の最新情報をお届けします</p>
      <form id="newsletter-form" style="display:flex; gap:0.5rem; flex-wrap:wrap; justify-content:center; margin-top:1rem;">
        <input type="email" id="newsletter-email" placeholder="メールアドレスを入力..."
          style="padding:0.6rem 1rem; border:1px solid #4a4a8e; background:#1a1a2e; color:#e0e0e0; border-radius:4px; min-width:260px;" required>
        <button type="submit"
          style="padding:0.6rem 1.2rem; background:linear-gradient(135deg,#2d2d5e,#1a1a2e); color:#a0a0ff; border:1px solid #4a4a8e; border-radius:4px; cursor:pointer; font-weight:600;">
          登録する
        </button>
      </form>
      <div id="newsletter-msg" style="margin-top:0.75rem; font-size:0.9rem; min-height:1.2em;"></div>
    </div>
    <div class="footer-links" style="margin-top:1.5rem; font-size:0.85rem; color:#888;">
      <a href="about.html" style="color:#a0a0ff; margin-right:1rem;">About</a>
      <a href="partnership.html" style="color:#a0a0ff; margin-right:1rem;">連絡先</a>
      <span>© 2026 chnmoto / Humanoid Media Factory</span>
    </div>
  </div>
</footer>
<style>
.site-footer { background:#0d0d1a; border-top:1px solid #2d2d5e; padding:2.5rem 1rem; text-align:center; margin-top:3rem; }
.site-footer__inner { max-width:800px; margin:0 auto; }
.newsletter-signup h3 { color:#e0e0e0; margin-bottom:0.5rem; }
.newsletter-signup p { color:#888; }
</style>
<script>
document.getElementById('newsletter-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('newsletter-email').value.trim();
  const msgEl = document.getElementById('newsletter-msg');
  const btn   = e.submitter;
  const API = window.location.hostname === 'localhost'
    ? 'http://localhost:8084/api/subscribe'
    : 'https://new-blog-system.onrender.com/api/subscribe';

  btn.disabled = true;
  msgEl.style.color = '#a0a0ff';
  msgEl.textContent = '送信中...';

  async function tryFetch() {
    const ctrl = new AbortController();
    const tid  = setTimeout(() => ctrl.abort(), 35000); // 35s for Render cold-start
    try {
      const res = await fetch(API, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({email}),
        signal: ctrl.signal
      });
      clearTimeout(tid);
      return res;
    } catch(err) {
      clearTimeout(tid);
      throw err;
    }
  }

  try {
    let res;
    try {
      res = await tryFetch();
    } catch (firstErr) {
      // Cold-start or network hiccup — show message and retry once
      msgEl.textContent = 'サーバー起動中... もう少しお待ちください（初回は30秒ほどかかります）';
      await new Promise(r => setTimeout(r, 3000));
      res = await tryFetch(); // 2nd attempt
    }
    const data = await res.json();
    msgEl.style.color = data.success ? '#6fcf6f' : '#cf6f6f';
    msgEl.textContent = data.message || (data.success ? '登録しました！' : 'エラーが発生しました');
  } catch (err) {
    msgEl.style.color = '#cf6f6f';
    msgEl.textContent = 'サーバーに接続できませんでした。時間をおいて再度お試しください。';
  } finally {
    btn.disabled = false;
  }
});
</script>

<script>
(() => {
  const tabs = document.querySelectorAll('.tab[data-filter]');
  const cards = document.querySelectorAll('.card[data-category]');
  const searchInput = document.getElementById('searchInput');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('is-active'));
      tab.classList.add('is-active');
      const filter = tab.dataset.filter;
      cards.forEach(card => {
        const show = filter === 'all' || card.dataset.category === filter;
        card.style.display = show ? '' : 'none';
      });
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.toLowerCase();
      cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(q) ? '' : 'none';
      });
    });
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
  <title>chnmotoTmz Media Factory</title>
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

  // 3. Sitemap (sitemap.xml)
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${BASE_URL}/index.html</loc></url>
  ${posts.map(p => `<url><loc>${BASE_URL}/${p.url}</loc></url>`).join('')}
</urlset>`;
  fs.writeFileSync(path.join(DIST_DIR, 'sitemap.xml'), sitemap);

  console.log('✅ Build Complete: Index, RSS, and Sitemap generated.');
}

build().catch(err => {
  console.error('Build failed:', err);
  process.exit(1);
});
