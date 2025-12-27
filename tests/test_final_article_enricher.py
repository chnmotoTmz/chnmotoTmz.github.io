import os
import json
from src.tasks.final_article_enricher_task import FinalArticleEnricherTask


def make_task():
    return FinalArticleEnricherTask({})


def test_restore_original_affiliate(monkeypatch, tmp_path):
    task = make_task()
    content = "# Title\n\nSome content\n\n## 🛒 おすすめ商品\n\n**[OldProduct](https://example.com/old)**\n"
    inputs = {
        "final_title": "T",
        "final_content": content,
        "article_concept": {"keywords": ["test"]},
        "blog_data": {"hatena_blog_id": "testblog"}
    }

    # Simulate no products returned
    monkeypatch.setattr("src.services.rakuten_api.search_related_products", lambda c, k: [])

    out = task.execute(inputs)

    assert out["affiliate_status"] == "restored_original"
    assert "おすすめ商品" in out["final_content"]
    assert "OldProduct" in out["final_content"]


def test_placeholder_when_no_original(monkeypatch, tmp_path):
    task = make_task()
    content = "# Title\n\nSome content\n"
    inputs = {
        "final_title": "T",
        "final_content": content,
        "article_concept": {"keywords": ["test"]},
        "blog_data": {"hatena_blog_id": "testblog2"}
    }

    # Simulate no products returned
    monkeypatch.setattr("src.services.rakuten_api.search_related_products", lambda c, k: [])

    # Ensure log file is removed
    try:
        os.remove("logs/affiliate_failures.log")
    except OSError:
        pass

    out = task.execute(inputs)

    assert out["affiliate_status"] == "placeholder_inserted"
    assert "おすすめ商品" in out["final_content"]

    # Check log was written
    with open("logs/affiliate_failures.log", "r", encoding="utf-8") as fh:
        lines = [l.strip() for l in fh.readlines() if l.strip()]
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry.get("blog") == "testblog2"
    assert entry.get("action") == "placeholder_inserted"


def test_products_found(monkeypatch):
    task = make_task()
    content = "# Title\n\nSome content\n"
    inputs = {
        "final_title": "T",
        "final_content": content,
        "article_concept": {"keywords": ["test"]},
        "blog_data": {"hatena_blog_id": "blog3"}
    }

    products = [
        {"itemName": "Prod1", "itemPrice": 1234, "affiliate_url": "https://rk.example/1", "imageUrl": "https://img.example/1.jpg"}
    ]

    monkeypatch.setattr("src.services.rakuten_api.search_related_products", lambda c, k: products)

    out = task.execute(inputs)

    assert out["affiliate_status"] == "found"
    assert "Prod1" in out["final_content"]
    assert "https://img.example/1.jpg" in out["final_content"]
