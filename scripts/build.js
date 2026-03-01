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

async function build() {
    console.log('🚀 Building Industrial Media Factory...');

    if (!fs.existsSync(POSTS_DIR)) {
        console.error('Error: Posts directory not found');
        return;
    }

    const files = fs.readdirSync(POSTS_DIR).filter(f => f.endsWith('.html'));
    const posts = [];

    files.forEach(file => {
        const filePath = path.join(POSTS_DIR, file);
        const rawContent = fs.readFileSync(filePath, 'utf8');
        const meta = extractMetadata(rawContent);
        const slug = path.basename(file, '.html');

        const post = {
            title: meta.title || 'Untitled',
            date: meta.date || new Date().toISOString().split('T')[0],
            description: meta.description || '',
            tags: meta.tags ? meta.tags.split(',').map(t => t.trim()) : [],
            slug: slug,
            url: `${slug}.html`
        };

        // Wrap the partial HTML into a full page
        const fullContent = POST_WRAPPER(post.title, rawContent, post.date, post.description, post.tags);
        fs.writeFileSync(path.join(DIST_DIR, `${slug}.html`), fullContent);

        posts.push(post);
        console.log(`- Synthesized ${slug}.html`);
    });

    // Sort descending
    posts.sort((a, b) => new Date(b.date) - new Date(a.date));

    // 1. index.html
    const indexHtml = `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>chnmotoTmz Media Factory</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header><h1>chnmotoTmz Media Factory</h1></header>
    <main>
        <ul class="post-list">
            ${posts.map(p => `
                <li>
                    <time>${p.date}</time>
                    <a href="${p.url}">${p.title}</a>
                </li>
            `).join('')}
        </ul>
    </main>
    <footer><p>&copy; 2026 chnmotoTmz</p></footer>
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
