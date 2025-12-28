import yaml

with open('blogs.yml', encoding='utf-8') as f:
    data = yaml.safe_load(f)
    blogs = data.get('blogs', {})
    print(f"Top-level blog keys: {list(blogs.keys())}")
    print(f"Total blogs defined: {len(blogs)}")
