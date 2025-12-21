"""
ブログ選択ロジックのテストスクリプト
家族で食事、ケーキ屋のWEBリンクなど、様々なシナリオをテスト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.tasks.blog_selector_task import BlogSelectorTask
from src.blog_config import BlogConfig

def test_blog_selector():
    """ブログ選択のテストケース"""
    
    # BlogSelectorTaskを初期化
    config = {}
    selector = BlogSelectorTask(config)
    
    print("=" * 80)
    print("ブログ選択ロジック テスト")
    print("=" * 80)
    
    # テストケース1: ケーキ屋のWEBリンク
    print("\n【テストケース1】ケーキ屋のWEBリンク")
    print("-" * 80)
    test_case_1 = {
        "texts": [
            "今日は素敵なケーキ屋さんを見つけました！",
            "https://example-cake-shop.com",
            "モンブランが絶品でした。季節のフルーツタルトも美しい。",
            "お店の雰囲気も良く、また行きたいです。"
        ],
        "images_for_prompt": []
    }
    
    try:
        result_1 = selector.execute(test_case_1)
        blog_1 = result_1.get('blog_config')
        if blog_1:
            print(f"✅ 選択されたブログ: {blog_1.get('name')} ({blog_1.get('hatena_blog_id')})")
            print(f"   期待値: うまいもの探訪記 (kaigotmusic.hatenablog.com)")
            if blog_1.get('hatena_blog_id') == 'kaigotmusic.hatenablog.com':
                print("   ✅ 正解！")
            else:
                print("   ❌ 期待値と異なります")
        else:
            print("❌ ブログが選択されませんでした")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # テストケース2: 家族で食事（家族の絆重視）
    print("\n【テストケース2】家族で食事（家族の絆重視）")
    print("-" * 80)
    test_case_2 = {
        "texts": [
            "久しぶりに家族みんなで外食しました。",
            "子供たちの笑顔を見ていると、幸せな気持ちになります。",
            "家族で過ごす時間は何よりも大切。",
            "また家族で来たいね、と話しながら帰りました。"
        ],
        "images_for_prompt": []
    }
    
    try:
        result_2 = selector.execute(test_case_2)
        blog_2 = result_2.get('blog_config')
        if blog_2:
            print(f"✅ 選択されたブログ: {blog_2.get('name')} ({blog_2.get('hatena_blog_id')})")
            print(f"   期待値: Wellness Mom Diary (wellness-mom-diary.hatenablog.com)")
            if blog_2.get('hatena_blog_id') == 'wellness-mom-diary.hatenablog.com':
                print("   ✅ 正解！")
            else:
                print(f"   ⚠️  別のブログが選択されました（これも正解の可能性あり）")
        else:
            print("❌ ブログが選択されませんでした")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # テストケース3: 家族でレストラン訪問（グルメレビュー重視）
    print("\n【テストケース3】家族でレストラン訪問（グルメレビュー重視）")
    print("-" * 80)
    test_case_3 = {
        "texts": [
            "家族で横浜中華街の新しいレストランに行ってきました。",
            "本格四川麻婆豆腐は辛さの中に深いコクがあり絶品。",
            "小籠包は皮が薄くてジューシー。一口で幸せが広がります。",
            "店名: 香港楼、住所: 横浜市中区、予算: 3000円/人",
            "https://example-restaurant.com"
        ],
        "images_for_prompt": []
    }
    
    try:
        result_3 = selector.execute(test_case_3)
        blog_3 = result_3.get('blog_config')
        if blog_3:
            print(f"✅ 選択されたブログ: {blog_3.get('name')} ({blog_3.get('hatena_blog_id')})")
            print(f"   期待値: うまいもの探訪記 (kaigotmusic.hatenablog.com)")
            if blog_3.get('hatena_blog_id') == 'kaigotmusic.hatenablog.com':
                print("   ✅ 正解！")
            else:
                print("   ⚠️  別のブログが選択されました")
        else:
            print("❌ ブログが選択されませんでした")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # テストケース4: 子供と料理（食育・学び重視）
    print("\n【テストケース4】子供と料理（食育・学び重視）")
    print("-" * 80)
    test_case_4 = {
        "texts": [
            "中学生の息子と一緒にカレーを作りました。",
            "野菜の切り方を教えながら、包丁の使い方も学べました。",
            "マイクラで学んだレシピを実際に作ってみたいと言い出したのがきっかけです。",
            "料理を通じて、子供の成長を感じる瞬間でした。"
        ],
        "images_for_prompt": []
    }
    
    try:
        result_4 = selector.execute(test_case_4)
        blog_4 = result_4.get('blog_config')
        if blog_4:
            print(f"✅ 選択されたブログ: {blog_4.get('name')} ({blog_4.get('hatena_blog_id')})")
            print(f"   期待値: 中学生の趣味と学び・子育てハブ (kosodate-hub.hatenablog.com)")
            if blog_4.get('hatena_blog_id') == 'kosodate-hub.hatenablog.com':
                print("   ✅ 正解！")
            else:
                print("   ⚠️  別のブログが選択されました（Wellness Mom Diaryも正解の可能性）")
        else:
            print("❌ ブログが選択されませんでした")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # テストケース5: 登山（グルメ・家族要素なし）
    print("\n【テストケース5】登山（グルメ・家族要素なし）")
    print("-" * 80)
    test_case_5 = {
        "texts": [
            "六甲山にハイキングに行ってきました。",
            "天気も良く、山頂からの眺めは最高でした。",
            "登山靴の選び方やおすすめギアも紹介します。",
            "関西の山歩き初心者にもおすすめのコースです。"
        ],
        "images_for_prompt": []
    }
    
    try:
        result_5 = selector.execute(test_case_5)
        blog_5 = result_5.get('blog_config')
        if blog_5:
            print(f"✅ 選択されたブログ: {blog_5.get('name')} ({blog_5.get('hatena_blog_id')})")
            print(f"   期待値: Hiking Community from Kansai (arafo40tozan.hatenadiary.jp)")
            if blog_5.get('hatena_blog_id') == 'arafo40tozan.hatenadiary.jp':
                print("   ✅ 正解！")
            else:
                print("   ❌ 期待値と異なります")
        else:
            print("❌ ブログが選択されませんでした")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # テストケース6: IT技術（家族・グルメ要素なし）
    print("\n【テストケース6】IT技術（家族・グルメ要素なし）")
    print("-" * 80)
    test_case_6 = {
        "texts": [
            "Pythonでブログ自動生成システムを作ってみました。",
            "FlaskとDockerを使った開発環境の構築方法を解説します。",
            "Qiitaにも投稿予定です。",
            "エンジニアの皆さんの参考になれば嬉しいです。"
        ],
        "images_for_prompt": []
    }
    
    try:
        result_6 = selector.execute(test_case_6)
        blog_6 = result_6.get('blog_config')
        if blog_6:
            print(f"✅ 選択されたブログ: {blog_6.get('name')} ({blog_6.get('hatena_blog_id')})")
            print(f"   期待値: 真面目に人生を考えるページ (yamasan1969.hatenablog.com)")
            if blog_6.get('hatena_blog_id') == 'yamasan1969.hatenablog.com':
                print("   ✅ 正解！")
            else:
                print("   ❌ 期待値と異なります")
        else:
            print("❌ ブログが選択されませんでした")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)

if __name__ == "__main__":
    test_blog_selector()
