import streamlit as st
import anthropic
import base64
import os
import json
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
import subprocess
import tempfile
import io

FONT_PATH = str(Path(__file__).parent / "assets" / "fonts" / "Heebo-Bold.ttf")


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load the Heebo font as bytes (works with non-ASCII paths)."""
    with open(FONT_PATH, "rb") as f:
        return ImageFont.truetype(io.BytesIO(f.read()), size)

# ─────────────────────────────────────────
#  Page config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Packaging Extractor",
    page_icon="📦",
    layout="wide",
)

# ─────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .main { background: #f8f9fa; }
    .stButton>button {
        background: linear-gradient(135deg, #6c63ff, #48bfef);
        color: white; border: none; border-radius: 10px;
        padding: 0.6rem 2rem; font-size: 1rem; font-weight: 600;
        transition: opacity .2s;
    }
    .stButton>button:hover { opacity: .85; color: white; }
    .card {
        background: white; border-radius: 14px;
        padding: 1.5rem; margin-bottom: 1rem;
        box-shadow: 0 2px 12px rgba(0,0,0,.07);
    }
    .step-badge {
        display: inline-block;
        background: #6c63ff; color: white;
        border-radius: 50%; width: 28px; height: 28px;
        text-align: center; line-height: 28px;
        font-weight: 700; margin-left: 8px;
    }
    .section-title { font-size: 1.1rem; font-weight: 700; color: #333; margin-bottom: .5rem; }
    .hebrew-content {
        direction: rtl; text-align: right;
        font-family: 'Segoe UI', Arial, sans-serif;
        line-height: 1.8; color: #222;
    }
    .img-thumb { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  Marketing template (from user example)
# ─────────────────────────────────────────
MARKETING_TEMPLATE = """
אתה כותב תוכן שיווקי מקצועי בעברית למוצרי חשמל לבית לאתר איקומרס ישראלי.
הנה דוגמא לסגנון ולמבנה שאני רוצה – שמור בדיוק על אותה מבנה ומינוח:

---דוגמא---
מכשיר להכנת מאפים עם 4 פלטות מתחלפות ANYBAKE מבית Food appeal
ANYBAKE - Multi Baker מכשיר אחד, אינסוף פינוקים קינוחים מוכנים תוך דקות: מערכת אחת להכנת מגוון קינוחים בקלות: 7 מיני דונאטס, 7 מיני מאפינס, 12 קייק-פופס ו-4 וופלים בלגיים. אין צורך בהכנות מורכבות! פשוט מכניסים את הפלטות הרצויות, מחברים לחשמל ומתחילים לאפות.
ביצועים ועמידות ללא פשרות עוצמה חזקה: הספק עוצמתי של 1000 וואט המבטיח ביצועים גבוהים, עבודה מהירה ותוצאות מושלמות בכל שימוש. עמידות לאורך זמן: גוף המכשיר עשוי פלדת אל-חלד (נירוסטה) איכותית, הכוללת ציפוי צבע ייחודי בסגנון רטרו המעניק למטבח מראה יוקרתי ונוסטלגי.
פלטות נשלפות: המכשיר כולל פלטות ייעודיות ומתחלפות להכנת מיני דונאטס, מיני מאפינס ומיני וופל. הכל במכשיר אחד (All-In-One): מערכת מושלמת להכנת קינוחים שתופסת מקום מינימלי על השיש שלכם ומספקת תוצאות מקצועיות. ציפוי Non-Stick (מונע הידבקות): הפלטות הנשלפות מצופות בשכבת נון-סטיק איכותית המאפשרת הוצאה קלה של הקינוחים ושמירה על צורתם. הפלטות נשלפות בקלות ובטוחות לשטיפה במדיח הכלים לניקוי מהיר וללא מאמץ.
---סוף דוגמא---

קיבלת את הטקסט האנגלי הבא מאריזת המוצר:
{packaging_text}

כתוב תוכן שיווקי בעברית לאתר בדיוק באותו מבנה וסגנון של הדוגמא.
המבנה:
1. שורת כותרת ראשית: [תיאור מוצר בעברית] + [שם המוצר באנגלית] + מבית [שם המותג]
2. [שם מוצר באנגלית] + כותרת משנה קליטה + תיאור ראשי: הסבר מה המוצר עושה, פירוט יתרונות מרכזיים ואופן שימוש פשוט. הכל בפסקה אחת רציפה וזורמת.
3. פסקת ביצועים ועמידות: עוצמה (ואט), חומרי גוף (נירוסטה/פלסטיק), עיצוב ומראה.
4. פסקת תכונות עיקריות: אביזרים/פלטות נשלפים, All-In-One, ציפוי Non-Stick, קלות ניקוי ושטיפה במדיח.

כללים חשובים:
- שמור על אותו טון שיווקי נלהב ומקצועי כמו בדוגמא
- השתמש במונחים עבריים מקצועיים (פלדת אל-חלד, נון-סטיק, הספק וכו׳)
- אם יש מפרט טכני באנגלית – תרגם ושלב בצורה טבעית
- אל תמציא מפרט שלא מופיע בטקסט המקורי
- החזר רק את הטקסט השיווקי, בלי הסברים נוספים
"""

# ─────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────

def extract_images_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """Extract all significant raster images from PDF using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    seen_xrefs = set()

    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                pix = fitz.Pixmap(doc, xref)
                # Skip tiny images (icons, masks, etc.)
                if pix.width < 400 or pix.height < 400:
                    pix = None
                    continue
                # Convert CMYK / non-RGB to RGB
                if pix.n - pix.alpha > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                img_bytes = pix.tobytes("jpeg")
                images.append({
                    "xref": xref,
                    "width": pix.width,
                    "height": pix.height,
                    "bytes": img_bytes,
                })
                pix = None
            except Exception:
                continue

    # Sort by area descending (largest first)
    images.sort(key=lambda x: x["width"] * x["height"], reverse=True)
    return images


def _compress_jpeg(raw_bytes: bytes, max_width: int = 1500, quality: int = 75) -> bytes:
    """Resize to max_width (keeping aspect ratio) and re-encode as JPEG."""
    img = Image.open(io.BytesIO(raw_bytes))
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def rasterize_pdf_page(pdf_bytes: bytes, page: int = 1, dpi: int = 100) -> bytes:
    """Rasterize a PDF page to JPEG bytes. Tries pdftoppm, falls back to PyMuPDF."""
    raw = None
    # Try pdftoppm first (better quality)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "input.pdf")
            out_prefix = os.path.join(tmpdir, "page")
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            subprocess.run(
                ["pdftoppm", "-jpeg", "-r", str(dpi), "-f", str(page), "-l", str(page), pdf_path, out_prefix],
                check=True, capture_output=True,
            )
            files = sorted(Path(tmpdir).glob("page-*.jpg"))
            if files:
                raw = files[0].read_bytes()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass  # pdftoppm not installed or failed — use PyMuPDF

    if raw is None:
        # Fallback: PyMuPDF rasterization
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_obj = doc[page - 1]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page_obj.get_pixmap(matrix=mat)
        raw = pix.tobytes("jpeg")

    return _compress_jpeg(raw)


def extract_packaging_text(client: anthropic.Anthropic, page_jpegs: list[bytes]) -> str:
    """Use Claude Vision to extract all marketing text from packaging images (all pages)."""
    content = []
    for jpeg in page_jpegs:
        b64 = base64.standard_b64encode(jpeg).decode()
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
    content.append({"type": "text", "text": (
        "These are images of product packaging (one or more sides/pages). "
        "Extract ALL the English marketing text you can see from ALL images. "
        "Include every feature description, benefit, specification, and marketing claim. "
        "Preserve the hierarchy (headers and their details). "
        "Ignore barcodes, copyright notices, and pure logo text. "
        "Return structured plain text, combining text from all images into one coherent document."
    )})
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
    )
    return msg.content[0].text


