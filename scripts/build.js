const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.join(__dirname, '..');
const POSTS_DIR = path.join(ROOT_DIR, 'posts');
const DIST_DIR = ROOT_DIR;
const BASE_URL = 'https://chnmototmz.github.io/';

// Utility: Correct relative path based on file depth
function getRelativePrefix(filePath) {
    const rel = path.relative(DIST_DIR, filePath);
    const depth = rel.split(path.sep).length - 1;
    return depth > 0 ? '../'.repeat(depth) : './';
}

// Components
const HEADER = (prefix) => `
<site-header prefix="${prefix}"></site-header>
`;

const FOOTER = (prefix) => `
<footer class="site-footer" style="background:#0d0d1a; border-top:1px solid #2d2d5e; padding:2.5rem 1rem; text-align:center; margin-top:3rem;">
  <div class="site-footer__inner" style="max-width:800px; margin:0 auto;">
    <div class="newsletter-signup">
      <h3 style="color:#e0e0e0; margin-bottom:0.5rem;">📬 メールマガジン登録</h3>
      <p style="color:#888;">ヒューマノイド・AI・開発の最新情報をお届けします</p>
      <form id="newsletter-form" style="display:flex; gap:0.5rem; flex-wrap:wrap; justify-content:center; margin-top:1rem;">
        <input type="email" id="newsletter-email" placeholder="メールアドレスを入力..." style="padding:0.6rem 1rem; border:1px solid #4a4a8e; background:#1a1a2e; color:#e0e0e0; border-radius:4px; min-width:260px;" required>
        <button type="submit" id="newsletter-btn" style="padding:0.6rem 1.2rem; background:linear-gradient(135deg,#2d2d5e,#1a1a2e); color:#a0a0ff; border:1px solid #4a4a8e; border-radius:4px; cursor:pointer; font-weight:600;">登録する</button>
      </form>
      <div id="newsletter-msg" style="margin-top:0.75rem; font-size:0.9rem; min-height:1.2em;"></div>
    </div>
    <div class="footer-links" style="display:flex; justify-content:center; gap:20px; margin-top:1.5rem; font-size:0.85rem; color:#888;">
        <a href="${prefix}about.html" style="color:#a0a0ff;">About Us</a>
        <a href="${prefix}partnership.html" style="color:#a0a0ff;">Contact</a>
        <span>&copy; ${new Date().getFullYear()} Humanoid Media Factory</span>
    </div>
  </div>
  <script>
  (function() {
    var SUBSCRIBE_API = 'https://eda5-2404-7a84-87c0-1800-c1f6-e390-d7bf-39f7.ngrok-free.app/api/subscribe';
    var form = document.getElementById('newsletter-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
          e.preventDefault();
          var email  = document.getElementById('newsletter-email').value.trim();
          var msgEl  = document.getElementById('newsletter-msg');
          var btn    = document.getElementById('newsletter-btn');
          btn.disabled = true;
          msgEl.style.color = '#a0a0ff';
          msgEl.textContent = '送信中...';
          try {
            var res = await fetch(SUBSCRIBE_API, {
              method: 'POST',
              headers: {'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '1'},
              body: JSON.stringify({email: email})
            });
            var data = await res.json();
            msgEl.style.color = data.success ? '#6fcf6f' : '#cf6f6f';
            msgEl.textContent = data.message || (data.success ? '登録しました！' : 'エラーが発生しました');
          } catch(err) {
            msgEl.style.color = '#cf6f6f';
            msgEl.textContent = 'サーバーに接続できませんでした: ' + err.message;
          } finally {
            btn.disabled = false;
          }
        });
    }
  })();
  </script>
</footer>
`;

const SIDEBAR = (posts, prefix) => `
<aside class="sidebar">
    <div class="sidebar-box">
        <h3 class="sidebar-title">アクセスランキング</h3>
        <ul class="ranking-list">
            ${posts.slice(0, 5).map((p, i) => `
                <li>
                    <span class="ranking-number">${i + 1}</span>
                    <a href="${prefix}${p.url}">${p.title}</a>
                </li>
            `).join('')}
        </ul>
    </div>
    <div class="sidebar-box sidebar-box--highlight">
        <h3 class="sidebar-title">注目トピック</h3>
        <div class="topic-list">
            <span class="badge topic-badge">#Humanoid</span>
            <span class="badge topic-badge">#AI_DX</span>
            <span class="badge topic-badge">#Robotics</span>
        </div>
    </div>
    <div class="sidebar-box" style="text-align: center; padding-top: 15px; border-top: 1px dashed var(--rule); margin-top: 20px;">
        <a href="https://internet.blogmura.com/generativeai/ranking/in?p_cid=11215182" target="_blank"><img src="https://b.blogmura.com/internet/generativeai/88_31.gif" width="88" height="31" border="0" alt="にほんブログ村 ネットブログ ChatGPT・生成AIへ" /></a><br /><a href="https://internet.blogmura.com/generativeai/ranking/in?p_cid=11215182" target="_blank" style="font-size: 10px; color: var(--muted); text-decoration: none;">にほんブログ村</a>
    </div>
</aside>
`;

