import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class CommandContext:
    type: str = "GENERATE"  # GENERATE, REPOST, SAVE_TO_BUFFER, GENERATE_FROM_BUFFER
    action: str = "GENERATE"
    target_blog: Optional[str] = None
    style_prompt: Optional[str] = None
    is_repost: bool = False
    has_rewrite_instruction: bool = False
    buffer_slot: Optional[int] = None
    source_texts: List[str] = None

    def __post_init__(self):
        if self.source_texts is None:
            self.source_texts = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CommandParser:
    """
    Parses commands from text messages.
    !BlogKeyword -> Target blog
    @BlogKeyword -> Repost
    #Style -> Style instruction
    @1, @2 -> Buffer operations
    """

    def parse_multi(self, texts: List[str]) -> CommandContext:
        ctx = CommandContext()
        cleaned_texts = []

        for text in texts:
            if not text:
                continue
            
            # Extract Style (# or ＃)
            style_matches = re.findall(r'[#＃](.+?)(?=\s|$|[!！@＠])', text)
            if style_matches:
                ctx.style_prompt = " ".join(style_matches)
                text = re.sub(r'[#＃].+?(\s|$|[!！@＠])', r'\1', text).strip()

            # Extract Blog Selection (! or ！名)
            blog_match = re.search(r'[!！]([a-zA-Z0-9\u4e00-\u9faf\u3040-\u309f\u30a0-\u30ff]+)', text)
            if blog_match:
                ctx.target_blog = blog_match.group(1)
                text = text.replace(blog_match.group(0), "").strip()

            # Extract Repost/Buffer (@ or ＠)
            # Pattern: @1 (Load), @1 text (Save), @Blog (Repost)
            repost_match = re.search(r'[@＠]([a-zA-Z0-9\u4e00-\u9faf\u3040-\u309f\u30a0-\u30ff]*)', text)
            if repost_match:
                val = repost_match.group(1)
                if val.isdigit():
                    ctx.buffer_slot = int(val)
                    # If there's other text, it's a SAVE, otherwise it's a LOAD (handled in task)
                    # But we'll set action here if possible
                    text = text.replace(repost_match.group(0), "").strip()
                    if text:
                        ctx.action = "SAVE_TO_BUFFER"
                    else:
                        ctx.action = "GENERATE_FROM_BUFFER"
                else:
                    ctx.is_repost = True
                    ctx.action = "REPOST"
                    if val:
                        ctx.target_blog = val
                    text = text.replace(repost_match.group(0), "").strip()

            if text:
                cleaned_texts.append(text)

        ctx.source_texts = cleaned_texts
        # If it was SAVE but no text, revert to standard? 
        # Actually the task handles the specifics.
        
        return ctx
