import markdown
from bleach import Cleaner, linkify
from bleach.css_sanitizer import CSSSanitizer
from bleach.sanitizer import ALLOWED_ATTRIBUTES, ALLOWED_TAGS

# Define custom allowed tags and attributes
custom_allowed_tags = list(ALLOWED_TAGS) + [
    "p",
    "span",
    "div",
    "br",
    "strong",
    "em",
    "u",
    "s",
    "blockquote",
    "code",
    "pre",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "hr",
    "a",
]
custom_allowed_attributes = {
    **ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "target"],
    "span": ["style"],
    "div": ["style"],
    "p": ["style"],
}

# Define CSS sanitizer
css_sanitizer = CSSSanitizer()

# Create a Cleaner object with custom rules for tags, attributes, and CSS sanitizer
cleaner = Cleaner(
    tags=custom_allowed_tags,
    attributes=custom_allowed_attributes,
    css_sanitizer=css_sanitizer,
)


async def convert_markdown_to_html(text):
    """Converts Markdown text to sanitized HTML."""
    # Convert Markdown to HTML
    html = markdown.markdown(text)
    # Linkify URLs in the text
    linkified_html = linkify(html)
    # Sanitize HTML with the Cleaner object
    sanitized_html = cleaner.clean(linkified_html)
    return sanitized_html