def generate_hebrew_content(client: anthropic.Anthropic, packaging_text: str, style: str = "long", user_notes: str = "") -> str:
    """Use Claude to turn extracted text into Hebrew website copy.
    style = 'long'  → full 4-paragraph template (default)
    style = 'short' → minimalistic summary with bullets
    user_notes      → optional free-text user emphasis/instructions."""
    notes_block = ""
    if user_notes.strip():
        notes_block = f"\n\n=== הערות חשובות מהמזמין (קח אותן בחשבון בכתיבה) ===\n{user_notes.strip()}\n===\n"

    if style == "short":
        prompt = f"""מתוך טקסט האריזה באנגלית, כתוב תוכן שיווקי **מינימליסטי** בעברית לאתר איקומרס.

טקסט האריזה:
{packaging_text}
{notes_block}
המבנה:
1. שורת כותרת ראשית: תיאור המוצר + מותג
2. פסקה קצרה (3-4 משפטים) על מה המוצר עושה ויתרונותיו העיקריים
3. 3-4 bullets על התכונות הבולטות ביותר

טון שיווקי מקצועי, תמציתי. החזר רק את הטקסט בעברית, בלי הסברים."""
    else:
        prompt = MARKETING_TEMPLATE.format(packaging_text=packaging_text) + notes_block

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    """Return number of pages in a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return len(doc)


def resize_to_square(img_bytes: bytes, size: int | None = None) -> bytes:
    """Crop image to center square and resize. If size is None, keep original resolution."""
    img = Image.open(io.BytesIO(img_bytes))
    # Crop to center square
    side = min(img.width, img.height)
    left = (img.width - side) // 2
    top = (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side))
    # Resize if specific size requested
    if size and img.width != size:
        img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def remove_background(img_bytes: bytes) -> bytes:
    """Remove background using rembg. Returns PNG bytes with transparency."""
    from rembg import remove
    result = remove(img_bytes)
    return result


def is_product_image(client: anthropic.Anthropic, img_bytes: bytes) -> bool:
    """Use Claude Vision to decide if an image is a clean product shot worth keeping.
    Filters out: designer PSD mockups, instructional diagrams, small logos/icons,
    images with overlaid instructional text, multi-product collages."""
    # Compress to keep API cost low
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    if max(img.size) > 800:
        ratio = 800 / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    b64 = base64.standard_b64encode(buf.getvalue()).decode()

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": (
                    "Is this a clean product photograph suitable for use on an e-commerce website? "
                    "Reply NO if the image contains: overlaid instructional text like 'PSD', 'TRANSPARENT', 'MOCKUP'; "
                    "visible arrows or step-by-step diagrams; checkered transparency background; icons/logos only; "
                    "or a mosaic/collage of many different products. "
                    "Reply YES if it's a professional product shot, a clean food/lifestyle photo, or a clean product-in-use shot. "
                    "Reply with only the single word YES or NO."
                )},
            ],
        }],
    )
    answer = msg.content[0].text.strip().upper()
    return answer.startswith("Y")


PRODUCT_PRESERVATION_RULES = (
    "ABSOLUTE PRODUCT INTEGRITY RULES (most important - do not violate): "
    "The product in your output image MUST be a perfect pixel-accurate match to the reference photos. "
    "Same exact shape, same exact color, same exact number of pieces, same handles, same lid, same proportions, "
    "same material finish, same surface details, same branding/logos. "
    "DO NOT add, remove, replace, or modify any element of the product itself - not even slightly. "
    "DO NOT invent extra handles, parts, accessories, or components that are not visible in the references. "
    "DO NOT swap the product for a generic look-alike from your training data. "
    "Treat the reference photos as a template that must be reproduced exactly. "
    "Your ONLY creative freedom is in the SCENE AROUND the product (background, lighting, props, food styling)."
)

# Intentionally minimal - we let Gemini choose the scene freely to maximize product fidelity.
# The preservation rules appear FIRST in the final prompt (they get higher attention weight).
MINIMAL_ATMOSPHERE_PROMPT = (
    "Create a beautiful professional lifestyle product photograph of the item shown in the reference images. "
    "You decide the scene, lighting, and composition - whatever makes the product look its most appealing "
    "in a natural setting suitable for a premium e-commerce website."
)


FALLBACK_TAGLINES = [
    "איכות יוצאת דופן",
    "עיצוב ללא פשרות",
    "מצטיין בכל מטבח",
    "חוויית שימוש מושלמת",
    "מקצועיות בכל פרט",
    "פשוט לאהוב",
]


def analyze_image_for_strip(client: anthropic.Anthropic, image_bytes: bytes, hebrew_content: str, used_taglines: list[str], user_notes: str = "") -> dict:
    """Ask Claude Vision to pick a Hebrew tagline + strip styling for the given atmosphere image.
    Uses a deliberately SHORT prompt to keep Claude's Hebrew output clean."""
    b64 = base64.standard_b64encode(image_bytes).decode()
    # Keep context compact - long context was causing Claude to produce garbled Hebrew.
    short_content = (hebrew_content or "").strip()
    if len(short_content) > 600:
        short_content = short_content[:600] + "..."
    short_notes = (user_notes or "").strip()
    if len(short_notes) > 200:
        short_notes = short_notes[:200] + "..."

    used_str = " / ".join(used_taglines) if used_taglines else "(none)"

    prompt = f"""Look at this product lifestyle photo. Pick a short Hebrew marketing tagline for it.

Product marketing copy (for context only):
{short_content}

User emphasis (optional):
{short_notes}

Already used taglines (avoid repeating): {used_str}

RETURN FORMAT: JSON object with these exact keys:
- "tagline": Hebrew text, 3 to 6 words MAX, 30 characters MAX. ONE simple phrase. NO commas, NO pipes, NO dashes, NO separators. Must be real Hebrew words forming a meaningful phrase.
- "strip_position": "top" if product is in lower half of image, "bottom" if product is in upper half, else "bottom"
- "strip_color": "#RRGGBB" - deep color that contrasts the image
- "text_color": "#RRGGBB" - white on dark strips, dark on light

Output ONLY the JSON, no other text. Example: {{"tagline":"איכות יוצאת דופן","strip_position":"bottom","strip_color":"#8B0000","text_color":"#FFFFFF"}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        raw_tagline = data.get("tagline", "")
        tagline = _sanitize_tagline(raw_tagline)
        # If tagline looks like gibberish (not valid Hebrew), use a fallback not yet used
        if _looks_like_gibberish(tagline):
            tagline = _pick_fallback_tagline(used_taglines)
        return {
            "tagline": tagline,
            "strip_position": data.get("strip_position", "bottom"),
            "strip_color": data.get("strip_color", "#8B0000"),
            "text_color": data.get("text_color", "#FFFFFF"),
            "strip_height_ratio": float(data.get("strip_height_ratio", 0.12)),
        }
    except Exception:
        return {"tagline": _pick_fallback_tagline(used_taglines), "strip_position": "bottom", "strip_color": "#8B0000", "text_color": "#FFFFFF", "strip_height_ratio": 0.12}


def _pick_fallback_tagline(used: list[str]) -> str:
    for t in FALLBACK_TAGLINES:
        if t not in used:
            return t
    return FALLBACK_TAGLINES[0]


def _looks_like_gibberish(text: str) -> bool:
    """Heuristic: real Hebrew marketing phrases contain common function words/patterns.
    Gibberish has random letter combinations that don't form real words."""
    if not text or len(text) < 4:
        return True
    # Common Hebrew particles/words - at least one should appear in a real tagline
    common_markers = [
        "של", "את", "על", "עם", "ב", "ל", "לכל", "יותר", "מעל", "הכל",
        "איכות", "עיצוב", "מקצוע", "חזק", "קל", "פשוט", "מושלם", "מעולה",
        "לנוחות", "לאורך", "בכל", "גדול", "קטן", "חדש", "טוב", "מהיר",
        "חכם", "חסכון", "יעיל", "מדויק", "אמין", "מיוחד", "ייחודי", "נקי",
        "חם", "קר", "רך", "עוצמה", "ביצועים", "טכנולוגיה", "חדשנות",
    ]
    for marker in common_markers:
        if marker in text:
            return False
    return True


