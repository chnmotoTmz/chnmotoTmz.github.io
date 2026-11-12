const fs = require('fs');
const path = require('path');

const POSTS_DIR = path.join(__dirname, 'posts');
const INDEX_FILE = path.join(__dirname, 'index.html');
const FEED_FILE = path.join(__dirname, 'feed.xml');
const SITEMAP_FILE = path.join(__dirname, 'sitemap.xml');

function parseMetadata(html) {
    const metaMatch = html.match(/<!--([\s\S]*?)-->/);
    if (!metaMatch) return {};

    const meta = {};
    const lines = metaMatch[1].split('\n');
    lines.forEach(line => {
        const [key, ...valueParts] = line.split(':');
        if (key && valueParts.length > 0) {
            meta[key.trim().toLowerCase()] = valueParts.join(':').trim();
        }
    });
    return meta;
}

function build() {
    console.log("Building static site indices...");

    if (!fs.existsSync(POSTS_DIR)) {
        console.error("Posts directory not found.");
        return;
    }

    // Recursively collect all HTML files under POSTS_DIR
    function collectHtmlFiles(dir) {
        let results = [];
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                results = results.concat(collectHtmlFiles(fullPath));
            } else if (entry.isFile() && entry.name.endsWith('.html')) {
                results.push(fullPath);
            }
        }
        return results;
    }
    const htmlFiles = collectHtmlFiles(POSTS_DIR);
    const posts = htmlFiles.map(filePath => {
        const content = fs.readFileSync(filePath, 'utf-8');
        const meta = parseMetadata(content);
        const relativePath = path.relative(POSTS_DIR, filePath).replace(/\\\\/g, '/'); // normalize
        const parts = relativePath.split('/');
        const filename = parts.pop();
        const category = parts.length > 0 ? parts.join('/') : 'Uncategorized';
        return {
            filename,
            title: meta.title || filename,
            date: meta.date || '2026-01-01',
            description: meta.description || '',
            excerpt: meta.excerpt || '',
            thumbnail: meta.thumbnail || '',
            url: `./posts/${relativePath}`,
            category
        };
    });

    posts.sort((a, b) => new Date(b.date) - new Date(a.date));

    // Group posts by category
    const postsByCategory = {};
    for (const post of posts) {
        if (!postsByCategory[post.category]) postsByCategory[post.category] = [];
        postsByCategory[post.category].push(post);
    }

    // Generate Popular Articles (Mocked by picking 5 random/featured posts)
    const shuffledPosts = [...posts].sort(() => 0.5 - Math.random());
    const popularPosts = shuffledPosts.slice(0, 5);

    function renderPostCard(p) {
        return `
        <div class="post-card">
            ${p.thumbnail ? `<img src="${p.thumbnail}" alt="${p.title}">` : ''}
            <div class="date">${p.date}</div>
            <h3><a href="${p.url}">${p.title}</a></h3>
            <p>${p.description}</p>
            ${p.excerpt ? `<div class="excerpt">${p.excerpt}</div>` : ''}
        </div>`;
    }

    function renderPopularSidebar(prefix = '') {
        return `
        <aside class="sidebar-ranking">
            <h2 style="font-size: 1.2rem; border-bottom: 2px solid #ff8c00; padding-bottom: 5px;">🔥 人気記事ランキング</h2>
            <ul style="list-style: none; padding: 0;">
                ${popularPosts.map((p, i) => `
                <li style="margin-bottom: 15px; display: flex; align-items: flex-start; gap: 10px;">
                    <span style="font-weight: bold; font-size: 1.2rem; color: #ff8c00;">${i + 1}</span>
                    <a href="${prefix}${p.url}" style="text-decoration: none; color: #fff; font-size: 0.95rem; line-height: 1.3;">${p.title}</a>
                </li>
                `).join('')}
            </ul>
        </aside>`;
    }

    // 1. Generate index.html with sidebar navigation
    const indexHtml = `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>chnmotoTmz's Media Factory</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
    <style>
        .post-card { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; padding: 15px; border-radius: 8px; background: rgba(255,255,255,0.05); }
        .post-card img { width: 100%; height: 200px; object-fit: cover; border-radius: 6px; margin-bottom: 10px; }
        .post-card h3 { margin: 0; font-size: 1.2rem; }
        .post-card p { margin: 0; font-size: 0.9rem; color: #ccc; }
        .post-card .excerpt { font-size: 0.85rem; color: #aaa; margin-top: 5px; }
        .post-card .date { font-size: 0.8rem; color: #888; }
        @media(min-width: 768px){
            .post-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
            .post-card { margin-bottom: 0; }
        }
    </style>
</head>
<body>
    <div class="hero">
        <div class="hero-bg"></div>
        <h1 class="hero-title">🦾 Humanoid Media Factory 🦾</h1>
        <p class="hero-sub">AI とロボットが紡ぐ、次世代コンテンツパイプライン</p>
    </div>
    <div class="container">
        <aside class="sidebar">
            <h2>Categories</h2>
            <ul>
                ${Object.keys(postsByCategory).map(cat => `<li><a href="./category/${cat.replace(/[\s\/]+/g, '-').toLowerCase()}.html">${cat}</a></li>`).join('')}
            </ul>
            ${renderPopularSidebar()}
        </aside>
        <main class="content">
            <h1>Latest Articles</h1>
            ${Object.entries(postsByCategory).map(([cat, items]) => `
            <section id="${cat.replace(/\\s+/g, '-').toLowerCase()}">
                <h2 class="category-title">${cat}</h2>
                <div class="post-list">
                    ${items.slice(0, 3).map(p => renderPostCard(p)).join('')}
                </div>
                <div style="text-align: right; margin-top: 10px;">
                    <a href="./category/${cat.replace(/[\s\/]+/g, '-').toLowerCase()}.html" style="color: #ff8c00; text-decoration: none; font-weight: bold;">もっと見る →</a>
                </div>
                </div>
            </section>`).join('')}
        </main>
    </div>
</body>
</html>
`;
    fs.writeFileSync(INDEX_FILE, indexHtml);

    // 1.5 Generate Category Hub Pages
    const CATEGORY_DIR = path.join(__dirname, 'category');
    if (!fs.existsSync(CATEGORY_DIR)) {
        fs.mkdirSync(CATEGORY_DIR, { recursive: true });
    }

    for (const [cat, items] of Object.entries(postsByCategory)) {
        const catSlug = cat.replace(/[\s\/]+/g, '-').toLowerCase();
        const catHtml = `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${cat} - chnmotoTmz's Media Factory</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../style.css">
    <style>
        .post-card { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; padding: 15px; border-radius: 8px; background: rgba(255,255,255,0.05); }
        .post-card img { width: 100%; height: 200px; object-fit: cover; border-radius: 6px; margin-bottom: 10px; }
        .post-card h3 { margin: 0; font-size: 1.2rem; }
        .post-card p { margin: 0; font-size: 0.9rem; color: #ccc; }
        @media(min-width: 768px){
            .post-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
            .post-card { margin-bottom: 0; }
        }
    </style>
</head>
<body>
    <div class="hero" style="min-height: 20vh; padding: 40px 20px;">
        <h1 class="hero-title">${cat} Articles</h1>
        <p class="hero-sub"><a href="../index.html" style="color:#fff;">← Back to Home</a></p>
    </div>
    <div class="container">
        <aside class="sidebar">
            <h2>Categories</h2>
            <ul>
                ${Object.keys(postsByCategory).map(c => `<li><a href="./${c.replace(/[\s\/]+/g, '-').toLowerCase()}.html">${c}</a></li>`).join('')}
            </ul>
            ${renderPopularSidebar('../')}
        </aside>
        <main class="content">
            <h2 class="category-title">${cat} 全記事一覧</h2>
            <div class="post-list">
                ${items.map(p => {
                    const adjP = {...p, url: '../' + p.url.replace('./', '')};
                    return renderPostCard(adjP);
                }).join('')}
            </div>
        </main>
    </div>
</body>
</html>
`;
        fs.writeFileSync(path.join(CATEGORY_DIR, `${catSlug}.html`), catHtml);
    }

    // 2. Generate feed.xml (unchanged)

    // 3. Generate sitemap.xml
    const sitemapXml = `<? xml version = "1.0" encoding = "UTF-8" ?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url><loc>https://chnmotoTmz.github.io/</loc><priority>1.0</priority></url>
                ${posts.map(p => `
    <url>
        <loc>https://chnmotoTmz.github.io/posts/${p.filename}</loc>
        <lastmod>${p.date}</lastmod>
        <priority>0.8</priority>
    </url>
    `).join('')}
            </urlset>
`;
    fs.writeFileSync(SITEMAP_FILE, sitemapXml);

    console.log(`Successfully generated index, feed, and sitemap for ${posts.length} articles.`);
}

build();
