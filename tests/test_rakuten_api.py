import pytest
from src.services import rakuten_api


def test_token_fallback(monkeypatch):
    # Simulate search_products returning empty for full keyword, but returning products for token tokens
    calls = []
    def fake_search_products(q, application_id=None, max_retries=5):
        calls.append(q)
        if q == "full complex keyword":
            return []
        if q == "complex keyword":
            return [{"itemName": "TokenProd", "itemPrice": 100, "itemUrl": "https://rk/1", "imageUrl": "https://img/1.jpg"}]
        return []

    monkeypatch.setattr(rakuten_api, 'search_products', fake_search_products)
    concept = {"keywords": ["full complex keyword"], "title": "full complex keyword"}
    products = rakuten_api.search_related_products(concept, keywords=["full complex keyword"])
    assert any('TokenProd' in (p.get('itemName') or '') for p in products)
    assert len(calls) >= 1


def test_error_skipped_and_success(monkeypatch):
    # First query returns an error dict, second returns results
    def fake_search_products(q, application_id=None, max_retries=5):
        if q == "first":
            return {"status": "error", "message": "bad"}
        return [{"itemName": "GoodProd", "itemPrice": 200, "itemUrl": "https://rk/2", "imageUrl": "https://img/2.jpg"}]

    monkeypatch.setattr(rakuten_api, 'search_products', fake_search_products)
    concept = {"keywords": ["first", "second"]}
    products = rakuten_api.search_related_products(concept, keywords=["first", "second"])
    assert any('GoodProd' in (p.get('itemName') or '') for p in products)


def test_no_app_id(monkeypatch):
    # If the app id is missing, search_products should return error dict and search_related_products should return empty
    monkeypatch.setenv('RAKUTEN_APP_ID', '')
    # reload the module to pick up env change is overkill; instead monkeypatch search_products to return error
    def fake_search_products(q, application_id=None, max_retries=5):
        return {"status": "error", "message": "RAKUTEN_APP_ID missing."}
    monkeypatch.setattr(rakuten_api, 'search_products', fake_search_products)

    products = rakuten_api.search_related_products({}, keywords=["x"])
    assert products == []