def _sanitize_tagline(raw: str) -> str:
    """Defensive cleanup so the strip drawing never chokes on a bad tagline."""
    if not raw:
        return "איכות יוצאת דופן"
    t = raw.strip().strip('"').strip("'").strip()
    # Strip at ANY separator - keep only first segment
    for sep in (",", "|", "·", ";", "\n", "•", " - ", " – ", " — ", " / "):
        if sep in t:
            t = t.split(sep)[0].strip()
    # Cap word count
    words = t.split()
    if len(words) > 6:
        words = words[:6]
        t = " ".join(words)
    # Cap character length - truncate at last word boundary under 30 chars
    if len(t) > 30:
        out = ""
        for w in t.split():
            if len(out) + len(w) + 1 > 30:
                break
            out = (out + " " + w).strip()
        t = out or t[:30]
    return t or "איכות יוצאת דופן"


def _unused_generate_feature_scenes(client: anthropic.Anthropic, packaging_text: str, hebrew_content: str) -> list[dict]:
    """Return 4 {tagline, scene_prompt} pairs - features-first design.
    Each tagline is a key product strength in Hebrew, and each scene_prompt tells
    Gemini to VISUALIZE that specific strength, guaranteeing text-image alignment."""
    prompt = f"""You are a creative director for a premium kitchen appliance brand (Food Appeal).

Product info (English text from packaging):
{packaging_text}

Hebrew marketing copy:
{hebrew_content}

## Your task

Identify the 4 STRONGEST selling points / features / strengths of this product from the marketing copy above, and for each one, design a lifestyle image that VISUALLY PROVES that strength.

Output 4 items. Each item has:
1. **tagline** (Hebrew, 3-6 words): the feature/strength/benefit written as a punchy marketing headline.
2. **scene_prompt** (English, 2-4 sentences): a photography-style prompt that tells an AI image generator how to create a lifestyle photo that VISUALLY DEMONSTRATES that specific tagline.

## Rules for image-text alignment

The image MUST visually show what the tagline says:
- Tagline about CAPACITY → image must show the product FULL of food, brimming with ingredients
- Tagline about NON-STICK → image must show food cooking cleanly or being easily flipped/lifted
- Tagline about STACKING / SPACE SAVING → image must show the pieces nested/stacked
- Tagline about FOLDING HANDLES → image must explicitly show a handle being folded or compacted
- Tagline about ALL STOVETOPS → image must show the product ON a stovetop (induction/gas)
- Tagline about ACCESSORIES → image must show the accessories clearly
- Tagline about POWER / SPEED → image must show steam, sizzling, or active cooking
- Tagline about DESIGN / AESTHETICS → image must show a styled kitchen shot

## Rules for scene_prompt

Each scene_prompt should include:
- Where the product is placed (kitchen counter, stovetop, dining table...)
- Lighting (warm morning light, soft overhead, golden hour...)
- Relevant food styling (ingredients that make sense for THIS appliance)
- Composition (3/4 angle, close-up, top-down...)

Every scene_prompt MUST end with this exact preservation text: "{PRODUCT_PRESERVATION_RULES}"

## Variety requirement

Pick 4 DIFFERENT strengths - don't make 2 taglines about the same feature.
Taglines must be natural Hebrew, like real product ads.

## Output format

Respond with ONLY valid JSON array, nothing else:
[
  {{"tagline": "משפט בעברית", "scene_prompt": "English scene prompt..."}},
  {{"tagline": "משפט בעברית", "scene_prompt": "English scene prompt..."}},
  {{"tagline": "משפט בעברית", "scene_prompt": "English scene prompt..."}},
  {{"tagline": "משפט בעברית", "scene_prompt": "English scene prompt..."}}
]"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Strip markdown code fence if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def extract_marketing_taglines(client: anthropic.Anthropic, hebrew_content: str) -> list[str]:
    """Use Claude to extract 4 short Hebrew marketing taglines."""
    prompt = f"""מתוך הטקסט השיווקי הבא, חלץ 4 משפטי שיווק קצרים וקליטים (3-6 מילים כל אחד) שיתאימו להצגה כפס שיווקי על תמונת מוצר.

כל משפט צריך:
- להיות קצר ומרשים
- להדגיש תכונה/יתרון מרכזי
- להיות שונה מהשאר

טקסט שיווקי:
{hebrew_content}

החזר רק JSON array של 4 מחרוזות בעברית, בלי שום הסבר נוסף:
["משפט 1", "משפט 2", "משפט 3", "משפט 4"]"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def generate_atmosphere_image(
    gemini_client,
    product_img_bytes_list: list[bytes],
    scene_template_bytes: bytes | None = None,
    prompt: str = MINIMAL_ATMOSPHERE_PROMPT,
    user_notes: str = "",
) -> bytes:
    """Generate a lifestyle image using Gemini 2.5 Flash Image.
    product_img_bytes_list: the actual product photos - must be preserved pixel-accurate.
    scene_template_bytes: OPTIONAL single reference image used as a SCENE TEMPLATE.
        When provided, Gemini reproduces the reference's scene/composition/lighting/angle
        but swaps the product visible in it for our product.
    user_notes: optional user instructions/emphasis to steer the atmosphere."""
    from google.genai import types as gen_types
    product_imgs = [Image.open(io.BytesIO(b)) for b in product_img_bytes_list]
    template_img = Image.open(io.BytesIO(scene_template_bytes)) if scene_template_bytes else None

    if template_img is not None:
        full_prompt = (
            PRODUCT_PRESERVATION_RULES + "\n\n"
            f"The first {len(product_imgs)} images show OUR PRODUCT — the only product allowed in your output. "
            "Preserve it pixel-accurately: shape, color, handles, lid, branding, proportions, finish — all exact.\n\n"
            "The LAST image is a SCENE TEMPLATE. You will use ONLY its scene, NOT its product.\n\n"
            "## What to COPY from the scene template:\n"
            "- The setting / environment / background\n"
            "- Camera angle, framing, distance, perspective\n"
            "- Lighting style, direction, color temperature, shadows\n"
            "- Mood, atmosphere, color palette\n"
            "- Surfaces, props, hands, food, garnishes, utensils — everything EXCEPT the product itself\n"
            "- The position, scale, and orientation that the template's product occupies in the frame\n\n"
            "## What is FORBIDDEN — must NOT appear in your output:\n"
            "- The product visible in the scene template. It is forbidden. Do not draw it. Do not keep it. "
            "Do not put it next to OUR product. Do not include both products. There is only ONE product in the output, and it is OURS.\n"
            "- Any text, captions, logos, watermarks, banners, marketing strips, badges, or overlays from the template.\n\n"
            "## What to DO:\n"
            "Reconstruct the template's scene from scratch, but with OUR product placed exactly where the template's product was — "
            "same spot, same scale, same orientation. Hands holding the template's product? Hands now hold OUR product. "
            "Template's product on a stove? OUR product is now on that stove. Template's product being washed in a sink? "
            "OUR product is now being washed in that sink. Replace, do not add.\n\n"
            "Final check before finishing: count the products in your output. There must be exactly ONE, and it must match "
            "the first reference images (OUR product), not the template's product."
        )
    else:
        full_prompt = PRODUCT_PRESERVATION_RULES + "\n\n" + prompt

    if user_notes.strip():
        full_prompt += (
            "\n\nAdditional user instructions for this image (follow these, but never at the cost of product preservation):\n"
            f"{user_notes.strip()}"
        )

    config = gen_types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])
    contents = [full_prompt, *product_imgs]
    if template_img is not None:
        contents.append(template_img)

    last_err = None
    for model_name in (
        "gemini-2.5-flash-image",
        "gemini-2.5-flash-image-preview",
    ):
        try:
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            parts = response.candidates[0].content.parts if response.candidates else []
            for part in parts:
                if part.inline_data is not None:
                    raw = part.inline_data.data
                    img = Image.open(io.BytesIO(raw))
                    side = min(img.width, img.height)
                    left = (img.width - side) // 2
                    top = (img.height - side) // 2
                    img = img.crop((left, top, left + side, top + side))
                    if img.width != 900:
                        img = img.resize((900, 900), Image.LANCZOS)
                    buf = io.BytesIO()
                    img.convert("RGB").save(buf, format="JPEG", quality=92)
                    return buf.getvalue()
            last_err = RuntimeError(f"{model_name}: no image in response. Text: {response.text or '(empty)'}")
        except Exception as e:
            last_err = e
    raise last_err if last_err else RuntimeError("Unknown Gemini error")


