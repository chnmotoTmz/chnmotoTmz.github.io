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

// Components
const HEADER = (prefix) => `
<site-header prefix="${prefix}"></site-header>
`;

const FOOTER = (prefix) => `
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
`;

const SIDEBAR = (posts, prefix) => `
<aside class="sidebar">
    <div class="sidebar-box">
        <h3 class="sidebar-title">アクセスランキング</h3>
        <ul class="ranking-list">
            ${posts.slice(0, 5).map((p, i) => `
                <li>
                    <span style="font-size:1.2rem; font-weight:900; color:#e1dfdd; margin-right:10px;">${i + 1}</span>
                    <a href="${prefix}${p.url}">${p.title}</a>
                </li>
            `).join('')}
        </ul>
    </div>
    <div class="sidebar-box" style="background: #f3f5f7; border:1px solid #e1dfdd;">
        <h3 class="sidebar-title">注目トピック</h3>
        <div style="display:flex; flex-wrap:wrap; gap:8px;">
            <span class="badge" style="background:#fff; padding:4px 8px; border-radius:4px; font-size:0.8rem; border:1px solid #e1dfdd;">#Humanoid</span>
            <span class="badge" style="background:#fff; padding:4px 8px; border-radius:4px; font-size:0.8rem; border:1px solid #e1dfdd;">#AI_DX</span>
            <span class="badge" style="background:#fff; padding:4px 8px; border-radius:4px; font-size:0.8rem; border:1px solid #e1dfdd;">#Robotics</span>
        </div>
    </div>
</aside>
`;

const LEFT_COL = (prefix) => `
<div class="left-col">
    <div class="sidebar-box">
        <h3 class="sidebar-title">主要カテゴリー</h3>
        <ul class="ranking-list">
            <li><a href="${prefix}archive.html?cat=humanoid">🤖 ロボット・AI</a></li>
            <li><a href="${prefix}archive.html?cat=tech">💻 テクノロジー</a></li>
            <li><a href="${prefix}archive.html?cat=devlog">📝 開発ログ</a></li>
            <li><a href="${prefix}archive.html?cat=gadget">📱 ガジェット</a></li>
        </ul>
    </div>
</div>
`;

