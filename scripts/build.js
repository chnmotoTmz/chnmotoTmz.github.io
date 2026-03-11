const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.join(__dirname, '..');
const POSTS_DIR = path.join(ROOT_DIR, 'posts');
const DIST_DIR = ROOT_DIR;

// Utility: Correct relative path based on file depth
function getRelativePrefix(filePath) {
    const rel = path.relative(DIST_DIR, filePath);
    const depth = rel.split(path.sep).length - 1;
    return depth > 0 ? '../'.repeat(depth) : './';
}

// MSN-Style Layout Wrapper
const POST_WRAPPER = (post, content, prevPost, nextPost, relatedPosts, prefix) => `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${post.title} | Humanoid Media Factory</title>
    <meta name="description" content="${post.description}">
    <link rel="stylesheet" href="${prefix}assets/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🤖</text></svg>">
</head>
<body class="humanoid-content">
    <header class="site-header">
        <div class="header-top">
            <a class="brand" href="${prefix}index.html">Humanoid <span>Media</span> Factory</a>
            <div class="header-auth">
                <span style="font-size:0.85rem; color:#616161;">Tokyo, 12°C ☀️</span>
                <a href="${prefix}archive.html" class="tab" style="background:#0078d4; color:#fff; border-radius:4px; padding:5px 15px; text-decoration:none; font-weight:600;">Archive</a>
            </div>
        </div>
        <nav class="header-nav">
            <a href="${prefix}index.html" class="tab">トップ</a>
            <button class="tab">ロボット・AI</button>
            <button class="tab">テクノロジー</button>
            <button class="tab">社会・コラム</button>
            <a href="${prefix}about.html" class="tab">About</a>
        </nav>
    </header>

    <main class="premium-article">
        <nav class="breadcrumbs">
            <a href="${prefix}index.html">Home</a> <span>&gt;</span>
            <a href="${prefix}archive.html">${post.categoryName}</a> <span>&gt;</span>
            <a href="${prefix}archive.html">Archive</a> <span>&gt;</span>
            <span style="color:var(--text-primary)">${post.title}</span>
        </nav>

        <div class="devlog-meta" style="color:#616161; margin-bottom:10px;">
            <time>${post.date}</time>
            <span style="margin:0 10px;">|</span>
            <span class="card__cat">${post.articleType}</span>
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

    <footer>
        <div style="margin-bottom:20px;">
            <a href="${prefix}index.html" class="brand" style="justify-content:center;">Humanoid <span>Media</span> Factory</a>
        </div>
        <div style="display:flex; justify-content:center; gap:20px; margin-bottom:20px;">
            <a href="#" class="tab">Privacy</a>
            <a href="${prefix}about.html" class="tab">About Us</a>
            <a href="${prefix}partnership.html" class="tab">Contact</a>
        </div>
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
                meta[part[0].trim().toLowerCase()] = part.slice(1).join(':').trim();
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

// Extract core content from article (between <main> and </main> or <body> and </body>)
function extractCoreContent(html) {
    const mainMatch = html.match(/<main[^>]*>([\s\S]*?)<\/main>/i);
    if (mainMatch) return mainMatch[1].trim();

    // Fallback: exclude boilerplate manually if no <main> tag
    let content = html.replace(/<!DOCTYPE[\s\S]*?<body[^>]*>/i, '');
    content = content.replace(/<\/body>[\s\S]*?<\/html>/i, '');

    // Remove injected headers/footers if they exist from previous builds
    content = content.replace(/<header class="site-header">[\s\S]*?<\/header>/ig, '');
    content = content.replace(/<footer>[\s\S]*?<\/footer>/ig, '');

    return content.trim();
}

async function build() {
    console.log('🚀 Building Enhanced Media Factory...');

    const files = collectHtmlFiles(POSTS_DIR);
    const posts = [];

    files.forEach(filePath => {
        const rawContent = fs.readFileSync(filePath, 'utf8');
        const meta = extractMetadata(rawContent);
        const relativePath = path.relative(POSTS_DIR, filePath).replace(/\\/g, '/');
        const dirName = path.dirname(relativePath);
        const categoryName = dirName === '.' ? 'General' : dirName;
        const filename = path.basename(filePath);
        const slug = path.basename(filename, '.html');

        // Date from meta or filename
        const dateFromFilename = (filename.match(/^(\d{4}-\d{2}-\d{2})/) || [])[1];

        posts.push({
            title: meta.title || slug,
            date: meta.date || dateFromFilename || '2026-01-01',
            description: meta.description || '',
            articleType: meta.article_type || 'OBSERVATION',
            categoryName: categoryName,
            dirName: dirName,
            slug: slug,
            url: `posts/${relativePath}`,
            absolutePath: filePath,
            rawContent: rawContent
        });
    });

    // Chronological Sort
    posts.sort((a, b) => new Date(b.date) - new Date(a.date));

    // 1. Regenerate All Article Pages with Wrapper
    posts.forEach((post, index) => {
        const prefix = '../../'; // Since articles are in posts/category/
        const prevPost = posts[index + 1] || null;
        const nextPost = posts[index - 1] || null;

        // Related: same directory, excluding self
        const related = posts
            .filter(p => p.dirName === post.dirName && p.slug !== post.slug)
            .slice(0, 3);

        const core = extractCoreContent(post.rawContent);
        const wrapped = POST_WRAPPER(post, core, prevPost, nextPost, related, prefix);

        fs.writeFileSync(post.absolutePath, wrapped);
    });

    // 2. Generate archive.html
    const postsByYear = {};
    posts.forEach(p => {
        const year = new Date(p.date).getFullYear();
        if (!postsByYear[year]) postsByYear[year] = [];
        postsByYear[year].push(p);
    });

    const archiveHtml = `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archive | Humanoid Media Factory</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body class="humanoid-content">
    <header class="site-header">
        <div class="header-top">
            <a class="brand" href="index.html">Humanoid <span>Media</span> Factory</a>
        </div>
    </header>
    <main class="portal" style="max-width:800px; margin:0 auto; padding:40px 20px;">
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
</html>
    `;
    fs.writeFileSync(path.join(DIST_DIR, 'archive.html'), archiveHtml);

    // 3. Update index.html (Simple version for this demo, focusing on the portal part)
    // In a real scenario, we'd reuse the renderCard logic from the original build.js
    console.log('✅ Articles wrapped and Archive page generated.');
}

build().catch(console.error);
