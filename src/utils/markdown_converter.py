import re
import logging

logger = logging.getLogger(__name__)

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
    # Links with Images: <a href="..."><img src="..." alt="..."></a> -> [![alt](img_url)](link_url)
    def convert_image_link(match):
        tag_attrs = match.group(1)
        img_tag = match.group(2)
        href_match = re.search(r'href=[\'"]([^\'"]+)[\'"]', tag_attrs, re.IGNORECASE)
        img_url_match = re.search(r'src=[\'"]([^\'"]+)[\'"]', img_tag, re.IGNORECASE)
        alt_match = re.search(r'alt=[\'"]([^\'"]+)[\'"]', img_tag, re.IGNORECASE)
        
        link_url = href_match.group(1) if href_match else "#"
        img_url = img_url_match.group(1) if img_url_match else ""
        alt_text = alt_match.group(1) if alt_match else ""
        
        if img_url:
            return f"[![{alt_text}]({img_url})]({link_url})"
        return f"[{img_tag}]({link_url})"

    text = re.sub(r'<a\s+([^>]*?)>\s*(<img\s+[^>]*?>)\s*</a>', convert_image_link, text, flags=re.DOTALL | re.IGNORECASE)

    # Standard Links: <a href="...">Text</a> -> [Text](url)
    def convert_a_tag(match):
        tag_attrs = match.group(1)
        text_content = match.group(2)
        href_match = re.search(r'href=[\'"]([^\'"]+)[\'"]', tag_attrs, re.IGNORECASE)
        url = href_match.group(1) if href_match else "#"
        text_content = re.sub(r"<.*?>", "", text_content)
        return f"[{text_content}]({url})"
    
    text = re.sub(r'<a\s+([^>]*?)>(.*?)</a>', convert_a_tag, text, flags=re.DOTALL | re.IGNORECASE)

    # Isolated Images: <img src="..." alt="..."> -> ![alt](url)
    def convert_img_tag(match):
        img_url_match = re.search(r'src=[\'"]([^\'"]+)[\'"]', match.group(0), re.IGNORECASE)
        alt_match = re.search(r'alt=[\'"]([^\'"]+)[\'"]', match.group(0), re.IGNORECASE)
        url = img_url_match.group(1) if img_url_match else ""
        alt = alt_match.group(1) if alt_match else ""
        return f"![{alt}]({url})" if url else ""

    text = re.sub(r'<img\s+[^>]*?>', convert_img_tag, text, flags=re.IGNORECASE)

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

    # 3. Smart Heading Correction (Physical enforcement)
    def handle_header(match):
        level = match.group(1) # ## or ###
        content = match.group(2).strip()
        
        # Case A: Extremely long - likely body text wrongly tagged
        if len(content) > 60:
            logger.warning(f"Heading too long ({len(content)} chars). Converting to plain text: {content[:30]}...")
            return content # Strip the ## markers
            
        # Case B: Moderately long - truncate to keep TOC clean
        if len(content) > 35:
            return f"{level} {content[:30]}..."
            
        return f"{level} {content}"

    text = re.sub(r"^(#{2,3})\s*(.+)$", handle_header, text, flags=re.MULTILINE)

    # 4. Handle Hatena specific tags
    # Ensure [:contents] is isolated and correct
    text = re.sub(r"\[+[:：]contents\]+", "[:contents]", text, flags=re.IGNORECASE)
    text = text.replace("[:contents]", "\n\n[:contents]\n\n")

    # 5. Clean up
    # Remove any remaining closing tags
    text = re.sub(r"</?[a-zA-Z0-9]+.*?>", "", text)
    text = re.sub(r"\[/[a-zA-Z0-9]+\]", "", text)
    
    # Fix double newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
