const fs = require('fs');
const path = require('path');

const POSTS_DIR = path.join(__dirname, '../posts');
const DIST_DIR = path.join(__dirname, '../'); // Root for GitHub Pages
const BASE_URL = 'https://chnmotoTmz.github.io'; // Change if needed

// HTML Wrapper Template (MSN Header Style)
const POST_WRAPPER = (title, content, date, description, tags) => `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title} | Humanoid Media Factory</title>
    <meta name="description" content="${description}">
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header class="site-header">
        <div class="header-top">
            <a class="brand" href="index.html">Humanoid <span>Media</span> Factory</a>
            <div class="header-search-container">
                <div class="search-input-wrapper">
                    <input class="search" type="search" placeholder="Search the web" aria-label="Search">
                </div>
            </div>
            <div class="header-auth">
                <button class="tab" style="background:#0078d4; color:#fff; border-radius:4px; padding:5px 15px;">Personalize</button>
            </div>
        </div>
        <nav class="header-nav">
            <a href="index.html" class="tab is-active">トップ</a>
            <a href="#" class="tab">ロボット・AI</a>
            <a href="#" class="tab">テクノロジー</a>
            <a href="#" class="tab">社会・コラム</a>
            <a href="about.html" class="tab">About</a>
        </nav>
    </header>
    <main class="premium-article">
        <div class="devlog-meta" style="color:#616161; margin-bottom:10px;">
            <time>${date}</time>
            <span style="margin:0 10px;">|</span>
            ${(tags || []).map(t => `<span class="card__cat" style="display:inline; margin-right:5px;">${t}</span>`).join('')}
        </div>
        <div class="content">
            ${content}
        </div>
    </main>
    <footer>
        <p>&copy; ${new Date().getFullYear()} Humanoid Media Factory. All rights reserved.</p>
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
      if (entry.name.toLowerCase() === 'index.html') continue;
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
  console.log('🚀 Building MSN-Style Media Factory...');

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
      articleType: meta.article_type || 'OBSERVATION',
      seriesName: meta.series_name || '',
      tags: meta.tags ? meta.tags.split(',').map(t => t.trim()) : [],
      slug: slug,
      url: isTopLevelPost ? `${slug}.html` : `posts/${relativePath}`
    };

    if (isTopLevelPost) {
      const fullContent = POST_WRAPPER(post.title, rawContent, post.date, post.description, post.tags);
      fs.writeFileSync(path.join(DIST_DIR, `${slug}.html`), fullContent);
    }

    posts.push(post);
  });

  posts.sort((a, b) => new Date(b.date) - new Date(a.date));

  // Category classification
  const getCategory = (p) => {
    const url = p.url || '';
    if (url.includes('/humanoid/')) return 'humanoid';
    if (url.includes('/music/')) return 'music';
    if (url.includes('/tech/')) return 'tech';
    if (url.includes('/devlog/')) return 'devlog';
    return 'zatsuki';
  };

  // Content Partitioning to avoid duplication
  let remainingPosts = [...posts];

  const featured = remainingPosts.shift();
  const heroSide = remainingPosts.splice(0, 2);
  const heroUrls = [featured, ...heroSide].filter(Boolean).map(p => p.url);

  const observationGrid = remainingPosts.filter(p => p.articleType === 'OBSERVATION').slice(0, 6);
  const usedInObservation = observationGrid.map(p => p.url);
  remainingPosts = remainingPosts.filter(p => !usedInObservation.includes(p.url));

  const techGrid = remainingPosts.filter(p => ['EXPERIMENT', 'HOWTO'].includes(p.articleType)).slice(0, 6);
  const usedInTech = techGrid.map(p => p.url);
  remainingPosts = remainingPosts.filter(p => !usedInTech.includes(p.url));

  const essayGrid = remainingPosts.filter(p => p.articleType === 'ESSAY').slice(0, 4);

  const rankingPosts = posts.slice(0, 5);

  function renderCard(p, opts = {}) {
    const isHero = opts.hero || false;
    const category = getCategory(p);
    const label = p.articleType || 'OBSERVATION';
    const excerpt = p.description || p.title;
    const imgUrl = `https://picsum.photos/seed/${p.slug}/800/450`; // Placeholder for now

    if (isHero) {
      return `
      <article class="card card--hero" style="background-image: url('${imgUrl}')">
        <div class="card__body">
          <span class="card__cat" style="color:#00f2ff; text-shadow: 0 0 10px rgba(0,0,0,0.5);">${label}</span>
          <h2 class="card__title"><a href="${p.url}">${p.title}</a></h2>
          <p class="card__excerpt" style="color:#eee;">${excerpt}</p>
          <time class="card__date" style="color:#ccc;">${p.date}</time>
        </div>
      </article>`;
    }

    return `
    <article class="card" data-category="${category}">
      <img src="${imgUrl}" alt="" class="card__image" loading="lazy">
      <div class="card__body">
        <span class="card__cat">${label}</span>
        <h3 class="card__title"><a href="${p.url}">${p.title}</a></h3>
        <p class="card__excerpt">${excerpt}</p>
        <time class="card__date">${p.date}</time>
      </div>
    </article>`;
  }

  const indexHtml = `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Humanoid Media Factory | MSN-Style Portal</title>
    <meta name="description" content="AI × Digital Transformation for Humanoid Lifestyle">
    <link rel="stylesheet" href="assets/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🤖</text></svg>">
</head>
<body>
    <header class="site-header">
        <div class="header-top">
            <a class="brand" href="index.html">Humanoid <span>Media</span> Factory</a>
            <div class="header-search-container">
                <div class="search-input-wrapper">
                    <input class="search" id="searchInput" type="search" placeholder="Search the web" aria-label="Search">
                </div>
            </div>
            <div class="header-auth" style="display:flex; gap:15px; align-items:center;">
                <span style="font-size:0.85rem; color:#616161;">Tokyo, 12°C ☀️</span>
                <button class="tab" style="background:#0078d4; color:#fff; border-radius:4px; padding:5px 15px; border:none; cursor:pointer; font-weight:600;">Personalize</button>
            </div>
        </div>
        <nav class="header-nav">
            <button class="tab is-active" data-filter="all">トップ</button>
            <button class="tab" data-filter="humanoid">ロボット・AI</button>
            <button class="tab" data-filter="tech">テクノロジー</button>
            <button class="tab" data-filter="zatsuki">社会・コラム</button>
            <a href="about.html" class="tab">About</a>
        </nav>
    </header>

    <main class="portal">
        <div class="portal-layout">
            <div class="portal-main">
                <!-- Hero Section -->
                <section class="hero-grid">
                    ${featured ? renderCard(featured, { hero: true }) : ''}
                    <div class="hero-side" style="display:flex; flex-direction:column; gap:16px;">
                        <div class="sidebar-box" style="margin:0; padding:15px;">
                            <h3 style="margin:0 0 10px 0; font-size:1rem; border:none; color:#d13438;">🔥 Trending Now</h3>
                            ${heroSide.map(p => `
                                <div style="margin-bottom:15px; border-bottom:1px solid #f3f5f7; padding-bottom:10px;">
                                    <h4 style="margin:0; font-size:0.95rem;"><a href="${p.url}" style="text-decoration:none; color:#1b1b1b;">${p.title}</a></h4>
                                    <time style="font-size:0.75rem; color:#616161;">${p.date}</time>
                                </div>
                            `).join('')}
                        </div>
                        <div style="background:#0078d4; color:#fff; padding:20px; border-radius:8px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
                            <span style="font-size:2rem; margin-bottom:10px;">📬</span>
                            <h4 style="margin:0 0 5px 0;">Newsletter</h4>
                            <p style="font-size:0.8rem; margin:0 0 10px 0;">Get the latest AI news</p>
                            <button style="background:#fff; color:#0078d4; border:none; padding:5px 15px; border-radius:4px; font-weight:700; cursor:pointer;">Subscribe</button>
                        </div>
                    </div>
                </section>

                <!-- Observation Section -->
                <div class="section-header">
                    <h2 class="section-label">Latest Observations</h2>
                </div>
                <section class="cards-grid">
                    ${observationGrid.map(p => renderCard(p)).join('')}
                </section>

                <!-- Tech Section -->
                <div class="section-header">
                    <h2 class="section-label">Experiments & Development</h2>
                </div>
                <section class="cards-grid">
                    ${techGrid.map(p => renderCard(p)).join('')}
                </section>
            </div>

            <aside class="sidebar">
                <div class="sidebar-box">
                    <h3 class="sidebar-title">チャートで見るトレンド</h3>
                    <ul class="ranking-list">
                        ${rankingPosts.map((p, i) => `
                            <li>
                                <span style="font-size:1.5rem; font-weight:900; color:#e1dfdd; margin-right:10px;">${i + 1}</span>
                                <a href="${p.url}">${p.title}</a>
                            </li>
                        `).join('')}
                    </ul>
                </div>

                <div class="sidebar-box" style="background: linear-gradient(135deg, #0078d4 0%, #00bcf2 100%); color:#fff; border:none;">
                    <h3 class="sidebar-title" style="color:#fff; border-color:rgba(255,255,255,0.3);">Featured Project</h3>
                    <p style="font-size:0.9rem; opacity:0.9;">pTIMER: The ultimate tool for personal productivity and DX logging.</p>
                    <a href="#" style="color:#fff; font-weight:700; text-decoration:none;">Learn more →</a>
                </div>
            </aside>
        </div>
    </main>

    <footer>
        <div style="margin-bottom:20px;">
            <a href="index.html" class="brand" style="justify-content:center;">Humanoid <span>Media</span> Factory</a>
        </div>
        <div style="display:flex; justify-content:center; gap:20px; margin-bottom:20px;">
            <a href="#" class="tab">Privacy</a>
            <a href="#" class="tab">Terms of Use</a>
            <a href="about.html" class="tab">About Us</a>
            <a href="partnership.html" class="tab">Contact</a>
        </div>
        <p>&copy; 2026 Humanoid Media Factory. All rights reserved.</p>
    </footer>

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
  console.log('✅ Build Complete: MSN-Style Portal generated.');
}

build().catch(err => {
  console.error('Build failed:', err);
  process.exit(1);
});
