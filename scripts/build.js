const fs = require('fs');
const path = require('path');

const POSTS_DIR = path.join(__dirname, '../posts');
const DIST_DIR = path.join(__dirname, '../');
const BASE_URL = 'https://chnmotoTmz.github.io';

const HEADER = (rootPath, activeFilter = 'all') => `
<header class="site-header">
  <div class="header-inner">
    <div class="brand"><a href="${rootPath}index.html" style="color: inherit; text-decoration: none;">Humanoid <span>Media</span> Factory</a></div>
    <nav class="nav-main">
      <button class="tab ${activeFilter === 'all' ? 'is-active' : ''}" data-filter="all">トップ</button>
      <button class="tab ${activeFilter === 'humanoid' ? 'is-active' : ''}" data-filter="humanoid">ロボット・AI</button>
      <button class="tab ${activeFilter === 'music' ? 'is-active' : ''}" data-filter="music">音楽</button>
      <button class="tab ${activeFilter === 'zatsuki' ? 'is-active' : ''}" data-filter="zatsuki">社会・コラム</button>
    </nav>
    <div class="nav-sub">
      <a href="${rootPath}index.html">速報</a>
      <a href="${rootPath}index.html">ライブ</a>
      <a href="${rootPath}index.html">オリジナル</a>
      <a href="${rootPath}index.html">ランキング</a>
    </div>
  </div>
</header>
`;

const FOOTER = `
<footer>
  <div class="footer-inner">
    <div>
      <div class="brand" style="font-size: 20px;">Humanoid <span>Media</span> Factory 🦾</div>
      <p style="font-size: 13px; color: #666;">AIとロボットが紡ぐ、次世代ニュースポータル。</p>
    </div>
    <div>
      <h4 style="font-size: 14px; margin-bottom: 10px;">カテゴリー</h4>
      <ul style="list-style: none; padding: 0; font-size: 13px;">
        <li><a href="#">テクノロジー・AI</a></li>
        <li><a href="#">政治・社会</a></li>
        <li><a href="#">エンタメ・音楽</a></li>
      </ul>
    </div>
    <div>
      <h4 style="font-size: 14px; margin-bottom: 10px;">サービス</h4>
      <ul style="list-style: none; padding: 0; font-size: 13px;">
        <li>📝 運営方針</li>
        <li>🔗 RSSフィード</li>
      </ul>
    </div>
  </div>
  <div class="footer-bottom">
    <span>© 2026 chnmotoTmz · Humanoid Media Factory</span><br>
    <span style="font-size: 10px;">Powered by Gemini × LINE × GitHub</span>
  </div>
</footer>
`;

const SIDEBAR = (posts, rootPath) => `
<aside class="side-col">
  <div class="side-box">
    <div class="side-box-title">アクセスランキング</div>
    <ul class="side-list">
      ${posts.slice(0, 5).map((p, i) => `
      <li class="side-item">
        <span class="side-rank">${i + 1}</span>
        <a class="side-item-title" href="${rootPath}${p.url}">${p.title}</a>
      </li>`).join('')}
    </ul>
  </div>
  <div class="side-box">
    <div class="side-box-title">編集部のPick up</div>
    <ul class="side-list">
      ${posts.slice(5, 10).map(p => `
      <li class="side-item">
        <a class="side-item-title" href="${rootPath}${p.url}">${p.title}</a>
      </li>`).join('')}
    </ul>
  </div>
</aside>
`;

const LEFT_COL = `
<aside class="left-col">
  <div class="reaction-box">
    <div class="reaction-count">${Math.floor(Math.random() * 500) + 100}</div>
    <div class="reaction-label">コメント</div>
  </div>
  <div class="reaction-box">
    <div class="reaction-count">${Math.floor(Math.random() * 1000) + 200}</div>
    <div class="reaction-label">リアクション</div>
  </div>
</aside>
`;