def analyze_strip_placement(client: anthropic.Anthropic, image_bytes: bytes) -> dict:
    """Ask Claude Vision to choose strip position, color, and text color for an image."""
    b64 = base64.standard_b64encode(image_bytes).decode()
    prompt = """Analyze this product lifestyle image and decide where to place a marketing text strip.

Rules:
- If the main product is in the UPPER half, place the strip at the BOTTOM. If in the LOWER half, place at the TOP. If centered, prefer BOTTOM.
- Pick a strip_color that harmonizes with or boldly contrasts the dominant image colors, similar to premium product ads. Deep reds, dark navy, forest green, warm black, or a tone matching the product's dominant color usually work well.
- text_color must be highly readable on the strip (white on dark strips, dark on light strips).
- strip_height_ratio should be 0.10-0.14.

Respond with ONLY valid JSON, nothing else:
{"strip_position": "top" or "bottom", "strip_color": "#RRGGBB", "text_color": "#RRGGBB", "strip_height_ratio": 0.12}"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        return {
            "strip_position": data.get("strip_position", "bottom"),
            "strip_color": data.get("strip_color", "#8B0000"),
            "text_color": data.get("text_color", "#FFFFFF"),
            "strip_height_ratio": float(data.get("strip_height_ratio", 0.12)),
        }
    except Exception:
        return {"strip_position": "bottom", "strip_color": "#8B0000", "text_color": "#FFFFFF", "strip_height_ratio": 0.12}


def extract_strip_text_from_reference(client: anthropic.Anthropic, ref_bytes: bytes) -> str:
    """If the reference image already has a marketing strip/banner with Hebrew text on it,
    return that text. Otherwise return ''."""
    img = Image.open(io.BytesIO(ref_bytes)).convert("RGB")
    if max(img.size) > 800:
        ratio = 800 / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.standard_b64encode(buf.getvalue()).decode()

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": (
                    "Does this image contain a marketing strip or banner (a colored bar at the top or bottom) "
                    "with Hebrew marketing text on it? "
                    "If YES → reply with ONLY the Hebrew text from that strip, exactly as written, no quotes, no prefix, no explanation. "
                    "If NO (no strip, or strip without Hebrew text) → reply with ONLY the single word: NONE"
                )},
            ],
        }],
    )
    text = msg.content[0].text.strip().strip('"').strip("'").strip()
    if text.upper() == "NONE" or len(text) < 3:
        return ""
    return text


def validate_atmosphere_image(
    client: anthropic.Anthropic,
    output_bytes: bytes,
    product_ref_bytes: bytes,
    scene_template_bytes: bytes | None,
) -> dict:
    """Use Claude Vision to verify that the generated atmosphere shows OUR product
    (matching the product reference) and — if a scene template was used — does NOT
    show the template's original product. Returns {"ok": bool, "reason": str}."""
    def _b64(b: bytes, max_dim: int = 700) -> str:
        img = Image.open(io.BytesIO(b)).convert("RGB")
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return base64.standard_b64encode(buf.getvalue()).decode()

    content = [
        {"type": "text", "text": "Image A — OUR product (the product that MUST appear in the output, matching shape/color/branding):"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _b64(product_ref_bytes)}},
    ]
    if scene_template_bytes:
        content += [
            {"type": "text", "text": "Image B — SCENE TEMPLATE. Only its scene/environment/composition should be reproduced. Its product is FORBIDDEN in the output:"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _b64(scene_template_bytes)}},
        ]
    content += [
        {"type": "text", "text": "Image C — GENERATED OUTPUT under review:"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _b64(output_bytes)}},
    ]

    if scene_template_bytes:
        instruction = (
            "Review image C. Decide:\n"
            '1. "product_match": Does C clearly show OUR product (matching A in shape, color, handles, lid, branding)? Answer true/false.\n'
            '2. "template_product_absent": Is the product from B absent from C? (true if only OUR product is visible, '
            'false if B\'s product is still in C, or if both products appear together)\n'
            '3. "scene_match": Does C reproduce B\'s scene/setting/composition reasonably (same kind of environment/angle/mood)? Answer true/false.\n'
            'Return ONLY a JSON object: {"product_match": bool, "template_product_absent": bool, "scene_match": bool, "reason": "<one short sentence>"}'
        )
    else:
        instruction = (
            "Review image C. Decide:\n"
            '1. "product_match": Does C clearly show OUR product (matching A in shape, color, handles, lid, branding)? Answer true/false.\n'
            '2. "professional_quality": Does C look like a professional lifestyle/marketing photograph (good lighting, composition, no obvious AI artifacts)? Answer true/false.\n'
            'Return ONLY a JSON object: {"product_match": bool, "professional_quality": bool, "reason": "<one short sentence>"}'
        )
    content.append({"type": "text", "text": instruction})

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": content}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        if scene_template_bytes:
            ok = bool(data.get("product_match")) and bool(data.get("template_product_absent")) and bool(data.get("scene_match"))
        else:
            ok = bool(data.get("product_match")) and bool(data.get("professional_quality"))
        return {"ok": ok, "reason": data.get("reason", "")}
    except Exception:
        return {"ok": True, "reason": "validator parse error - skipped"}


def _measure_text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    l, _, r, _ = draw.textbbox((0, 0), text, font=font)
    return r - l


def _split_two_lines(text: str) -> list[str]:
    """Split text into two roughly-equal lines at the closest word boundary."""
    words = text.split()
    if len(words) < 2:
        return [text]
    target = len(text) / 2
    best_i, best_diff = 1, float("inf")
    for i in range(1, len(words)):
        diff = abs(len(" ".join(words[:i])) - target)
        if diff < best_diff:
            best_diff, best_i = diff, i
    return [" ".join(words[:best_i]), " ".join(words[best_i:])]


