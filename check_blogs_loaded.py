from src.blog_config import BlogConfig

if __name__ == "__main__":
    blogs = BlogConfig.get_all_blogs()
    print(f"Total blogs: {len(blogs)}")
    for k, v in blogs.items():
        print(f"- {k}: {v.get('blog_name')} (API key: {v.get('hatena_api_key')})")