const POST_WRAPPER = (post, rankingPosts, rootPath) => `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${post.title} | Humanoid Media Factory</title>
    <link rel="stylesheet" href="${rootPath}assets/style.css">
</head>
<body>
    ${HEADER(rootPath, normalizeCategory(post.category))}

    <main class="portal">
      <div class="portal-layout">
        ${LEFT_COL}
        <div class="main-col">
          <article class="article-page">
            <header class="article-header">
              <h1 class="article-title">${post.title}</h1>
              <div class="article-meta">
                <time>${post.date}</time> &nbsp;|&nbsp; <span>${post.category}</span>
              </div>
            </header>
            <div class="article-body">
              ${post.content}
            </div>
          </article>
        </div>
        ${SIDEBAR(rankingPosts, rootPath)}
      </div>
    </main>

    ${FOOTER}
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
  let clean = html.replace(/<[^>]*>/g, '').trim();
  clean = clean.replace(/\s+/g, ' ');
  return clean.substring(0, 100) + '...';
}

function getThumbnailFromContent(html) {
  const imgMatch = html.match(/<img[^>]+src=["']([^"']+)["']/i);
  return imgMatch ? imgMatch[1] : '';
}

function normalizeCategory(category) {
  const val = String(category || '').toLowerCase();
  if (val.includes('humanoid')) return 'humanoid';
  if (val.includes('music')) return 'music';
  return 'zatsuki';
}

function normalizePostContent(html) {
  let clean = html;
  const contentMatch = clean.match(/<div class="article-body">([\s\S]*?)<\/div>\s*<\/article>/i) ||
                       clean.match(/<div class="content">([\s\S]*?)<\/div>\s*<\/article>/i);
  if (contentMatch && contentMatch[1]) {
    clean = contentMatch[1];
  } else {
    const bodyMatch = clean.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    if (bodyMatch && bodyMatch[1]) {
      clean = bodyMatch[1];
    }
  }
  clean = clean.replace(/<header[^>]*>[\s\S]*?<\/header>/gi, '');
  clean = clean.replace(/<h1[^>]*>[\s\S]*?<\/h1>/gi, '');
  clean = clean.replace(/<!DOCTYPE[^>]*>/gi, '');
  clean = clean.replace(/<html[^>]*>/gi, '');
  clean = clean.replace(/<\/html>/gi, '');
  clean = clean.replace(/<head[\s\S]*?<\/head>/gi, '');
  clean = clean.replace(/<body[^>]*>/gi, '');
  clean = clean.replace(/<\/body>/gi, '');
  clean = clean.replace(/<link[^>]*>/gi, '');
  clean = clean.replace(/<style[\s\S]*?<\/style>/gi, '');
  return clean.trim();
}

async function build() {
  console.log('🚀 Building Yahoo! Style Portal...');

  if (!fs.existsSync(POSTS_DIR)) return;

  const getFiles = (dir) => {
    let results = [];
    fs.readdirSync(dir).forEach(file => {
      const filePath = path.join(dir, file);
      if (fs.statSync(filePath).isDirectory()) {
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
    const raw = fs.readFileSync(filePath, 'utf8');
    const meta = extractMetadata(raw);
    const content = normalizePostContent(raw);
    const fileName = path.basename(filePath);

    let pathRelativeToRoot = path.relative(DIST_DIR, filePath).replace(/\\/g, '/');
    let dirRelativeToRoot = path.relative(DIST_DIR, path.dirname(filePath)).replace(/\\/g, '/');
    let rootPath = '../'.repeat(dirRelativeToRoot.split('/').length);

    posts.push({
      title: meta.title || fileName,
      date: meta.date || '2026-01-01',
      category: meta.category || '雑記',
      content: content,
      excerpt: getExcerpt(content),
      thumbnail: getThumbnailFromContent(content),
      url: pathRelativeToRoot,
      filePath: filePath,
      rootPath: rootPath
    });
  });

  posts.sort((a, b) => new Date(b.date) - new Date(a.date));

  // Update all post files with new template
  posts.forEach(p => {
    const full = POST_WRAPPER(p, posts, p.rootPath);
    fs.writeFileSync(p.filePath, full);
  });

  // Generate index.html
  const featured = posts[0];
  const gridPosts = posts.slice(1);

  const indexHtml = `
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Humanoid Media Factory - Yahoo! Style</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
    ${HEADER('', 'all')}

    <main class="portal">
      <div class="portal-layout">
        ${LEFT_COL}
        <div class="main-col">
          <section class="hero-article">
            <a href="${featured.url}">
              <img src="${featured.thumbnail || 'https://via.placeholder.com/800x450'}" alt="${featured.title}">
              <h2 class="title">${featured.title}</h2>
            </a>
            <p class="news-meta">${featured.date} | ${featured.category}</p>
          </section>

          <ul class="news-list" id="newsList">
            ${gridPosts.map(p => `
            <li class="news-item" data-category="${normalizeCategory(p.category)}">
              <div class="news-thumb">
                <img src="${p.thumbnail || 'https://via.placeholder.com/120x80'}" alt="${p.title}">
              </div>
              <div class="news-content">
                <a href="${p.url}"><h3 class="news-title">${p.title}</h3></a>
                <p class="news-meta">${p.date} | ${p.category}</p>
              </div>
            </li>`).join('')}
          </ul>
        </div>
        ${SIDEBAR(posts, '')}
      </div>
    </main>

    ${FOOTER}

    <script>
      const tabs = document.querySelectorAll('.tab');
      const items = document.querySelectorAll('.news-item');
      tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          tabs.forEach(t => t.classList.remove('is-active'));
          tab.classList.add('is-active');
          const filter = tab.dataset.filter;
          items.forEach(item => {
            if (filter === 'all' || item.dataset.category === filter) {
              item.style.display = 'flex';
            } else {
              item.style.display = 'none';
            }
          });
        });
      });
    </script>
</body>
</html>
`;

  fs.writeFileSync(path.join(DIST_DIR, 'index.html'), indexHtml);
  console.log('✅ Build Successful');
}

build();
