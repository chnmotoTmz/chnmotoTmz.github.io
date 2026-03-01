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

    const files = fs.readdirSync(POSTS_DIR).filter(f => f.endsWith('.html'));
    const posts = files.map(filename => {
        const filePath = path.join(POSTS_DIR, filename);
        const content = fs.readFileSync(filePath, 'utf-8');
        const meta = parseMetadata(content);
        return {
            filename,
            title: meta.title || filename,
            date: meta.date || '2026-01-01',
            description: meta.description || '',
            url: `./posts/${filename}`
        };
    });

    posts.sort((a, b) => new Date(b.date) - new Date(a.date));

    // 1. Generate index.html
    const indexHtml = `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>chnmotoTmz's Media Factory</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; background: #f9f9f9; }
        h1 { color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }
        ul { list-style: none; padding: 0; }
        li { background: #fff; margin-bottom: 20px; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .date { color: #884488; font-weight: bold; font-size: 0.9em; }
        a { text-decoration: none; color: #0077cc; font-size: 1.2em; font-weight: bold; }
        a:hover { text-decoration: underline; }
        p { margin: 10px 0 0; color: #666; }
    </style>
</head>
<body>
    <h1>Latest Articles</h1>
    <ul>
        ${posts.map(p => `
            <li>
                <div class="date">${p.date}</div>
                <a href="${p.url}">${p.title}</a>
                <p>${p.description}</p>
            </li>
        `).join('')}
    </ul>
</body>
</html>
`;
    fs.writeFileSync(INDEX_FILE, indexHtml);

    // 2. Generate feed.xml
    const feedXml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
    <title>chnmotoTmz's Media Factory</title>
    <link>https://chnmotoTmz.github.io</link>
    <description>AI-generated Industrial Media Factory</description>
    <atom:link href="https://chnmotoTmz.github.io/feed.xml" rel="self" type="application/rss+xml" />
    ${posts.map(p => `
    <item>
        <title>${p.title}</title>
        <link>https://chnmotoTmz.github.io/posts/${p.filename}</link>
        <description>${p.description}</description>
        <pubDate>${new Date(p.date).toUTCString()}</pubDate>
        <guid>https://chnmotoTmz.github.io/posts/${p.filename}</guid>
    </item>
    `).join('')}
</channel>
</rss>
`;
    fs.writeFileSync(FEED_FILE, feedXml);

    // 3. Generate sitemap.xml
    const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
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
