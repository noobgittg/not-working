from config import Config

SMALLCAPS_MAP = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ',
    'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ',
    'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ'
}

def to_smallcaps(text: str) -> str:
    """Converts alphabetic characters to stylish smallcaps while preserving symbols, numbers, and tags."""
    if not text:
        return ""
    return "".join(SMALLCAPS_MAP.get(c, c) for c in str(text))

def badge(text: str) -> str:
    """Formats a stylish smallcaps badge."""
    return f"✦ **{to_smallcaps(text)}** ✦"

def btn_text(emoji: str, text: str) -> str:
    """Formats an inline button label with short emoji and smallcaps text."""
    return f"{emoji} {to_smallcaps(text)}"

def header(emoji: str, text: str) -> str:
    """Formats a section header with emoji and bold smallcaps text."""
    return f"{emoji} **{to_smallcaps(text)}**"

def field(emoji: str, label: str, value: str) -> str:
    """Formats a clean key-value field line."""
    return f"• {emoji} **{to_smallcaps(label)}** : `{value}`"

def style_text(title: str, items: dict = None) -> str:
    """Formats a stylized card with header, key-value items, and watermark."""
    out = f"✦ **{to_smallcaps(title)}** ✦\n\n"
    if items:
        for k, v in items.items():
            out += f"• **{to_smallcaps(k)}** : `{v}`\n"
        out += "\n"
    out += format_watermark()
    return out

def format_watermark() -> str:
    """Returns official bot watermark footer link."""
    return f"\n\n⚡ **{to_smallcaps('ᴘᴏᴡᴇʀᴇᴅ ʙʏ')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