// Layout Wrapper
const POST_WRAPPER = (post, content, prevPost, nextPost, relatedPosts, prefix, allPosts) => `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${post.title} | Humanoid Media Factory</title>
    <meta name="description" content="${post.description}">
    <link rel="stylesheet" href="${prefix}assets/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🤖</text></svg>">
    <script src="${prefix}assets/components/site-header.js"></script>
</head>
<body class="humanoid-content">
    ${HEADER(prefix)}

    <div class="portal">
        <div class="portal-layout">
            ${LEFT_COL(prefix)}

            <main class="premium-article">
                <nav class="breadcrumbs">
                    <a href="${prefix}index.html">Home</a> <span>&gt;</span>
                    <a href="${prefix}archive.html">${post.categoryName}</a> <span>&gt;</span>
                    <span style="color:var(--text-primary)">${post.title}</span>
                </nav>

                <div class="devlog-meta" style="color:#616161; margin-bottom:10px;">
                    <time>${post.date}</time>
                    <span style="margin:0 10px;">|</span>
                    <span class="card__cat" style="color:var(--accent-red)">${post.articleType}</span>
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

// Extract core content from article - Surgical Version
function extractCoreContent(html) {
    // Look for metadata block as start anchor
    const metaStartMatch = html.match(/<!--\s*title:/i);
    if (!metaStartMatch) {
        // If no metadata, attempt to find <div class="content"> or similar
        const contentMatch = html.match(/<div[^>]*class="content"[^>]*>/i);
        if (contentMatch) {
            let start = contentMatch.index + contentMatch[0].length;
            let sub = html.substring(start);
            const endMatch = sub.match(/<\/div>\s*<\/article>/i) || sub.match(/<\/article>/i);
            if (endMatch) return sub.substring(0, endMatch.index).trim();
        }
        return html.replace(/<!DOCTYPE[\s\S]*?<body[^>]*>/i, '').replace(/<\/body>[\s\S]*?<\/html>/i, '').trim();
    }

    // Slice from metadata start
    let content = html.substring(metaStartMatch.index);

    // Look for end markers (Next/Prev nav, Related posts, etc.)
    const endMarkers = [
        /<!-- Next\/Prev Navigation -->/i,
        /<nav[^>]*class="post-nav"/i,
        /<!-- Related Posts -->/i,
        /<section[^>]*class="related-posts"/i,
        /<\/article>\s*<\/main>/i
    ];

    for (const marker of endMarkers) {
        const match = content.match(marker);
        if (match) {
            content = content.substring(0, match.index);
            break;
        }
    }

    // Remove any leftover structural junk at the very end
    content = content.replace(/<\/article>\s*$/i, '');
    content = content.replace(/<\/div>\s*$/i, '');

    return content.trim();
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

        postsData.push({
            title: meta.title || slug,
            date: meta.date || dateFromFilename || '2026-01-01',
            description: meta.description || '',
            articleType: meta.article_type || 'OBSERVATION',
            categoryName: categoryName,
            dirName: dirName,
            slug: slug,
            url: relativeUrl,
            absolutePath: filePath,
            rawContent: rawContent
        });
    });

    // Chronological Sort
    postsData.sort((a, b) => new Date(b.date) - new Date(a.date));

    // 1. Regenerate All Article Pages
    postsData.forEach((post, index) => {
        const prefix = getRelativePrefix(post.absolutePath);
        const prevPost = postsData[index + 1] || null;
        const nextPost = postsData[index - 1] || null;

        const related = postsData
            .filter(p => p.dirName === post.dirName && p.slug !== post.slug)
            .slice(0, 3);

        const core = extractCoreContent(post.rawContent);
        const wrapped = POST_WRAPPER(post, core, prevPost, nextPost, related, prefix, postsData);

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
    <link rel="stylesheet" href="assets/style.css">
    <script src="assets/components/site-header.js"></script>
</head>
<body class="humanoid-content">
    <site-header prefix=""></site-header>
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
</html>`;
    fs.writeFileSync(path.join(DIST_DIR, 'archive.html'), archiveHtml);

    // 3. Update index.html
    const indexCardsHtml = postsData.slice(0, 15).map(p => {
        let excerpt = p.description || p.title;
        if (!p.description && p.rawContent) {
            const core = extractCoreContent(p.rawContent);
            const sanitized = core.replace(/<figure[^>]*>[\s\S]*?<\/figure>/ig, '');
            const temp = sanitized.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
            excerpt = temp.length > 80 ? temp.substring(0, 80) + '...' : temp;
        }
        return `
    <article class="card" data-category="${p.categoryName || 'other'}">
      <img src="https://picsum.photos/seed/${encodeURIComponent(p.slug)}/120/80" alt="" class="card__image" loading="lazy">
      <div class="card__body">
        <h3 class="card__title"><a href="${p.url}">${p.title}</a></h3>
        <p class="card__excerpt">${excerpt}</p>
        <div style="display:flex; gap:10px; align-items:center;">
            <span class="card__cat" style="font-size:0.7rem; color:var(--accent-red)">${p.articleType || 'NEWS'}</span>
            <time class="card__date">${p.date}</time>
        </div>
      </div>
    </article>`;
    }).join('\n');

    const indexPath = path.join(DIST_DIR, 'index.html');
    if (fs.existsSync(indexPath)) {
        let indexHtml = fs.readFileSync(indexPath, 'utf8');

        // Clean up previous redundant injections
        indexHtml = indexHtml.replace(/<script[^>]*src="[^"]*site-header\.js"[^>]*><\/script>/ig, '');
        indexHtml = indexHtml.replace(/<site-header[^>]*>[\s\S]*?<\/site-header>/ig, '');
        indexHtml = indexHtml.replace(/<header[^>]*class="site-header"[^>]*>[\s\S]*?<\/header>/ig, '');
        indexHtml = indexHtml.replace(/<footer>[\s\S]*?<\/footer>/ig, '');

        // Re-inject structure
        const headerHtml = HEADER('');
        const footerHtml = FOOTER('');
        const portalLayout = `<div class="portal-layout">
            ${LEFT_COL('')}
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

    console.log('✅ Surgical Build Complete.');
}

build().catch(console.error);
