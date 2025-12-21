import re

def convert_custom_tags_to_markdown(text: str) -> str:
    """
    Converts custom tags (e.g., [h2], [b], [li]) to Markdown equivalents.
    Extend this function as needed for new tags.
    """
    # Headings
    text = re.sub(r"\[h2\](.*?)\[/h2\]", r"## \1", text, flags=re.DOTALL)
    text = re.sub(r"\[h3\](.*?)\[/h3\]", r"### \1", text, flags=re.DOTALL)
    # Bold
    text = re.sub(r"\[b\](.*?)\[/b\]", r"**\1**", text, flags=re.DOTALL)
    # List items
    text = re.sub(r"\[li\](.*?)\[/li\]", r"- \1", text, flags=re.DOTALL)
    # Remove any remaining closing tags (for robustness)
    text = re.sub(r"\[/[a-zA-Z0-9]+\]", "", text)
    return text.strip()