const CATEGORY_META = {
    'humanoid': { icon: '🤖', name: 'ロボット・AI' },
    'tech': { icon: '💻', name: 'テクノロジー' },
    'devlog': { icon: '📝', name: '開発ログ' },
    'gadget': { icon: '📱', name: 'ガジェット' },
    'news': { icon: '📰', name: 'ニュース・時事' },
    'finance': { icon: '💰', name: '金融・投資' },
    'relationships': { icon: '❤️', name: '恋愛・人間関係' },
    'adult': { icon: '🔞', name: 'アダルト' },
    'art': { icon: '🎨', name: 'アート・創作' },
    'education': { icon: '📚', name: '教育・学習' },
    'english': { icon: '🔤', name: '英語学習' },
    'entertainment': { icon: '🍿', name: 'エンタメ' },
    'gourmet': { icon: '🍽️', name: 'グルメ' },
    'music': { icon: '🎵', name: '音楽' },
    'occult': { icon: '👽', name: 'オカルト' },
    'rakuten': { icon: '🛍️', name: '楽天・お得' },
    'sports': { icon: '⚽', name: 'スポーツ' },
    'travel': { icon: '✈️', name: '旅行' },
    'wellness': { icon: '🌿', name: '健康・ウェルネス' },
    'uncategorized': { icon: '📦', name: 'その他' },
    'affiliate': { icon: '💸', name: 'アフィリエイト' },
};

function getCategoryMeta(cat) {
    if (CATEGORY_META[cat]) return CATEGORY_META[cat];
    return { icon: '📁', name: cat.charAt(0).toUpperCase() + cat.slice(1) };
}

const LEFT_COL = (prefix, categories = []) => `
<div class="left-col">
    <div class="sidebar-box">
        <h3 class="sidebar-title">主要カテゴリー</h3>
        <ul class="ranking-list" style="max-height: 500px; overflow-y: auto; padding-right: 5px;">
            ${categories.map(cat => {
                const meta = getCategoryMeta(cat);
                return '<li><a href="' + prefix + 'posts/' + cat + '/index.html">' + meta.icon + ' ' + meta.name + '</a></li>';
            }).join('')}
        </ul>
    </div>
</div>
`;

