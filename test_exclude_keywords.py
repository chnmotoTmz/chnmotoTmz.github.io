"""
排除キーワードロジックの単体テスト（Flask不要）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.blog_config import BlogConfig

def test_exclude_logic():
    """排除キーワードのロジックをシミュレーション"""
    
    print("=" * 80)
    print("排除キーワード ロジックテスト")
    print("=" * 80)
    
    # 全ブログ設定を取得
    all_blogs = BlogConfig.get_all_blogs()
    
    # テストケース1: ケーキ屋のWEBリンク
    print("\n【テストケース1】ケーキ屋のWEBリンク")
    print("-" * 80)
    content_1 = """
    今日は素敵なケーキ屋さんを見つけました！
    https://example-cake-shop.com
    モンブランが絶品でした。季節のフルーツタルトも美しい。
    お店の雰囲気も良く、また行きたいです。
    """.lower()
    
    filtered_1 = filter_by_exclude_keywords(content_1, all_blogs)
    print(f"コンテンツ: ケーキ屋レビュー（グルメ）")
    print(f"除外されないブログ: {list(filtered_1.keys())}")
    print(f"✅ 期待値: umai_mono, wellness_mom_diary, kosodate_hub が含まれる")
    
    # テストケース2: 家族で食事（家族重視）
    print("\n【テストケース2】家族で食事（家族の絆重視）")
    print("-" * 80)
    content_2 = """
    久しぶりに家族みんなで外食しました。
    子供たちの笑顔を見ていると、幸せな気持ちになります。
    家族で過ごす時間は何よりも大切。
    また家族で来たいね、と話しながら帰りました。
    """.lower()
    
    filtered_2 = filter_by_exclude_keywords(content_2, all_blogs)
    print(f"コンテンツ: 家族での食事体験")
    print(f"除外されないブログ: {list(filtered_2.keys())}")
    print(f"✅ 期待値: wellness_mom_diary, kosodate_hub, umai_mono が含まれる")
    
    # テストケース3: 登山（グルメ・家族なし）
    print("\n【テストケース3】登山（グルメ・家族要素なし）")
    print("-" * 80)
    content_3 = """
    六甲山にハイキングに行ってきました。
    天気も良く、山頂からの眺めは最高でした。
    登山靴の選び方やおすすめギアも紹介します。
    関西の山歩き初心者にもおすすめのコースです。
    """.lower()
    
    filtered_3 = filter_by_exclude_keywords(content_3, all_blogs)
    print(f"コンテンツ: 関西ハイキング")
    print(f"除外されないブログ: {list(filtered_3.keys())}")
    print(f"✅ 期待値: arafo40tozan, hikingsong が含まれる")
    print(f"❌ 除外されるべき: wellness_mom_diary, kosodate_hub, umai_mono (「登山」が除外KW)")
    
    # テストケース4: IT技術（家族・グルメなし）
    print("\n【テストケース4】IT技術（家族・グルメ要素なし）")
    print("-" * 80)
    content_4 = """
    Pythonでブログ自動生成システムを作ってみました。
    FlaskとDockerを使った開発環境の構築方法を解説します。
    Qiitaにも投稿予定です。
    エンジニアの皆さんの参考になれば嬉しいです。
    プログラミング
    """.lower()
    
    filtered_4 = filter_by_exclude_keywords(content_4, all_blogs)
    print(f"コンテンツ: Python技術記事")
    print(f"除外されないブログ: {list(filtered_4.keys())}")
    print(f"✅ 期待値: yamasan1969, lifehacking1919 が含まれる")
    print(f"❌ 除外されるべき: wellness_mom_diary, kosodate_hub, umai_mono, fx (「IT技術」「プログラミング」が除外KW)")
    
    # テストケース5: 家族でレストラン（グルメ+家族）
    print("\n【テストケース5】家族でレストラン訪問（グルメレビュー重視）")
    print("-" * 80)
    content_5 = """
    家族で横浜中華街の新しいレストランに行ってきました。
    本格四川麻婆豆腐は辛さの中に深いコクがあり絶品。
    小籠包は皮が薄くてジューシー。一口で幸せが広がります。
    店名: 香港楼、住所: 横浜市中区、予算: 3000円/人
    グルメ レストラン
    """.lower()
    
    filtered_5 = filter_by_exclude_keywords(content_5, all_blogs)
    print(f"コンテンツ: 家族でレストラン（グルメ+家族）")
    print(f"除外されないブログ: {list(filtered_5.keys())}")
    print(f"✅ 期待値: umai_mono が含まれる（グルメ重視なら）")
    print(f"⚠️ wellness_mom_diary, kosodate_hub は「グルメ」が除外KWに含まれない")
    
    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)

def filter_by_exclude_keywords(content_text: str, blogs: dict) -> dict:
    """BlogSelectorTaskと同じロジックで排除キーワードをフィルタリング"""
    filtered = {}
    content_lower = content_text.lower()
    
    for blog_id, blog_config in blogs.items():
        exclude_keywords = blog_config.get('exclude_keywords', [])
        if not exclude_keywords:
            filtered[blog_id] = blog_config
            continue
        
        has_excluded = False
        matched_keywords = []
        for keyword in exclude_keywords:
            if keyword.lower() in content_lower:
                has_excluded = True
                matched_keywords.append(keyword)
        
        if has_excluded:
            print(f"   🚫 除外: {blog_id} (マッチ: {', '.join(matched_keywords)})")
        else:
            filtered[blog_id] = blog_config
    
    return filtered

if __name__ == "__main__":
    test_exclude_logic()