def draw_marketing_strip(image_bytes: bytes, tagline: str, placement: dict) -> bytes:
    """Draw a colored strip with Hebrew tagline on top/bottom of the image.
    Auto-fits the text: shrinks the font to fit; falls back to two lines if even
    the smallest font won't fit on a single line."""
    from bidi.algorithm import get_display

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    W, H = img.size
    strip_h = int(H * placement["strip_height_ratio"])
    pos = placement["strip_position"]

    max_text_width = int(W * 0.92)
    initial_font_size = int(strip_h * 0.55)
    min_font_size = max(14, int(strip_h * 0.30))
    draw = ImageDraw.Draw(img)

    # Try single line, shrinking font down to min
    display_text = get_display(tagline)
    one_line_size = None
    for size in range(initial_font_size, min_font_size - 1, -2):
        font = _load_font(size)
        if _measure_text_width(draw, display_text, font) <= max_text_width:
            one_line_size = size
            break

    if one_line_size is not None:
        lines = [display_text]
        font_size = one_line_size
    else:
        # Wrap to two lines and pick a font size that fits both within max width
        raw_lines = _split_two_lines(tagline)
        if len(raw_lines) == 1:
            lines = [display_text]
            font_size = min_font_size
        else:
            lines = [get_display(line) for line in raw_lines]
            two_line_max = int(strip_h * 0.42)
            font_size = max(12, min_font_size)
            for size in range(two_line_max, 11, -2):
                font = _load_font(size)
                widths = [_measure_text_width(draw, line, font) for line in lines]
                if max(widths) <= max_text_width:
                    font_size = size
                    break

    font = _load_font(font_size)

    if pos == "top":
        strip_box = (0, 0, W, strip_h)
    else:
        strip_box = (0, H - strip_h, W, H)
    draw.rectangle(strip_box, fill=placement["strip_color"])

    line_height = int(font_size * 1.15)
    total_text_height = line_height * len(lines) - int(font_size * 0.15)
    if pos == "top":
        y_start = (strip_h - total_text_height) // 2
    else:
        y_start = (H - strip_h) + (strip_h - total_text_height) // 2

    for idx, line in enumerate(lines):
        l, t, r, b = draw.textbbox((0, 0), line, font=font)
        tw = r - l
        x = (W - tw) // 2 - l
        y = y_start + idx * line_height - t
        draw.text((x, y), line, font=font, fill=placement["text_color"])

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def generate_hebrew_from_images(client: anthropic.Anthropic, img_bytes_list: list[bytes], style: str = "short", user_notes: str = "") -> str:
    """Generate Hebrew marketing copy from one or more product images.
    style = 'short' → minimalistic (1-2 sentences + bullets)
    style = 'long'  → detailed multi-paragraph copy (like from packaging PDF)
    user_notes      → optional user emphasis/instructions."""
    content_blocks = []
    for raw in img_bytes_list:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        if max(img.size) > 1200:
            ratio = 1200 / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.standard_b64encode(buf.getvalue()).decode()
        content_blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})

    if style == "long":
        instruction = (
            f"קיבלת {len(img_bytes_list)} תמונות של אותו מוצר חשמלי למטבח (המוצר עצמו + אביזרים נלווים / זוויות שונות). "
            "למד על המוצר מכל התמונות יחד וכתוב תוכן שיווקי **מפורט וארוך** בעברית לאתר איקומרס.\n\n"
            "המבנה (3-4 פסקאות):\n"
            "1. שורת כותרת ראשית: תיאור המוצר + שם/מותג אם נראה\n"
            "2. פסקה ראשית: מה המוצר עושה, יתרונות מרכזיים, אופן שימוש - פסקה רציפה וזורמת\n"
            "3. פסקת ביצועים ועמידות: חומרים, עיצוב, איכות בנייה (רק מה שרואים)\n"
            "4. פסקת תכונות: אביזרים נלווים (אם יש בתמונות!), עיצוב, קלות תפעול\n\n"
            "טון שיווקי נלהב ומקצועי, כמו פרסומת אמיתית. "
            "אם אתה רואה אביזרים נלווים (מסננות, תוספות, כיסויים) - הזכר אותם. "
            "אל תמציא מפרט טכני שאתה לא רואה. החזר רק את הטקסט השיווקי בעברית."
        )
    else:  # short
        instruction = (
            f"קיבלת {len(img_bytes_list)} תמונות של אותו מוצר חשמלי למטבח. "
            "למד על המוצר מכל התמונות יחד וכתוב תוכן שיווקי **מינימליסטי** בעברית.\n\n"
            "המבנה:\n"
            "1. שורת כותרת ראשית: סוג המוצר + שם/מותג אם נראה\n"
            "2. פסקה קצרה (3-4 משפטים) על מה המוצר עושה ויתרונותיו\n"
            "3. 3-4 bullets על תכונות בולטות (חומרים, עיצוב, שימושיות, אביזרים אם יש)\n\n"
            "טון שיווקי מקצועי אך קצר ותמציתי. "
            "אם אתה רואה אביזרים נלווים בתמונות - הזכר אותם בקצרה. "
            "אל תמציא מפרט טכני שאתה לא רואה. החזר רק את הטקסט השיווקי בעברית."
        )
    if user_notes.strip():
        instruction += (
            f"\n\n=== הערות חשובות מהמזמין (קח אותן בחשבון בכתיבה) ===\n"
            f"{user_notes.strip()}\n===\n"
        )
    content_blocks.append({"type": "text", "text": instruction})

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000 if style == "long" else 800,
        messages=[{"role": "user", "content": content_blocks}],
    )
    return msg.content[0].text


def create_zip(images: list[dict], hebrew_text: str, bg_removed: bool = False,
               atmospheres_clean: list[bytes] | None = None,
               atmospheres_striped: list[bytes] | None = None) -> bytes:
    """Pack images + text file into a ZIP."""
    ext = "png" if bg_removed else "jpg"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("marketing_content_he.txt", hebrew_text.encode("utf-8"))
        for i, img in enumerate(images):
            zf.writestr(f"product_image_{i+1}.{ext}", img["bytes"])
        if atmospheres_clean:
            for i, b in enumerate(atmospheres_clean):
                zf.writestr(f"atmosphere_clean_{i+1}.jpg", b)
        if atmospheres_striped:
            for i, b in enumerate(atmospheres_striped):
                zf.writestr(f"atmosphere_marketing_{i+1}.jpg", b)
    buf.seek(0)
    return buf.read()