// Layout Wrapper
const POST_WRAPPER = (post, content, prevPost, nextPost, relatedPosts, prefix, allPosts, categories) => {
    const absoluteUrl = new URL(post.url, BASE_URL).href;
    let ogImage = '';
    if (post.thumbnail) {
        if (post.thumbnail.startsWith('http')) {
            ogImage = post.thumbnail;
        } else {
            // Remove leading ../ or ./ and join with BASE_URL
            const cleanThumb = post.thumbnail.replace(/^(\.\.\/|\.\/)+/, '');
            ogImage = new URL(cleanThumb, BASE_URL).href;
        }
    }

    return `<!--
title: ${post.title}
date: ${post.date}
description: ${post.description}
article_type: ${post.articleType}
-->
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${post.title} | Humanoid Media Factory</title>
    <meta name="description" content="${post.description}">

    <!-- SEO / Canonical / Robots -->
    <link rel="canonical" href="${absoluteUrl}">
    <meta name="robots" content="${post.dirName === 'adult' ? 'noindex, follow' : 'index, follow'}">

    <!-- Structured Data (JSON-LD) -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "BlogPosting",
      "headline": "${post.title.replace(/"/g, '\\"')}",
      "description": "${post.description.replace(/"/g, '\\"')}",
      "image": "${ogImage}",
      "author": {
        "@type": "Person",
        "name": "chnmotoTmz"
      },
      "publisher": {
        "@type": "Organization",
        "name": "Humanoid Media Factory",
        "logo": {
          "@type": "ImageObject",
          "url": "${BASE_URL}images/2026年の決意-AI共生時代に刻む-後悔しない30年-への全力疾走.jpg"
        }
      },
      "datePublished": "${post.date}",
      "dateModified": "${post.date}",
      "mainEntityOfPage": {
        "@type": "WebPage",
        "@id": "${absoluteUrl}"
      }
    }
    </script>

    <!-- OGP -->
    <meta property="og:locale" content="ja_JP">
    <meta property="og:title" content="${post.title} | Humanoid Media Factory">
    <meta property="og:description" content="${post.description}">
    <meta property="og:url" content="${absoluteUrl}">
    <meta property="og:image" content="${ogImage}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="Humanoid Media Factory">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:site" content="@chnmotoTmz">

    <link rel="stylesheet" href="${prefix}assets/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🤖</text></svg>">
    <script src="${prefix}assets/components/site-header.js"></script>
</head>
<body class="humanoid-content">
    ${HEADER(prefix)}

    <div class="portal">
        <div class="portal-layout">
            ${LEFT_COL(prefix, categories)}

            <main class="premium-article">
                <nav class="breadcrumbs" aria-label="Breadcrumb">
                    <ol itemscope itemtype="https://schema.org/BreadcrumbList" style="list-style:none; padding:0; margin:0; display:flex; gap:8px;">
                        <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                            <a itemprop="item" href="${BASE_URL}">
                                <span itemprop="name">Home</span>
                            </a>
                            <meta itemprop="position" content="1" />
                        </li>
                        <li style="color:var(--muted);">&gt;</li>
                        <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                            <a itemprop="item" href="${BASE_URL}posts/${post.dirName}/index.html">
                                <span itemprop="name">${post.categoryName}</span>
                            </a>
                            <meta itemprop="position" content="2" />
                        </li>
                        <li style="color:var(--muted);">&gt;</li>
                        <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                            <span itemprop="name" style="color:var(--text-primary)">${post.title}</span>
                            <meta itemprop="position" content="3" />
                        </li>
                    </ol>
                </nav>

                <h1>${post.title}</h1>

                <div class="devlog-meta">
                    <time>${post.date}</time>
                    <span class="separator">|</span>
                    <span class="card__cat card__cat--small">${post.articleType}</span>
                </div>

                <article class="post-content">
                    ${content}
                </article>

                <!-- Next/Prev Navigation -->
                <nav class="post-nav">
                    <div class="post-nav__item">
                        ${prevPost ? `
                            <span class="post-nav__label">← Previous</span>
                            <a href="${prefix}${prevPost.url}" class="post-nav__link">${prevPost.title}</a>
                        ` : ''}
                    </div>
                    <div class="post-nav__item" style="text-align:right;">
                        ${nextPost ? `
                            <span class="post-nav__label">Next →</span>
                            <a href="${prefix}${nextPost.url}" class="post-nav__link">${nextPost.title}</a>
                        ` : ''}
                    </div>
                </nav>

                <!-- Related Posts -->
                ${relatedPosts.length > 0 ? `
                <section class="related-posts">
                    <h3 class="related-posts__title">Related Stories</h3>
                    <div class="related-grid">
                        ${relatedPosts.map(p => `
                            <a href="${prefix}${p.url}" class="related-card">
                                <h4 class="related-card__title">${p.title}</h4>
                                <time class="related-card__date">${p.date}</time>
                            </a>
                        `).join('')}
                    </div>
                </section>
                ` : ''}
            </main>

            ${SIDEBAR(allPosts, prefix)}
        </div>
    </div>

    ${FOOTER(prefix)}
</body>
</html>`;
};

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

    // Fallback: Extract from HTML tags if comment metadata is missing
    if (!meta.title) {
        const titleMatch = content.match(/<title>([^|<-]+)(?:\s*\||\s*<)/i);
        if (titleMatch) meta.title = titleMatch[1].trim();
    }
    if (!meta.description) {
        const descMatch = content.match(/<meta\s+name=["']description["']\s+content=["']([^"']+)["']/i);
        if (descMatch) meta.description = descMatch[1].trim();
    }
    return meta;
}

function collectHtmlFiles(dir) {
    let results = [];
    if (!fs.existsSync(dir)) return results;
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

// Extract core content from article - Surgical Version (Innermost focus)
function extractCoreContent(html) {
    // 1. Find all metadata blocks. We want the innermost one if nested.
    const metaPattern = /<!--[\s\S]*?title:[\s\S]*?-->/gi;
    let metaMatches = [];
    let match;
    while ((match = metaPattern.exec(html)) !== null) {
        metaMatches.push(match);
    }

    if (metaMatches.length === 0) {
        return html; // Fallback for raw snippets
    }

    // Take the last metadata block to pierce through Matryoshka layers
    const lastMeta = metaMatches[metaMatches.length - 1];
    let startPos = lastMeta.index + lastMeta[0].length;

    // 2. Find the earliest end anchor after the metadata block
    const endAnchors = [
        /<!-- Next\/Prev Navigation -->/i,
        /<!-- Footer -->/i,
        /<\/article>\s*<\/main>/i,
        /<\/main>/i,
        /<footer>/i
    ];

    let endPos = html.length;
    for (const anchor of endAnchors) {
        const m = html.substring(startPos).match(anchor);
        if (m) {
            const candidate = startPos + m.index;
            if (candidate < endPos) {
                endPos = candidate;
            }
        }
    }

    let extracted = html.substring(startPos, endPos).trim();

    // 3. Repeatedly dive into content containers to find raw innerHTML
    // Handles cases where previous build cycles caught containers.
    while (true) {
        const diveMatch = extracted.match(/<article[^>]*class=["'](?:post-content|premium-article)["'][^>]*>/i);
        if (diveMatch) {
            // Dive deeper into the container
            extracted = extracted.substring(diveMatch.index + diveMatch[0].length).trim();
            // Strip the trailing tag from the end of the current block
            extracted = extracted.replace(/<\/article>\s*$/i, '').trim();
        } else {
            break;
        }
    }

    // 4. Final cleanup of problematic tags and artifacts
    extracted = extracted.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
    extracted = extracted.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
    extracted = extracted.replace(/<h1[^>]*>[\s\S]*?<\/h1>/i, '');

    // Generic strip of trailing layout closures if they exist
    for (let i = 0; i < 5; i++) {
        extracted = extracted.replace(/<\/article>\s*$/i, '').trim();
        extracted = extracted.replace(/<\/main>\s*$/i, '').trim();
        extracted = extracted.replace(/<\/div>\s*$/i, '').trim();
    }

    return extracted.trim();
}

async function build() {
    console.log('🚀 Building Enhanced Media Factory (Surgical Clean)...');

    // Collect from posts/ AND root
    const postsFiles = collectHtmlFiles(POSTS_DIR);
    const rootFiles = fs.readdirSync(ROOT_DIR, { withFileTypes: true })
        .filter(entry => entry.isFile() && entry.name.endsWith('.html'))
        .filter(entry => {
            const name = entry.name.toLowerCase();
            return !['index.html', 'about.html', 'archive.html', 'partnership.html', 'dashboard.html', 'humanoid-portal.html', 'temp_index.html', 'old_index.html', 'test-html-post.html'].includes(name);
        })
        .map(entry => path.join(ROOT_DIR, entry.name));

    const files = [...postsFiles, ...rootFiles];
    const postsData = [];

    files.forEach(filePath => {
        const rawContent = fs.readFileSync(filePath, 'utf8');
        const meta = extractMetadata(rawContent);

        let relativeUrl;
        let dirName;
        if (filePath.startsWith(POSTS_DIR)) {
            const relPath = path.relative(POSTS_DIR, filePath).replace(/\\/g, '/');
            relativeUrl = `posts/${relPath}`;
            dirName = path.dirname(relPath);
        } else {
            relativeUrl = path.basename(filePath);
            dirName = '.';
        }

        const categoryName = dirName === '.' ? 'General' : dirName;
        const filename = path.basename(filePath);
        const slug = path.basename(filename, '.html');
        const dateFromFilename = (filename.match(/^(\d{4}-\d{2}-\d{2})/) || [])[1];

        let displayTitle = meta.title || slug;
        // Clean up title if it's just the slug with date
        if (!meta.title && dateFromFilename && displayTitle.startsWith(dateFromFilename)) {
            displayTitle = displayTitle.substring(dateFromFilename.length).replace(/^[-_]+/, '');
        }

        let thumbnail = meta.thumbnail || '';
        if (!thumbnail) {
            const imgMatch = rawContent.match(/<figure[^>]*class=["'](?:article-thumbnail|main-thumbnail)["'][^>]*>\s*<img[^>]*src=["']([^"']+)["']/i);
            if (imgMatch) {
                thumbnail = imgMatch[1];
            } else {
                const genericMatch = rawContent.match(/<img[^>]*src=["']([^"']+)["']/i);
                if (genericMatch) thumbnail = genericMatch[1];
            }
        }

        let absoluteThumbnail = '';
        if (thumbnail) {
            if (thumbnail.startsWith('http')) {
                absoluteThumbnail = thumbnail;
            } else {
                const cleanThumb = thumbnail.replace(/^(\.\.\/|\.\/)+/, '');
                absoluteThumbnail = new URL(cleanThumb, BASE_URL).href;
            }
        }

        let excerpt = meta.description || '';
        if (!excerpt && rawContent) {
            const core = extractCoreContent(rawContent);
            const sanitized = core.replace(/<style[^>]*>[\s\S]*?<\/style>/ig, '').replace(/<figure[^>]*>[\s\S]*?<\/figure>/ig, '');
            const temp = sanitized.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
            excerpt = temp.length > 100 ? temp.substring(0, 100) + '...' : temp;
        }

        postsData.push({
            title: displayTitle,
            date: meta.date || dateFromFilename || '2026-01-01',
            description: meta.description || '',
            excerpt: excerpt,
            articleType: meta.article_type || 'OBSERVATION',
            categoryName: categoryName,
            dirName: dirName,
            slug: slug,
            url: relativeUrl,
            absolutePath: filePath,
            rawContent: rawContent,
            thumbnail: thumbnail,
            absoluteThumbnail: absoluteThumbnail
        });
    });

    // Chronological Sort
    postsData.sort((a, b) => new Date(b.date) - new Date(a.date));

    // Extract categories early
    const categories = [...new Set(postsData.filter(p => p.dirName !== '.').map(p => p.dirName))];

    // 1. Regenerate All Article Pages
    postsData.forEach((post, index) => {
        const prefix = getRelativePrefix(post.absolutePath);
        const prevPost = postsData[index + 1] || null;
        const nextPost = postsData[index - 1] || null;

        const related = postsData
            .filter(p => p.dirName === post.dirName && p.slug !== post.slug)
            .slice(0, 3);

        const core = extractCoreContent(post.rawContent);
        const wrapped = POST_WRAPPER(post, core, prevPost, nextPost, related, prefix, postsData, categories);

        fs.writeFileSync(post.absolutePath, wrapped);
    });

    // 2. Generate archive.html
    const postsByYear = {};
    postsData.forEach(p => {
        const year = new Date(p.date).getFullYear();
        if (!postsByYear[year]) postsByYear[year] = [];
        postsByYear[year].push(p);
    });

    const archiveHtml = `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archive | Humanoid Media Factory</title>
    <!-- SEO / Canonical -->
    <link rel="canonical" href="${BASE_URL}archive.html">
    <meta name="robots" content="index, follow">
    <!-- Structured Data (JSON-LD) -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      "name": "Archive | Humanoid Media Factory",
      "description": "Article Archive for Humanoid Media Factory",
      "url": "${BASE_URL}archive.html",
      "publisher": {
        "@type": "Organization",
        "name": "Humanoid Media Factory"
      }
    }
    </script>
    <!-- OGP -->
    <meta property="og:locale" content="ja_JP">
    <meta property="og:title" content="Archive | Humanoid Media Factory">
    <meta property="og:description" content="Article Archive for Humanoid Media Factory">
    <meta property="og:url" content="${BASE_URL}archive.html">
    <meta property="og:image" content="${BASE_URL}images/2026年の決意-AI共生時代に刻む-後悔しない30年-への全力疾走.jpg">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Humanoid Media Factory">
    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">

    <link rel="stylesheet" href="assets/style.css">
    <script src="assets/components/site-header.js"></script>
</head>
<body class="humanoid-content">
    <site-header prefix=""></site-header>
    <main class="portal archive-portal">
        <h1>Article Archive</h1>
        <div class="archive-list">
            ${Object.keys(postsByYear).sort((a, b) => b - a).map(year => `
                <h2 class="archive-year">${year}</h2>
                ${postsByYear[year].map(p => `
                    <div class="archive-item">
                        <time>${p.date}</time>
                        <a href="${p.url}">${p.title}</a>
                        <span class="badge" style="font-size:0.7rem; opacity:0.6;">${p.categoryName}</span>
                    </div>
                `).join('')}
            `).join('')}
        </div>
    </main>
    <footer>
        <p>&copy; ${new Date().getFullYear()} Humanoid Media Factory</p>
    </footer>
</body>
</html>`;
    fs.writeFileSync(path.join(DIST_DIR, 'archive.html'), archiveHtml);

    // 3. Update index.html
    // Generate Magazine Layout for index.html
    const getExcerpt = (p) => {
        let excerpt = p.description || p.title;
        if (!p.description && p.rawContent) {
            const core = extractCoreContent(p.rawContent);
            const sanitized = core.replace(/<style[^>]*>[\s\S]*?<\/style>/ig, '').replace(/<figure[^>]*>[\s\S]*?<\/figure>/ig, '');
            const temp = sanitized.replace(/<[^>]+>/g, ' ').replace(/\\s+/g, ' ').trim();
            excerpt = temp.length > 80 ? temp.substring(0, 80) + '...' : temp;
        }
        return excerpt;
    };

    const getThumb = (p) => p.thumbnail ? (p.thumbnail.startsWith('http') ? p.thumbnail : new URL(p.thumbnail.replace(/^(\.\.\/|\.\/)+/, ''), BASE_URL).href) : '';

    const heroPosts = postsData.slice(0, 3);
    const heroMain = heroPosts[0];
    const heroSide1 = heroPosts[1];
    const heroSide2 = heroPosts[2];

    let indexCardsHtml = '';
    if (heroMain) {
        const thumb = getThumb(heroMain);
        indexCardsHtml += '      <section class="hero-grid">\n';
        indexCardsHtml += '        <article class="card card--hero" data-category="' + heroMain.dirName + '">\n';
        if (thumb) indexCardsHtml += '            <img src="' + thumb + '" class="card__image" alt="" loading="lazy">\n';
        indexCardsHtml += '            <div class="card__body">\n';
        indexCardsHtml += '                <span class="card__cat">' + getCategoryMeta(heroMain.dirName).name + '</span>\n';
        indexCardsHtml += '                <h2 class="card__title"><a href="' + heroMain.url + '">' + heroMain.title + '</a></h2>\n';
        indexCardsHtml += '                <p class="card__excerpt">' + getExcerpt(heroMain) + '</p>\n';
        indexCardsHtml += '                <time class="card__date">' + heroMain.date + '</time>\n';
        indexCardsHtml += '            </div>\n';
        indexCardsHtml += '        </article>\n';
        indexCardsHtml += '        <div class="hero-side">\n';
        indexCardsHtml += '          <h3 class="hero-side-title">🔥 注目のニュース</h3>\n';
          
        if (heroSide1) {
            indexCardsHtml += '          <article class="card" data-category="' + heroSide1.dirName + '">\n';
            indexCardsHtml += '            <div class="card__body">\n';
            indexCardsHtml += '                <span class="card__cat">' + getCategoryMeta(heroSide1.dirName).name + '</span>\n';
            indexCardsHtml += '                <h3 class="card__title"><a href="' + heroSide1.url + '">' + heroSide1.title + '</a></h3>\n';
            indexCardsHtml += '                <time class="card__date">' + heroSide1.date + '</time>\n';
            indexCardsHtml += '            </div>\n';
            indexCardsHtml += '          </article>\n';
        }
        if (heroSide2) {
            indexCardsHtml += '          <article class="card" data-category="' + heroSide2.dirName + '">\n';
            indexCardsHtml += '            <div class="card__body">\n';
            indexCardsHtml += '                <span class="card__cat">' + getCategoryMeta(heroSide2.dirName).name + '</span>\n';
            indexCardsHtml += '                <h3 class="card__title"><a href="' + heroSide2.url + '">' + heroSide2.title + '</a></h3>\n';
            indexCardsHtml += '                <time class="card__date">' + heroSide2.date + '</time>\n';
            indexCardsHtml += '            </div>\n';
            indexCardsHtml += '          </article>\n';
        }
        indexCardsHtml += '        </div>\n';
        indexCardsHtml += '      </section>\n';
    }

    const remainingPosts = postsData.slice(3);
    const categoryGroups = [
        { title: '🤖 ロボット・AI', color: '#a0a0ff', filters: ['humanoid', 'tech'] },
        { title: '🌍 社会・生活', color: '#6fcf6f', filters: ['news', 'finance', 'gadget', 'relationships'] },
        { title: '🎵 エンタメ・アート', color: '#cf6fcf', filters: ['music', 'art', 'entertainment', 'devlog'] }
    ];

    categoryGroups.forEach((group, idx) => {
        const groupPosts = remainingPosts.filter(p => group.filters.includes(p.dirName)).slice(0, 4);
        if (groupPosts.length > 0) {
            indexCardsHtml += '      <div class="section-header" style="margin-top: 2.5rem; border-bottom: 2px solid ' + group.color + '; padding-bottom: 0.5rem;">\n';
            indexCardsHtml += '        <h2 class="section-label" style="font-size: 1.5rem; color: var(--text-primary, #333);">' + group.title + '</h2>\n';
            indexCardsHtml += '      </div>\n';
            indexCardsHtml += '      <section class="cards-grid" id="cardsGrid' + idx + '">\n';
            groupPosts.forEach(p => {
                indexCardsHtml += '        <article class="card" data-category="' + p.dirName + '">\n';
                indexCardsHtml += '          <div class="card__body">\n';
                indexCardsHtml += '            <span class="card__cat">' + getCategoryMeta(p.dirName).name + '</span>\n';
                indexCardsHtml += '            <h3 class="card__title"><a href="' + p.url + '">' + p.title + '</a></h3>\n';
                indexCardsHtml += '            <time class="card__date">' + p.date + '</time>\n';
                indexCardsHtml += '          </div>\n';
                indexCardsHtml += '        </article>\n';
            });
            indexCardsHtml += '      </section>\n';
        }
    });

    const indexPath = path.join(DIST_DIR, 'index.html');
    if (fs.existsSync(indexPath)) {
        let indexHtml = fs.readFileSync(indexPath, 'utf8');

        // Clean up previous redundant injections
        indexHtml = indexHtml.replace(/<script[^>]*src="[^"]*site-header\.js"[^>]*><\/script>/ig, '');
        indexHtml = indexHtml.replace(/<site-header[^>]*>[\s\S]*?<\/site-header>/ig, '');
        indexHtml = indexHtml.replace(/<header[^>]*class="site-header"[^>]*>[\s\S]*?<\/header>/ig, '');
        indexHtml = indexHtml.replace(/<footer>[\s\S]*?<\/footer>/ig, '');

        // Update head for OGP
        const ogpHead = `
    <!-- SEO / Canonical -->
    <link rel="canonical" href="${BASE_URL}">
    <meta name="robots" content="index, follow">
    <!-- Structured Data (JSON-LD) -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "WebSite",
          "@id": "${BASE_URL}#website",
          "name": "Humanoid Media Factory",
          "url": "${BASE_URL}",
          "description": "朝の観察メディア - AI・社会・人間関係・アダルトまで、人間臭い視点で毎日更新",
          "potentialAction": {
            "@type": "SearchAction",
            "target": "${BASE_URL}?q={search_term_string}",
            "query-input": "required name=search_term_string"
          }
        },
        {
          "@type": "Blog",
          "@id": "${BASE_URL}#blog",
          "mainEntityOfPage": "${BASE_URL}",
          "name": "Humanoid Media Factory",
          "description": "AIエージェントが生成する実験的メディア。ヒューマノイド、最新テクノロジー、ガジェット情報から、日々の開発ログまで、独自の視点で未来を予測・発信します。",
          "publisher": {
            "@type": "Organization",
            "name": "Humanoid Media Factory",
            "logo": {
              "@type": "ImageObject",
              "url": "${BASE_URL}images/2026年の決意-AI共生時代に刻む-後悔しない30年-への全力疾走.jpg"
            }
          }
        }
      ]
    }
    </script>
    <!-- OGP -->
    <meta property="og:locale" content="ja_JP">
    <meta property="og:title" content="Humanoid Media Factory | MSN-Style Portal">
    <meta property="og:description" content="AI × Digital Transformation for Humanoid Lifestyle">
    <meta property="og:url" content="${BASE_URL}">
    <meta property="og:image" content="${BASE_URL}images/2026年の決意-AI共生時代に刻む-後悔しない30年-への全力疾走.jpg">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Humanoid Media Factory">
    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">`;

        if (indexHtml.includes('<!-- SEO / Canonical -->')) {
            indexHtml = indexHtml.replace(/<!-- SEO \/ Canonical -->[\s\S]*?<meta name="twitter:card"[^>]*>/i, ogpHead.trim());
        } else if (indexHtml.includes('<!-- Structured Data (JSON-LD) -->')) {
            indexHtml = indexHtml.replace(/<!-- Structured Data \(JSON-LD\) -->[\s\S]*?<meta name="twitter:card"[^>]*>/i, ogpHead.trim());
        } else if (indexHtml.includes('<!-- OGP -->')) {
            indexHtml = indexHtml.replace(/<!-- OGP -->[\s\S]*?<meta name="twitter:card"[^>]*>/i, ogpHead.trim());
        } else {
            indexHtml = indexHtml.replace(/<\/title>/i, `</title>\n${ogpHead.trim()}`);
        }

        // Re-inject structure
        const headerHtml = HEADER('');
        const footerHtml = FOOTER('');
        const portalLayout = `<div class="portal-layout">
            ${LEFT_COL('', categories)}
            <div class="portal-main">
                <!-- DYNAMIC_CARDS_START -->
                ${indexCardsHtml}
                <!-- DYNAMIC_CARDS_END -->
            </div>
            ${SIDEBAR(postsData, '')}
        </div>`;

        // Update body content
        indexHtml = indexHtml.replace(/<body[^>]*>[\s\S]*?<\/body>/i, `<body class="humanoid-content">
    ${headerHtml}
    <main class="portal">${portalLayout}</main>
    ${footerHtml}
</body>`);

        fs.writeFileSync(indexPath, indexHtml, 'utf8');
    }

    // 4. Generate Category Index Pages
    categories.forEach(cat => {
        const catPosts = postsData.filter(p => p.dirName === cat);
        const catDir = path.join(POSTS_DIR, cat);
        if (!fs.existsSync(catDir)) fs.mkdirSync(catDir, { recursive: true });

        const catTitle = `${cat.charAt(0).toUpperCase() + cat.slice(1)} Archive | Humanoid Media Factory`;
        const catUrl = `${BASE_URL}posts/${cat}/index.html`;
        const catDescription = `${cat} category article archive.`;
        
        let catHtml = `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${catTitle}</title>
    <meta name="description" content="${catDescription}">
    <!-- SEO / Canonical -->
    <link rel="canonical" href="${catUrl}">
    <meta name="robots" content="${cat === 'adult' ? 'noindex, follow' : 'index, follow'}">
    <!-- Structured Data (JSON-LD) -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      "name": "${catTitle}",
      "description": "${catDescription}",
      "url": "${catUrl}"
    }
    </script>
    <!-- OGP -->
    <meta property="og:title" content="${catTitle}">
    <meta property="og:description" content="${catDescription}">
    <meta property="og:url" content="${catUrl}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Humanoid Media Factory">
    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">

    <link rel="stylesheet" href="../../assets/style.css">
    <script src="../../assets/components/site-header.js"></script>
</head>
<body class="humanoid-content">
    ${HEADER('../../')}
    <main class="portal archive-portal">
        <h1>${cat.charAt(0).toUpperCase() + cat.slice(1)} Archive</h1>
        <div class="archive-list">
            ${catPosts.map(p => `
                <div class="archive-item">
                    <time>${p.date}</time>
                    <a href="../../${p.url}">${p.title}</a>
                </div>
            `).join('')}
        </div>
    </main>
    ${FOOTER('../../')}
</body>
</html>`;
        fs.writeFileSync(path.join(catDir, 'index.html'), catHtml, 'utf8');
    });

    // 5. Generate feed.xml (RSS)
    const rssXml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Humanoid Media Factory</title>
    <link>${BASE_URL}</link>
    <description>AIとロボットが紡ぐ、次世代コンテンツパイプライン</description>
    <language>ja</language>
    ${postsData.slice(0, 30).map(p => `
    <item>
        <title>${p.title}</title>
        <link>${new URL(p.url, BASE_URL).href}</link>
        <description><![CDATA[${p.absoluteThumbnail ? `<img src="${p.absoluteThumbnail}" /><br/>` : ''}${p.excerpt || p.title}]]></description>
        <pubDate>${new Date(p.date).toUTCString()}</pubDate>
        <guid>${new URL(p.url, BASE_URL).href}</guid>
    </item>`).join('')}
</channel>
</rss>`;
    fs.writeFileSync(path.join(DIST_DIR, 'feed.xml'), rssXml, 'utf8');

    // 6. Generate sitemap.xml
    const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>${BASE_URL}</loc>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>${BASE_URL}about.html</loc>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>${BASE_URL}humanoid-portal.html</loc>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>${BASE_URL}archive.html</loc>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>${BASE_URL}partnership.html</loc>
        <priority>0.7</priority>
    </url>
    ${categories.map(cat => `
    <url>
        <loc>${BASE_URL}posts/${cat}/index.html</loc>
        <priority>0.8</priority>
    </url>`).join('')}
    ${postsData.filter(p => p.dirName !== 'adult').map(p => `
    <url>
        <loc>${new URL(p.url, BASE_URL).href}</loc>
        <lastmod>${p.date}</lastmod>
        <priority>0.6</priority>
    </url>`).join('')}
</urlset>`;
    fs.writeFileSync(path.join(DIST_DIR, 'sitemap.xml'), sitemapXml, 'utf8');

    // 6. Send Ping to Blog Mura
    try {
        console.log("📡 Sending Ping to Blog Mura...");
        const response = await fetch('https://ping.blogmura.com/xmlrpc/8tzjv6r74eed/');
        if (response.ok) {
            console.log("✅ Ping sent successfully.");
        } else {
            console.log(`⚠️ Ping returned status: ${response.status}`);
        }
    } catch (e) {
        console.log("⚠️ Failed to send Ping to Blog Mura:", e.message);
    }

    console.log('✅ Surgical Build Complete.');
}

build().catch(console.error);
