#!/usr/bin/env node
/**
 * gen-devlog.js
 * ルールベースの開発日誌ジェネレーター（chnmotoTmz.github.io 完結版）
 *
 * やること:
 *   1. posts/ 以下を再帰走査し、今日 (JST) に作成/更新された HTML ファイルを検出
 *   2. 各ファイルのメタデータ (title, date) を抽出
 *   3. ルールベースで開発日誌 HTML を生成
 *   4. posts/devlog/YYYY-MM-DD-....html に保存
 *   5. git add / commit / push
 *
 * 使い方: node scripts/gen-devlog.js
 *         npm run devlog
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// ── 設定 ──────────────────────────────────────────────────────────────
const ROOT = path.join(__dirname, '..');
const POSTS_DIR = path.join(ROOT, 'posts');
const DEVLOG_DIR = path.join(POSTS_DIR, 'devlog');
const JST_OFFSET = 9; // UTC+9

// ── ユーティリティ ────────────────────────────────────────────────────

/** 今日の日付を JST で "YYYY-MM-DD" として返す */
function todayJST() {
    const now = new Date();
    const jst = new Date(now.getTime() + JST_OFFSET * 60 * 60 * 1000);
    return jst.toISOString().slice(0, 10);
}

/** ディレクトリを再帰走査して .html ファイルの絶対パスを返す */
function collectHtmlFiles(dir) {
    let results = [];
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            results = results.concat(collectHtmlFiles(full));
        } else if (entry.isFile() && entry.name.endsWith('.html')) {
            results.push(full);
        }
    }
    return results;
}

/** HTML コメント内のメタデータを抽出（build.js と同じロジック） */
function extractTitle(content) {
    // <!-- title: ... --> 形式
    const commentMatch = content.match(/<!--[\s\S]*?title:\s*([^\n\r]+)/i);
    if (commentMatch) return commentMatch[1].trim();
    // <title> タグ
    const titleMatch = content.match(/<title[^>]*>([^<]+)<\/title>/i);
    if (titleMatch) return titleMatch[1].replace(/\s*\|\s*.*$/, '').trim(); // " | サイト名" を除去
    // <h1> タグ
    const h1Match = content.match(/<h1[^>]*>([^<]+)<\/h1>/i);
    if (h1Match) return h1Match[1].trim();
    return null;
}

/** ファイルの mtime が今日 (JST) かどうか確認 */
function isToday(filePath, todayStr) {
    const stat = fs.statSync(filePath);
    const jst = new Date(stat.mtimeMs + JST_OFFSET * 60 * 60 * 1000);
    return jst.toISOString().slice(0, 10) === todayStr;
}

/** カテゴリをパスから推定 */
function guessCategory(filePath) {
    const rel = filePath.replace(/\\/g, '/');
    if (rel.includes('/humanoid/')) return 'ロボット・AI';
    if (rel.includes('/music/')) return '音楽';
    if (rel.includes('/tech/')) return 'テクノロジー';
    if (rel.includes('/rakuten/')) return '楽天';
    if (rel.includes('/art/')) return 'アート';
    if (rel.includes('/devlog/')) return '開発日誌'; // 自分自身は除外される
    return '雑記';
}

// ── メイン ────────────────────────────────────────────────────────────

function main() {
    const today = todayJST();
    console.log(`📅 開発日誌を生成します (${today})`);

    // devlog 自身の既存ファイルは除外対象にする
    const existingDevlogSlugs = new Set(
        fs.existsSync(DEVLOG_DIR)
            ? fs.readdirSync(DEVLOG_DIR).map(f => f.replace(/\.html$/, ''))
            : []
    );

    // posts/ 全体を走査
    const allHtmlFiles = fs.existsSync(POSTS_DIR) ? collectHtmlFiles(POSTS_DIR) : [];

    // 今日更新されたファイルのうち devlog 以外を抽出
    const updatedArticles = allHtmlFiles
        .filter(f => {
            const rel = f.replace(/\\/g, '/');
            if (rel.includes('/devlog/')) return false; // devlog 自身は除外
            return isToday(f, today);
        })
        .map(f => {
            const content = fs.readFileSync(f, 'utf8');
            const title = extractTitle(content) || path.basename(f, '.html');
            const category = guessCategory(f);
            const relUrl = 'posts/' + path.relative(POSTS_DIR, f).replace(/\\/g, '/');
            return { title, category, relUrl };
        });

    console.log(`  更新記事: ${updatedArticles.length} 件`);

    // ── 日誌本文を生成 ──────────────────────────────────────────────

    const articleSection = updatedArticles.length > 0
        ? `<p>今日は以下の記事を追加・更新しました。</p>
<ul style="padding-left:1.5rem; line-height:2;">
  ${updatedArticles.map(a =>
            `<li>[${a.category}] <a href="../../${a.relUrl}" style="color:#a0a0ff;">${a.title}</a></li>`
        ).join('\n  ')}
</ul>`
        : `<p>今日はブログ記事の追加・更新はありませんでした。</p>`;

    const updateCount = updatedArticles.length;
    const categoryCounts = {};
    updatedArticles.forEach(a => {
        categoryCounts[a.category] = (categoryCounts[a.category] || 0) + 1;
    });
    const catSummary = Object.entries(categoryCounts)
        .map(([k, v]) => `${k} ${v}件`)
        .join('、') || 'なし';

    const diaryBody = `<article>
<h1>開発日誌 ${today}</h1>
<p>${today}の作業記録です。</p>
${articleSection}
<p>本日の更新サマリー: 全${updateCount}件（${catSummary}）。</p>
<p>引き続き少しずつ前に進んでいきます。</p>
</article>`;

    // ── HTML ファイル生成 ──────────────────────────────────────────

    const safeDate = today;
    const filename = `${safeDate}-devlog.html`;
    const outputPath = path.join(DEVLOG_DIR, filename);

    // devlog ディレクトリがなければ作成
    fs.mkdirSync(DEVLOG_DIR, { recursive: true });

    // 簡略化したテンプレート（build.js でラップされることを想定）
    const fullHtml = `<!--
title: 開発日誌 ${today}
date: ${today}
description: chnmoto 個人開発日誌 ${today}
article_type: OBSERVATION
-->
<div class="devlog-content">
    ${diaryBody}
</div>`;

    fs.writeFileSync(outputPath, fullHtml, 'utf8');
    console.log(`✅ 生成完了: ${outputPath}`);

    // ── git commit & push ────────────────────────────────────────
    try {
        execSync(`git add "${outputPath}"`, { cwd: ROOT, stdio: 'inherit' });
        execSync(`git commit -m "devlog: ${today} (rule-based, ${updateCount} articles)"`, { cwd: ROOT, stdio: 'inherit' });
        execSync('git push origin main', { cwd: ROOT, stdio: 'inherit' });
        console.log('🚀 GitHubにプッシュしました');
    } catch (err) {
        // "nothing to commit" は正常
        const msg = err.message || '';
        if (msg.includes('nothing to commit') || msg.includes('nothing added')) {
            console.log('ℹ️  変更なし（git commit スキップ）');
        } else {
            console.warn('⚠️  git push に失敗しました（ローカルには保存済み）:', msg.slice(0, 200));
        }
    }

    console.log(`\n📋 本日の更新記事一覧:`);
    updatedArticles.forEach((a, i) => console.log(`  ${i + 1}. [${a.category}] ${a.title}`));
}

main();