def run_atmosphere_pipeline(
    *,
    client: anthropic.Anthropic,
    gemini_client,
    ref_bytes_list: list[bytes],
    scene_template_inputs: list,
    user_notes: str,
    hebrew_content: str,
    target_count: int = 4,
    enable_validator: bool = True,
    max_retries: int = 2,
) -> tuple[list[bytes], list[bytes]]:
    """End-to-end atmosphere image generation:
    1) Process scene-template uploads, OCR strip text from each as a tagline fallback.
    2) Build target_count generation tasks (cycle through templates if any, else generic).
    3) For each task: generate via Gemini, optionally validate via Claude Vision (retry up to max_retries).
    4) Apply marketing strip with priority: user-typed > OCR'd > auto-generated.
    Returns (atmospheres_clean, atmospheres_striped)."""
    atmospheres_clean: list[bytes] = []
    atmospheres_striped: list[bytes] = []
    if not gemini_client or not ref_bytes_list:
        return atmospheres_clean, atmospheres_striped

    # ── Step 1: ingest scene templates + OCR taglines if user didn't type one
    scene_templates: list[dict] = []
    if scene_template_inputs:
        with st.status("מעבד תמונות רפרנס...", expanded=False) as status:
            for idx, (ref_file, ref_tagline) in enumerate(scene_template_inputs):
                if ref_file is None:
                    continue
                sr_pil = Image.open(io.BytesIO(ref_file.read())).convert("RGB")
                if max(sr_pil.size) > 1200:
                    ratio = 1200 / max(sr_pil.size)
                    sr_pil = sr_pil.resize((int(sr_pil.width * ratio), int(sr_pil.height * ratio)), Image.LANCZOS)
                sb = io.BytesIO()
                sr_pil.save(sb, format="JPEG", quality=85)
                ref_bytes = sb.getvalue()

                effective_tagline = (ref_tagline or "").strip()
                if not effective_tagline:
                    status.update(label=f"קורא טקסט מהפס של רפרנס {idx+1}...")
                    try:
                        ocr = extract_strip_text_from_reference(client, ref_bytes)
                        if ocr:
                            effective_tagline = ocr
                    except Exception:
                        pass

                scene_templates.append({"img_bytes": ref_bytes, "tagline": effective_tagline})
            status.update(label=f"{len(scene_templates)} רפרנסים מוכנים", state="complete")

    # ── Step 2: build generation tasks (always target_count)
    tasks: list[dict] = []
    if scene_templates:
        n = len(scene_templates)
        for i in range(target_count):
            tpl = scene_templates[i % n]
            tasks.append({"scene_template_bytes": tpl["img_bytes"], "tagline": tpl["tagline"]})
    else:
        for _ in range(target_count):
            tasks.append({"scene_template_bytes": None, "tagline": ""})

    # ── Step 3: generate (with optional validator + retry)
    user_taglines_per_atm: list[str] = []
    errors: list[str] = []
    intro = (
        f"מייצר {target_count} תמונות אווירה ({len(scene_templates)} רפרנסים, מסבב ביניהם)..."
        if scene_templates else
        f"מייצר {target_count} תמונות אווירה גנריות..."
    )
    with st.status(intro, expanded=True) as status:
        for i, task in enumerate(tasks):
            src_label = "תבנית סצנה" if task["scene_template_bytes"] else "גנרי"
            attempt = 0
            chosen_atm: bytes | None = None
            last_atm: bytes | None = None
            last_reason = ""
            while attempt <= max_retries:
                attempt += 1
                status.update(label=f"מייצר תמונה {i+1}/{target_count} ({src_label}) — ניסיון {attempt}...")
                try:
                    last_atm = generate_atmosphere_image(
                        gemini_client, ref_bytes_list,
                        scene_template_bytes=task["scene_template_bytes"],
                        user_notes=user_notes,
                    )
                except Exception as e:
                    errors.append(f"תמונה {i+1} (ניסיון {attempt}): {type(e).__name__}: {e}")
                    continue

                if not enable_validator:
                    chosen_atm = last_atm
                    break

                status.update(label=f"בודק איכות תמונה {i+1}/{target_count} (ניסיון {attempt})...")
                try:
                    result = validate_atmosphere_image(
                        client, last_atm, ref_bytes_list[0], task["scene_template_bytes"]
                    )
                except Exception as e:
                    errors.append(f"תמונה {i+1} (ולידציה): {type(e).__name__}: {e}")
                    chosen_atm = last_atm
                    break
                if result.get("ok"):
                    chosen_atm = last_atm
                    break
                last_reason = result.get("reason", "")
                # else: retry

            if chosen_atm is None and last_atm is not None:
                # All retries failed validation; keep the last attempt anyway and warn
                chosen_atm = last_atm
                if last_reason:
                    errors.append(f"תמונה {i+1}: עברה את כל הניסיונות אך הוולידטור התריע: {last_reason}")

            if chosen_atm is not None:
                atmospheres_clean.append(chosen_atm)
                user_taglines_per_atm.append(task["tagline"])
        status.update(label=f"נוצרו {len(atmospheres_clean)} תמונות אווירה", state="complete")

    for err in errors:
        st.warning(err)

    # ── Step 4: marketing strips
    if atmospheres_clean:
        with st.status("מתאים פסי שיווק...", expanded=True) as status:
            used_taglines: list[str] = []
            for i, atm in enumerate(atmospheres_clean):
                status.update(label=f"מתאים פס שיווקי לתמונה {i+1}/{len(atmospheres_clean)}...")
                user_tag = user_taglines_per_atm[i] if i < len(user_taglines_per_atm) else ""
                if user_tag:
                    placement = analyze_strip_placement(client, atm)
                    placement["tagline"] = user_tag
                else:
                    placement = analyze_image_for_strip(client, atm, hebrew_content, used_taglines, user_notes=user_notes)
                used_taglines.append(placement["tagline"])
                striped = draw_marketing_strip(atm, placement["tagline"], placement)
                atmospheres_striped.append(striped)
            status.update(label="פסי שיווק מוכנים!", state="complete")

    return atmospheres_clean, atmospheres_striped


# ─────────────────────────────────────────
#  UI
# ─────────────────────────────────────────

st.markdown("## 📦 Packaging Extractor")
st.markdown("העלה PDF של אריזת מוצר וקבל תמונות נקיות + תוכן שיווקי בעברית")

# ── API Key ──
with st.sidebar:
    st.markdown("### ⚙️ הגדרות")
    def _safe_secret(key: str) -> str:
        try:
            return st.secrets.get(key, "")
        except Exception:
            return ""

    default_key = _safe_secret("ANTHROPIC_API_KEY")
    if default_key:
        api_key = default_key
    else:
        api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")

    default_gemini = _safe_secret("GEMINI_API_KEY")
    if default_gemini:
        gemini_key = default_gemini
    else:
        gemini_key = st.text_input("Gemini API Key (אופציונלי)", type="password", placeholder="AIza...")
    st.markdown("---")
    st.markdown("**מה האפליקציה עושה:**")
    st.markdown("""
- 🖼️ שולפת תמונות מוצר נקיות מה-PDF
- 📝 קוראת את הטקסט האנגלי מהאריזה
- ✍️ ממירה לתוכן שיווקי בעברית
- 📥 מייצרת ZIP להורדה
    """)

