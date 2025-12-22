import re

def convert_custom_tags_to_markdown(text: str) -> str:
    """
    Converts custom tags (HTML-style and BBCode-style) to Markdown equivalents.
    Ensures high fidelity for Hatena Blog posting.
    Aggressively truncates long headings and strips AI junk.
    """
    # 0. Pre-cleaning AI junk
    # Remove CSS blocks or meta-text often found at the end
    text = re.sub(r"```css.*?```", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"（次に私ができること：.*?\）", "", text, flags=re.DOTALL)
    text = re.sub(r"Next I can do:.*", "", text, flags=re.DOTALL | re.IGNORECASE)

    # 1. Handle HTML tags
    # Headings
    text = re.sub(r"<h2.*?>(.*?)</h2>", r"## \1", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<h3.*?>(.*?)</h3>", r"### \1", text, flags=re.DOTALL | re.IGNORECASE)
    # Bold/Strong
    text = re.sub(r"<(b|strong)>(.*?)</\1>", r"**\2**", text, flags=re.DOTALL | re.IGNORECASE)
    # List Items (Li to dash)
    text = re.sub(r"<li>(.*?)</li>", r"- \1", text, flags=re.DOTALL | re.IGNORECASE)
    # Unordered Lists (Remove container tags but keep content)
    text = re.sub(r"<ul>(.*?)</ul>", r"\1", text, flags=re.DOTALL | re.IGNORECASE)
    # Basic Paragraphs
    text = re.sub(r"<p>(.*?)</p>", r"\1\n\n", text, flags=re.DOTALL | re.IGNORECASE)
    # Br tags
    text = re.sub(r"<br\s*/?>", r"\n", text, flags=re.IGNORECASE)

    # 2. Handle existing BBCode-style tags (Backward Compatibility)
    text = re.sub(r"\[h2\](.*?)\[/h2\]", r"## \1", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[h3\](.*?)\[/h3\]", r"### \1", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[b\](.*?)\[/b\]", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[li\](.*?)\[/li\]", r"- \1", text, flags=re.DOTALL | re.IGNORECASE)

    # 3. Aggressive Heading Truncation (Physical enforcement)
    def truncate_header(match):
        level = match.group(1) # ## or ###
        content = match.group(2).strip()
        if len(content) > 35: # Limit relaxed to 30-35 chars
            content = content[:30] + "..."
        return f"{level} {content}"

    text = re.sub(r"^(#{2,3})\s*(.+)$", truncate_header, text, flags=re.MULTILINE)

    # 4. Clean up
    # Remove any remaining closing tags
    text = re.sub(r"</?[a-zA-Z0-9]+.*?>", "", text)
    text = re.sub(r"\[/[a-zA-Z0-9]+\]", "", text)
    
    # Fix double newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
