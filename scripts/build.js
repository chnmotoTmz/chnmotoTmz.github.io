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
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Zen+Antique&family=Noto+Sans+JP:wght@300;400;500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
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
    const featured = posts[0] || {};
    const sideArticles = posts.slice(1, 5);
    const gridArticles = posts.slice(5, 8);
    const tickerText = posts.slice(0, 5).map(p => `${p.emoji} ${p.title}`).join(' \u00a0 ');

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
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Zen+Antique&family=Noto+Sans+JP:wght@300;400;500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <div class="topbar-inner">
    <div class="topbar-left">
      <span>Vol.08 No.247</span>
      <span>2026年3月2日（月）</span>
      <span>AIとロボットが紡ぐ、次世代コンテンツパイプライン</span>
    </div>
    <div class="topbar-right">
      <span class="live-badge"><span class="live-dot"></span>LIVE GENERATE</span>
      <span>記事${posts.length}本公開中</span>
    </div>
  </div>
</div>

<!-- MASTHEAD -->
<div class="masthead">
  <div class="masthead-inner">
    <div class="masthead-left">
      <div class="issue-info">// Automated Content Pipeline</div>
      <div class="issue-info">LINE → Moondream → Gemini → Publish</div>
    </div>
    <div class="mascot-area">
      <span class="mascot-emoji">🦾</span>
      <h1 class="site-title">Humanoid<br><span class="robot">Media</span> Factory</h1>
      <p class="site-tagline">// AIとロボットが紡ぐ、次世代コンテンツパイプライン</p>
    </div>
    <div class="masthead-right">
      <div class="stats-mini">
        <div class="stat-row"><strong>${posts.length}</strong>本 公開済</div>
        <div class="stat-row"><strong>98%</strong> 生成成功率</div>
        <div class="stat-row"><strong>2</strong>媒体 同時配信</div>
      </div>
    </div>
  </div>
</div>

<!-- NAV -->
<nav>
  <div class="nav-inner">
    <a href="#" class="nav-link active">すべて</a>
    ${categories.map(c => `<a href="#" class="nav-link">${c}</a>`).join('')}
    <div class="nav-search">
      <input type="text" placeholder="記事を検索...">
    </div>
  </div>
</nav>

<!-- TICKER -->
<div class="ticker-wrap">
  <div class="ticker-inner">
    <div class="ticker-label">NEW</div>
    <div class="ticker-text">${tickerText}</div>
  </div>
</div>

<!-- MAIN CONTENT -->
<div class="wrapper">

  <!-- FEATURED -->
  <div class="featured-label"><span>✦ 注目記事 ✦</span></div>
  <div class="featured-grid">
    <div class="featured-main">
      <span class="featured-kicker">${featured.kicker || '特集'}</span>
      <h2 class="featured-title" onclick="location.href='${featured.url}'">${featured.title}</h2>
      <p class="featured-body">${featured.excerpt}</p>
      <div class="featured-meta">
        <span>📅 ${featured.date}</span>
        <span>✨ Gemini生成</span>
        <span style="margin-left:auto; color:var(--accent); font-weight:600; cursor:pointer;" onclick="location.href='${featured.url}'">続きを読む →</span>
      </div>
    </div>
    <div class="featured-side">
      <div class="side-title">最新の投稿</div>
      ${sideArticles.map((p, i) => `
      <div class="side-article" onclick="location.href='${p.url}'">
        <div class="side-num">0${i + 1}</div>
        <div class="side-article-title">${p.title}</div>
        <div class="side-article-meta">${p.date} · ${p.category}</div>
      </div>
      `).join('')}
    </div>
  </div>

  <!-- LATEST 3-COLUMN -->
  <div class="section-header">
    <h2>最新記事</h2>
    <div class="section-rule"></div>
    <a href="#" class="section-more">すべて見る →</a>
  </div>

  <div class="grid-3">
    ${gridArticles.map(p => `
    <div class="card" onclick="location.href='${p.url}'">
      <div class="card-thumb">${p.emoji}<span class="card-thumb-label">${p.category}</span></div>
      <div class="card-body">
        <span class="card-cat">${p.category}</span>
        <div class="card-title">${p.title}</div>
        <p class="card-excerpt">${p.excerpt}</p>
      </div>
      <div class="card-footer"><span>${p.date}</span><span class="card-read-more">読む →</span></div>
    </div>
    `).join('')}
  </div>

  <!-- CONTENT + SIDEBAR -->
  <div class="content-with-sidebar">
    <div>
      <div class="section-header">
        <h2>以前の投稿</h2>
        <div class="section-rule"></div>
        <a href="#" class="section-more">もっと見る →</a>
      </div>
      <div class="grid-3" style="grid-template-columns: repeat(2,1fr);">
        ${posts.slice(8, 12).map(p => `
        <div class="card" onclick="location.href='${p.url}'">
          <div class="card-thumb">${p.emoji}<span class="card-thumb-label">${p.category}</span></div>
          <div class="card-body">
            <span class="card-cat">${p.category}</span>
            <div class="card-title">${p.title}</div>
            <p class="card-excerpt">${p.excerpt}</p>
          </div>
          <div class="card-footer"><span>${p.date}</span><span class="card-read-more">読む →</span></div>
        </div>
        `).join('')}
      </div>
    </div>

    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="widget">
        <div class="widget-title">カテゴリー</div>
        <div class="widget-body">
          <ul class="cat-list">
            ${catCounts.map(c => `
            <li class="cat-item"><span>${c.name}</span><span class="cat-count">${c.count}</span></li>
            `).join('')}
          </ul>
        </div>
      </div>

      <div class="widget">
        <div class="widget-title">パイプライン状態</div>
        <div class="widget-body">
          <div class="pipeline-mini">
            <div class="pipe-step"><span class="pipe-icon">📱</span><div><div class="pipe-name">LINE Webhook</div><div class="pipe-tech">接続中</div></div><span class="pipe-ok">● OK</span></div>
            <div class="pipe-step"><span class="pipe-icon">🌙</span><div><div class="pipe-name">Moondream</div><div class="pipe-tech">画像解析</div></div><span class="pipe-ok">● OK</span></div>
            <div class="pipe-step"><span class="pipe-icon">🖼️</span><div><div class="pipe-name">Catbox CDN</div><div class="pipe-tech">ホスティング</div></div><span class="pipe-ok">● OK</span></div>
            <div class="pipe-step"><span class="pipe-icon">✨</span><div><div class="pipe-name">Gemini AI</div><div class="pipe-tech">文章生成</div></div><span class="pipe-ok">● OK</span></div>
            <div class="pipe-step"><span class="pipe-icon">📝</span><div><div class="pipe-name">はてなBlog</div><div class="pipe-tech">公開中</div></div><span class="pipe-ok">● OK</span></div>
            <div class="pipe-step"><span class="pipe-icon">🐙</span><div><div class="pipe-name">GitHub Pages</div><div class="pipe-tech">デプロイ済</div></div><span class="pipe-ok">● OK</span></div>
          </div>
        </div>
      </div>

      <div class="widget">
        <div class="widget-title">最近の投稿</div>
        <div class="widget-body">
          <div class="recent-list">
            ${posts.slice(0, 5).map((p, i) => `
            <div class="recent-item" onclick="location.href='${p.url}'">
              <div class="recent-num">${String(i + 1).padStart(2, '0')}</div>
              <div>
                <div class="recent-title">${p.title}</div>
                <div class="recent-date">${p.date}</div>
              </div>
            </div>
            `).join('')}
          </div>
        </div>
      </div>
    </aside>
  </div>
</div>

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