# ── Upload ──
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="step-badge">1</span> העלאת קובץ</div>', unsafe_allow_html=True)

    upload_mode = st.radio(
        "סוג קלט",
        options=["PDF של אריזה", "תמונות מוצר"],
        horizontal=True,
    )

    if upload_mode == "PDF של אריזה":
        uploaded_files = st.file_uploader("גרור PDF של אריזת מוצר", type=["pdf"], label_visibility="collapsed", key="pdf_upl")
        # Normalize to a single file (keep the variable interface consistent)
        uploaded = uploaded_files
        upload_count = 1 if uploaded else 0
    else:
        uploaded_files = st.file_uploader(
            "גרור תמונות מוצר (אפשר כמה - למשל מוצר + אביזרים)",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
            accept_multiple_files=True,
            key="img_upl",
        )
        uploaded = uploaded_files if uploaded_files else None
        upload_count = len(uploaded_files) if uploaded_files else 0

    if uploaded:
        if upload_mode == "PDF של אריזה":
            st.success(f"✅ {uploaded.name} ({uploaded.size // 1024} KB)")
        else:
            st.success(f"✅ הועלו {upload_count} תמונות: " + ", ".join(f.name for f in uploaded_files))

        st.markdown('<div class="section-title">הגדרות</div>', unsafe_allow_html=True)

        # Text length selector
        default_text_idx = 0 if upload_mode == "PDF של אריזה" else 1
        text_style = st.radio(
            "אורך טקסט שיווקי",
            options=["ארוך ומפורט", "קצר ומינימליסטי"],
            index=default_text_idx,
            horizontal=True,
            help="ארוך = 3-4 פסקאות. קצר = פסקה + bullets",
        )

        image_size = st.radio(
            "גודל תמונות",
            options=["900x900", "גודל מקסימלי"],
            horizontal=True,
        )
        if upload_mode == "PDF של אריזה":
            remove_bg = st.checkbox("הסרת רקע (רקע שקוף)")
        else:
            remove_bg = False
        user_notes = st.text_area(
            "הערות משלך על המוצר (אופציונלי)",
            placeholder=(
                "למשל: 'תדגישו את הידית הארגונומית', 'זה מוצר פרימיום', "
                "'קהל היעד אמהות צעירות', 'תמונות אווירה עם מראה מינימליסטי', "
                "'אל תזכירו מפרט טכני', וכו'"
            ),
            height=100,
            help=(
                "כל מה שתכתוב כאן יילקח בחשבון: בטקסט השיווקי, בבחירת המשפטים לפסי השיווק, "
                "ובסגנון תמונות האווירה. אופציונלי - לא חובה למלא."
            ),
        )

        gen_atmospheres = st.checkbox("ייצר 4 תמונות אווירה (נקיות + עם פס שיווקי) (~$0.20 לקובץ)")

        enable_validator = True
        scene_template_inputs = []
        if gen_atmospheres:
            enable_validator = st.checkbox(
                "🔍 בדיקת איכות אוטומטית (Claude Vision מוודא שהמוצר הנכון בתמונה, עם retry של עד 2 ניסיונות אם לא)",
                value=True,
                help=(
                    "בכל תמונה Claude Vision בודק שהמוצר שלך מופיע בתמונה — ובמצב 'תעשה לי כזה' שגם המוצר של הרפרנס "
                    "אכן הוחלף ולא נשאר. אם הוולידציה נכשלת, התמונה מיוצרת מחדש (עד 2 פעמים נוספות). "
                    "מוסיף עלות קטנה אבל משפר משמעותית את האיכות."
                ),
            )
            with st.expander("🎯 מצב 'תעשה לי כזה' — תמונות רפרנס כתבנית סצנה (אופציונלי)", expanded=False):
                st.caption(
                    "אפשר להעלות עד 4 תמונות רפרנס. כשמועלים פחות מ-4, האפליקציה תסבב ביניהן עד שמייצרת 4 תמונות סך הכל. "
                    "אפשר לכתוב לכל תמונה משפט שיווקי משלך שיופיע על הפס. "
                    "אם הרפרנס כבר מכיל פס שיווקי בעברית, האפליקציה תקרא ממנו את הטקסט אוטומטית (כשלא הקלדת אחד משלך). "
                    "אם תשאיר את כל הסלוטים ריקים — ייוצרו 4 תמונות אווירה גנריות עם משפטי שיווק אוטומטיים."
                )
                for i in range(4):
                    st.markdown(f"**רפרנס {i+1}:**")
                    rc1, rc2 = st.columns([1, 1])
                    with rc1:
                        ref_file = st.file_uploader(
                            f"תמונת רפרנס {i+1}",
                            type=["jpg", "jpeg", "png", "webp"],
                            label_visibility="collapsed",
                            key=f"scene_ref_{i}",
                        )
                    with rc2:
                        ref_tagline = st.text_input(
                            f"משפט שיווקי {i+1}",
                            placeholder="משפט שיווקי לפס (אופציונלי)",
                            key=f"scene_tag_{i}",
                            label_visibility="collapsed",
                        )
                    scene_template_inputs.append((ref_file, ref_tagline))
                n_uploaded = sum(1 for f, _ in scene_template_inputs if f is not None)
                if n_uploaded:
                    st.success(f"✅ {n_uploaded} רפרנסים יומרו ל-{n_uploaded} תמונות אווירה לפי הסצנות שלהן")
                else:
                    st.info("📋 לא הועלו רפרנסים — ייוצרו 4 תמונות אווירה גנריות")

        run_btn = st.button("🚀 עבד", use_container_width=True)
    else:
        run_btn = False
        text_style = "ארוך ומפורט"
        user_notes = ""
        st.info("📂 ממתין לקובץ...")
    st.markdown('</div>', unsafe_allow_html=True)

