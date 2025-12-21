import pytest

from src.services.framework.service_registry import service_registry


def test_thumbnail_generator_is_registered():
    cls = service_registry.get_module("ThumbnailGenerator")
    assert cls is not None
    assert cls.get_module_info()["name"] == "ThumbnailGenerator"
