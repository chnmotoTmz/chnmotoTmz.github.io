
import os
import re

mapping = {
    "posts/music/2026-03-03-吉川晃司の低音が響かない-COMPLEX攻略のための胸鳴り低音強化メソッドと推奨機材.html": "i1FQX--FeNg",
    "posts/2026-03-02-深夜の静寂-鋼の伴走者--令和八年-中途覚醒を-知の黄金期-へ変える生活osの革命.html": "vWXN2bttm4g",
    "posts/2026-03-02-鋼の給仕-熱き滋味--令和八年-山嶺の知恵とヒューマノイドが紡ぐ-最適化-の極致.html": "4a0b67fdcSg",
    "posts/2026-03-02-骨身に沁みる-鋼の滋味---令和八年-圧力鍋とヒューマノイドが醸成する食卓の革命.html": "ktrconfVssg",
    "posts/humanoid/2026-03-04-ホルムズの火花と生活防衛のリアル-2026年3月-私たちは物理の壁にどう向き合うか.html": "3jducjFxLR4",
    "posts/humanoid/2026-03-04-語らずとも-心は通う-2026年-ヒューマノイドが鉄腕アトムの身振りを実装する必然.html": "FGQZn8U2HDI",
    "posts/humanoid/2026-03-04-肩に掛ける文明の火-2026年-Anker-Solix-C300が変えるエネルギーと自由の物理的距離.html": "GwxSNoOh3fw",
    "posts/humanoid/2026-03-04-富士山が見えるという贅沢の再定義-2026年-高解像度の日常が最後に辿り着く不変の座標.html": "_DVxOsbH8AA",
    "posts/humanoid/2026-03-04-垂直の絶壁を溶かす技術-2026年-ドローンと杖が再定義する移動の自律.html": "CDiALMj2iAA",
    "posts/humanoid/2026-03-04-人形の館の深淵に触れる-2026年-カラクリの不完全さがAIヒューマンモデルに命を吹き込む.html": "aAiaXRjlSlA",
    "posts/humanoid/2026-03-04-海峡の封鎖とおかんの備え-2026年3月-エネルギー危機を賢く生き抜くための処方箋.html": "3jducjFxLR4",
    "posts/humanoid/2026-03-04-海峡の封鎖と生活防衛の防波堤-2026年-エネルギー危機を賢く生き抜くための生存戦略.html": "3jducjFxLR4",
    "posts/humanoid/2026-03-04-垂直の避難とエネルギーの野生-2026年-京都の猛暑から愛犬を守る登山知恵の転用術.html": "NH0f8VuKJBI"
}

def update_article(filepath, video_id):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'class="main-thumbnail"' in content:
        print(f"Skipping {filepath}, already has thumbnail")
        return

    # Find the best place to insert
    # Usually after <article class="premium-article"> or <div class="content"> followed by some comments

    thumbnail_html = f'<figure class="main-thumbnail"><img src="https://img.youtube.com/vi/{video_id}/hqdefault.jpg" alt="YouTube Thumbnail" style="width:100%;max-height:400px;object-fit:cover;border-radius:8px;margin-bottom:1.5rem;"><figcaption style="text-align:center;font-size:0.85rem;color:#888;margin-top:-1rem;margin-bottom:1.5rem;font-style:italic;">YouTubeより引用</figcaption></figure>'

    # Try to find the second <article class="premium-article"> for music posts if it exists
    if filepath.startswith("posts/music/"):
        parts = re.split(r'(<article class="premium-article">)', content)
        if len(parts) >= 5: # [before, tag1, mid, tag2, after]
            parts.insert(4, thumbnail_html)
            new_content = "".join(parts)
        else:
            new_content = content.replace('<article class="premium-article">', f'<article class="premium-article">{thumbnail_html}', 1)
    else:
        # For others, try to find <article class="premium-article"> or just after the metadata comment
        if '<article class="premium-article">' in content:
            new_content = content.replace('<article class="premium-article">', f'<article class="premium-article">{thumbnail_html}', 1)
        else:
            # Fallback: after the metadata comment
            new_content = re.sub(r'(-->\s*)', r'\1' + thumbnail_html, content, count=1)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Updated {filepath}")

for path, vid in mapping.items():
    if os.path.exists(path):
        update_article(path, vid)
    else:
        print(f"File not found: {path}")