# ── Process ──
if run_btn and uploaded:
    if not api_key:
        st.error("הכנס Anthropic API Key בסרגל השמאלי")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)
    # PDF mode has a single UploadedFile; image mode has a list
    if upload_mode == "PDF של אריזה":
        file_bytes = uploaded.read()
        display_filename = uploaded.name
    else:
        all_image_bytes = [f.read() for f in uploaded_files]
        display_filename = Path(uploaded_files[0].name).stem + "_multi"

    style_arg = "long" if text_style == "ארוך ומפורט" else "short"

    try:
     if upload_mode == "תמונות מוצר":
        # === MULTI-IMAGE MODE ===
        with col1:
            with st.status(f"מעבד {len(all_image_bytes)} תמונות...", expanded=True) as status:
                target_size = 900 if image_size == "900x900" else None
                images = []
                for i, raw in enumerate(all_image_bytes):
                    resized = resize_to_square(raw, target_size)
                    pil = Image.open(io.BytesIO(resized))
                    images.append({"bytes": resized, "width": pil.width, "height": pil.height, "xref": i})
                status.update(label=f"{len(images)} תמונות מעובדות", state="complete")

            with st.status(f"מייצר תוכן שיווקי ({text_style}) בעברית מכל התמונות...", expanded=True) as status:
                hebrew_content = generate_hebrew_from_images(client, [img["bytes"] for img in images], style=style_arg, user_notes=user_notes)
                status.update(label="תוכן שיווקי מוכן!", state="complete")

            packaging_text = ""
            num_pages = 0
            bg_removed = False

            # Atmosphere images
            atmospheres_clean = []
            atmospheres_striped = []
            if gen_atmospheres:
                if not gemini_key:
                    st.warning("צריך Gemini API Key כדי לייצר תמונות אווירה")
                else:
                    try:
                        from google import genai as google_genai
                        gemini_client = google_genai.Client(api_key=gemini_key)
                        ref_bytes_list = []
                        for img in images[:3]:
                            ref_pil = Image.open(io.BytesIO(img["bytes"])).convert("RGB")
                            rb = io.BytesIO()
                            ref_pil.save(rb, format="JPEG", quality=92)
                            ref_bytes_list.append(rb.getvalue())

                        atmospheres_clean, atmospheres_striped = run_atmosphere_pipeline(
                            client=client,
                            gemini_client=gemini_client,
                            ref_bytes_list=ref_bytes_list,
                            scene_template_inputs=scene_template_inputs,
                            user_notes=user_notes,
                            hebrew_content=hebrew_content,
                            target_count=4,
                            enable_validator=enable_validator,
                        )
                    except Exception as e:
                        st.warning(f"כשל בייצור תמונות אווירה: {e}")

        st.session_state["results"] = {
            "images": images,
            "packaging_text": packaging_text,
            "hebrew_content": hebrew_content,
            "filename": display_filename,
            "bg_removed": bg_removed,
            "atmospheres_clean": atmospheres_clean,
            "atmospheres_striped": atmospheres_striped,
        }

     else:
        # === PDF MODE (original flow) ===
        pdf_bytes = file_bytes
        with col1:
            # Step 1 – Extract images
            with st.status("שולף תמונות מה-PDF...", expanded=True) as status:
                raw_images = extract_images_from_pdf(pdf_bytes)
                status.update(label=f"נמצאו {len(raw_images)} תמונות, מסנן...")

                # Filter out non-product images using Claude Vision (PSD mockups, diagrams, etc.)
                images = []
                for i, img in enumerate(raw_images):
                    status.update(label=f"מסנן תמונות ({i+1}/{len(raw_images)})...")
                    try:
                        if is_product_image(client, img["bytes"]):
                            images.append(img)
                    except Exception:
                        images.append(img)  # On filter error, keep the image

                # Apply resize
                target_size = 900 if image_size == "900x900" else None
                for img in images:
                    img["bytes"] = resize_to_square(img["bytes"], target_size)
                    pil = Image.open(io.BytesIO(img["bytes"]))
                    img["width"], img["height"] = pil.width, pil.height
                status.update(label=f"{len(images)} תמונות מוצר איכותיות (סוננו {len(raw_images)-len(images)})", state="complete")

            # Step 1.5 – Remove background if requested
            bg_removed = False
            if remove_bg:
                with st.status("מסיר רקע מתמונות...", expanded=True) as status:
                    for i, img in enumerate(images):
                        img["bytes"] = remove_background(img["bytes"])
                        status.update(label=f"מסיר רקע... ({i+1}/{len(images)})")
                    bg_removed = True
                    status.update(label="רקע הוסר בהצלחה!", state="complete")

            # Step 2 – Rasterize all pages + OCR
            with st.status("קורא טקסט מהאריזה...", expanded=True) as status:
                num_pages = get_pdf_page_count(pdf_bytes)
                page_jpegs = []
                for p in range(1, num_pages + 1):
                    page_jpegs.append(rasterize_pdf_page(pdf_bytes, page=p, dpi=200))
                packaging_text = extract_packaging_text(client, page_jpegs)
                status.update(label=f"טקסט אריזה חולץ ({num_pages} עמודים)", state="complete")

            # Step 3 – Generate Hebrew
            with st.status(f"מייצר תוכן שיווקי ({text_style}) בעברית...", expanded=True) as status:
                hebrew_content = generate_hebrew_content(client, packaging_text, style=style_arg, user_notes=user_notes)
                status.update(label="תוכן שיווקי מוכן!", state="complete")

            # Step 4 – Atmosphere images + marketing strips (optional)
            atmospheres_clean = []
            atmospheres_striped = []
            if gen_atmospheres:
                if not gemini_key:
                    st.warning("צריך Gemini API Key כדי לייצר תמונות אווירה - דילגנו על השלב")
                elif not images:
                    st.warning("לא נמצאו תמונות מוצר ב-PDF, אי אפשר לייצר אווירה - דילגנו")
                else:
                    try:
                        from google import genai as google_genai
                        gemini_client = google_genai.Client(api_key=gemini_key)
                        ref_bytes_list = []
                        for img in images[:3]:
                            ref_pil = Image.open(io.BytesIO(img["bytes"])).convert("RGB")
                            rb = io.BytesIO()
                            ref_pil.save(rb, format="JPEG", quality=92)
                            ref_bytes_list.append(rb.getvalue())

                        atmospheres_clean, atmospheres_striped = run_atmosphere_pipeline(
                            client=client,
                            gemini_client=gemini_client,
                            ref_bytes_list=ref_bytes_list,
                            scene_template_inputs=scene_template_inputs,
                            user_notes=user_notes,
                            hebrew_content=hebrew_content,
                            target_count=4,
                            enable_validator=enable_validator,
                        )
                    except Exception as e:
                        st.warning(f"כשל בייצור תמונות אווירה: {e}")

        # Save to session state so results survive reruns
        st.session_state["results"] = {
            "images": images,
            "packaging_text": packaging_text,
            "hebrew_content": hebrew_content,
            "filename": display_filename,
            "bg_removed": bg_removed,
            "atmospheres_clean": atmospheres_clean,
            "atmospheres_striped": atmospheres_striped,
        }

    except anthropic.AuthenticationError:
        st.error("API Key לא תקין. בדוק את המפתח ונסה שוב.")
        st.stop()
    except anthropic.APIError as e:
        st.error(f"שגיאת API: {e.message}")
        st.stop()
    except Exception as e:
        st.error(f"שגיאה: {e}")
        st.stop()

# ── Show results (from session state or fresh run) ──
results = st.session_state.get("results")
if results:
    images = results["images"]
    packaging_text = results["packaging_text"]
    hebrew_content = results["hebrew_content"]
    filename = results["filename"]
    bg_removed = results.get("bg_removed", False)
    atmospheres_clean = results.get("atmospheres_clean", [])
    atmospheres_striped = results.get("atmospheres_striped", [])

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title"><span class="step-badge">2</span> תמונות מוצר נקיות</div>', unsafe_allow_html=True)

        if images:
            img_cols = st.columns(min(len(images), 3))
            for i, img_data in enumerate(images[:6]):
                with img_cols[i % 3]:
                    pil_img = Image.open(io.BytesIO(img_data["bytes"]))
                    st.image(pil_img, caption=f"תמונה {i+1}", use_container_width=True)
        else:
            st.warning("לא נמצאו תמונות מוצר מוטמעות ב-PDF")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title"><span class="step-badge">3</span> תוכן שיווקי – עברית</div>', unsafe_allow_html=True)

        with st.expander("טקסט אנגלי שחולץ מהאריזה"):
            st.text(packaging_text)

        st.markdown(f'<div class="hebrew-content">{hebrew_content.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        st.code(hebrew_content, language=None)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Atmosphere images ──
        if atmospheres_clean:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title"><span class="step-badge">4</span> תמונות אווירה שיווקיות</div>', unsafe_allow_html=True)

            st.markdown("**תמונות אווירה נקיות:**")
            atm_cols = st.columns(min(len(atmospheres_clean), 2))
            for i, atm in enumerate(atmospheres_clean):
                with atm_cols[i % 2]:
                    st.image(Image.open(io.BytesIO(atm)), caption=f"אווירה {i+1}", use_container_width=True)

            if atmospheres_striped:
                st.markdown("**תמונות עם פס שיווקי:**")
                str_cols = st.columns(min(len(atmospheres_striped), 2))
                for i, atm in enumerate(atmospheres_striped):
                    with str_cols[i % 2]:
                        st.image(Image.open(io.BytesIO(atm)), caption=f"שיווקי {i+1}", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Download ZIP ──
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title"><span class="step-badge">5</span> הורדה</div>', unsafe_allow_html=True)
        zip_bytes = create_zip(images, hebrew_content, bg_removed, atmospheres_clean, atmospheres_striped)
        st.download_button(
            label="הורד ZIP (תמונות + תוכן עברי)",
            data=zip_bytes,
            file_name=f"{Path(filename).stem}_processed.zip",
            mime="application/zip",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

elif not uploaded:
    with col2:
        st.markdown('<div class="card" style="min-height:300px; display:flex; align-items:center; justify-content:center; flex-direction:column; color:#aaa;">', unsafe_allow_html=True)
        st.markdown("### 📦")
        st.markdown("תוצאות יופיעו כאן לאחר עיבוד ה-PDF")
        st.markdown('</div>', unsafe_allow_html=True)
