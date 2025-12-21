import pytest
from src.processes.blog_selection import BlogSelectorProcess

class TestBlogSelectorProcess:
    def test_parse_commands_simple(self):
        texts = ["Hello", "!TechBlog", "#Serious", "World"]
        cleaned, cmd_kw, repost_kw, styles = BlogSelectorProcess.parse_commands(texts)
        assert cleaned == ["Hello", "World"]
        assert cmd_kw == "TechBlog"
        assert repost_kw is None
        assert styles == ["Serious"]

    def test_parse_commands_repost(self):
        texts = ["@TechBlog", "Rewrite this"]
        cleaned, cmd_kw, repost_kw, styles = BlogSelectorProcess.parse_commands(texts)
        # @TechBlog means repost mode = True, keyword = TechBlog
        assert cmd_kw is None
        assert repost_kw == "TechBlog"
        assert cleaned == ["Rewrite this"]

    def test_parse_commands_repost_with_prompt(self):
        texts = ["@TechBlog #MakeItFunny"]
        cleaned, cmd_kw, repost_kw, styles = BlogSelectorProcess.parse_commands(texts)
        assert repost_kw == "TechBlog"
        assert styles == ["MakeItFunny"]
        assert cleaned == []

    def test_filter_blogs_exclude(self):
        blogs = {
            "tech": {"exclude_keywords": ["politics"], "hatena_id": "h", "hatena_blog_id": "b", "api_key": "k"},
            "news": {"exclude_keywords": [], "hatena_id": "h", "hatena_blog_id": "b", "api_key": "k"}
        }
        content = "I hate politics"
        filtered = BlogSelectorProcess.filter_blogs(blogs, content)
        assert "tech" not in filtered
        assert "news" in filtered

    def test_filter_blogs_invalid(self):
        blogs = {
            "valid": {"hatena_id": "h", "hatena_blog_id": "b", "api_key": "k"},
            "invalid": {"hatena_id": "", "hatena_blog_id": "b", "api_key": "k"},
            "default": {"hatena_id": "default", "hatena_blog_id": "b", "api_key": "k"}
        }
        filtered = BlogSelectorProcess.filter_blogs(blogs, "")
        assert "valid" in filtered
        assert "invalid" not in filtered
        assert "default" not in filtered

    def test_heuristic_select(self):
        blogs = {
            "cat_blog": {"keywords": ["cat", "kitten"], "blog_name": "Cats"},
            "dog_blog": {"keywords": ["dog", "puppy"], "blog_name": "Dogs"}
        }
        content = "I love a cute kitten"
        selection = BlogSelectorProcess.heuristic_select(content, blogs)
        assert selection == "cat_blog"

    def test_parse_selection_response(self):
        resp = '```json\n{"blog_id": "my_blog", "reason": "test"}\n```'
        bid, reason = BlogSelectorProcess.parse_selection_response(resp, [])
        assert bid == "my_blog"
        assert reason == "test"

    def test_resolve_blog_id(self):
        blogs = {
            "my_blog_key": {"hatena_blog_id": "my-awesome-blog", "blog_name": "My Blog"}
        }
        # Exact key
        assert BlogSelectorProcess.resolve_blog_id("my_blog_key", blogs) == "my_blog_key"
        # Host name
        assert BlogSelectorProcess.resolve_blog_id("my-awesome-blog", blogs) == "my_blog_key"
        # Blog Name
        assert BlogSelectorProcess.resolve_blog_id("My Blog", blogs) == "my_blog_key"
        # URL
        assert BlogSelectorProcess.resolve_blog_id("https://my-awesome-blog.hatenablog.com/", blogs) == "my_blog_key"
