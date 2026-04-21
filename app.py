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


def generate_hebrew_content(client: anthropic.Anthropic, packaging_text: str) -> str:
    """Use Claude to turn extracted text into Hebrew website copy."""
    prompt = MARKETING_TEMPLATE.format(packaging_text=packaging_text)
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


def generate_scene_prompts(client: anthropic.Anthropic, packaging_text: str, hebrew_content: str) -> list[str]:
    """Use Claude to generate 4 English scene prompts for Gemini image generation."""
    prompt = f"""You are a creative director for product photography. A Food Appeal kitchen appliance needs 4 lifestyle images.

Product info (English text from packaging):
{packaging_text}

Hebrew marketing copy:
{hebrew_content}

Generate 4 detailed English prompts for AI image generation. Each prompt will be combined with a reference product photo to create a lifestyle image:
- Prompt 1 & 2: The product IN USE with relevant food inside/on it (e.g., for slow cooker → stew inside; for waffle maker → fresh waffles). Choose FOODS THAT MAKE SENSE for this specific appliance.
- Prompt 3 & 4: The product in a BEAUTIFUL KITCHEN SCENE (on a counter, styled with plates/ingredients nearby, natural light, modern home).

Each prompt should:
- Describe lighting (warm morning light, soft overhead, etc.)
- Describe composition (close-up, 3/4 angle, etc.)
- Describe styling (herbs, ingredients, plates)
- Mention the product should remain identical to the reference
- Be 2-3 sentences, photography-style

Respond with ONLY a valid JSON array of 4 strings, nothing else:
["prompt 1", "prompt 2", "prompt 3", "prompt 4"]"""

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


def generate_atmosphere_image(gemini_client, product_img_bytes: bytes, prompt: str) -> bytes:
    """Generate a lifestyle image using Gemini 2.5 Flash Image."""
    from google.genai import types as gen_types
    product_img = Image.open(io.BytesIO(product_img_bytes))
    config = gen_types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])
    last_err = None
    for model_name in ("gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"):
        try:
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=[prompt, product_img],
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
- Pick a strip_color that harmonizes with (or boldly contrasts) the dominant image colors, similar to how premium product ads look. Deep reds, dark navy, forest green, or warm black usually work well.
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
        # Safe default
        return {"strip_position": "bottom", "strip_color": "#8B0000", "text_color": "#FFFFFF", "strip_height_ratio": 0.12}


def draw_marketing_strip(image_bytes: bytes, tagline: str, placement: dict) -> bytes:
    """Draw a colored strip with Hebrew tagline on top/bottom of the image."""
    from bidi.algorithm import get_display

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    W, H = img.size
    strip_h = int(H * placement["strip_height_ratio"])
    pos = placement["strip_position"]

    draw = ImageDraw.Draw(img)
    if pos == "top":
        strip_box = (0, 0, W, strip_h)
    else:
        strip_box = (0, H - strip_h, W, H)
    draw.rectangle(strip_box, fill=placement["strip_color"])

    # Hebrew text: reorder for RTL
    display_text = get_display(tagline)
    font_size = int(strip_h * 0.55)
    font = _load_font(font_size)

    l, t, r, b = draw.textbbox((0, 0), display_text, font=font)
    tw, th = r - l, b - t
    x = (W - tw) // 2 - l
    if pos == "top":
        y = (strip_h - th) // 2 - t
    else:
        y = (H - strip_h) + (strip_h - th) // 2 - t

    draw.text((x, y), display_text, font=font, fill=placement["text_color"])

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def generate_minimal_hebrew_from_image(client: anthropic.Anthropic, img_bytes: bytes) -> str:
    """Generate minimalistic Hebrew marketing copy from a single product image."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    if max(img.size) > 1200:
        ratio = 1200 / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.standard_b64encode(buf.getvalue()).decode()

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": (
                    "זו תמונה של מוצר חשמלי למטבח. "
                    "כתוב תוכן שיווקי מינימליסטי בעברית לאתר איקומרס, בהתבסס רק על מה שאתה רואה בתמונה.\n\n"
                    "המבנה:\n"
                    "1. שורת כותרת ראשית: סוג המוצר + שם/מותג אם נראה בתמונה\n"
                    "2. פסקה קצרה (3-4 משפטים) על מה המוצר עושה ויתרונותיו הנראים לעין\n"
                    "3. 3-4 bullets על תכונות בולטות (חומרים, עיצוב, שימושיות)\n\n"
                    "שמור על טון שיווקי מקצועי אך קצר ותמציתי. אל תמציא מפרט טכני שאתה לא רואה בתמונה. "
                    "החזר רק את הטקסט השיווקי בעברית, בלי הסברים נוספים."
                )},
            ],
        }],
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
        options=["PDF של אריזה", "תמונת מוצר בודדת"],
        horizontal=True,
    )

    if upload_mode == "PDF של אריזה":
        uploaded = st.file_uploader("גרור PDF של אריזת מוצר", type=["pdf"], label_visibility="collapsed", key="pdf_upl")
    else:
        uploaded = st.file_uploader("גרור תמונת מוצר (JPG/PNG)", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed", key="img_upl")

    if uploaded:
        st.success(f"✅ {uploaded.name} ({uploaded.size // 1024} KB)")

        st.markdown('<div class="section-title">הגדרות תמונה</div>', unsafe_allow_html=True)
        image_size = st.radio(
            "גודל תמונות",
            options=["900x900", "גודל מקסימלי"],
            horizontal=True,
        )
        if upload_mode == "PDF של אריזה":
            remove_bg = st.checkbox("הסרת רקע (רקע שקוף)")
        else:
            remove_bg = False
        gen_atmospheres = st.checkbox("ייצר תמונות אווירה (4 נקיות + 4 עם פס שיווקי) (~$0.16 לקובץ)")

        run_btn = st.button("🚀 עבד", use_container_width=True)
    else:
        run_btn = False
        st.info("📂 ממתין לקובץ...")
    st.markdown('</div>', unsafe_allow_html=True)

# ── Process ──
if run_btn and uploaded:
    if not api_key:
        st.error("הכנס Anthropic API Key בסרגל השמאלי")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)
    file_bytes = uploaded.read()

    try:
     if upload_mode == "תמונת מוצר בודדת":
        # === SINGLE IMAGE MODE ===
        with col1:
            with st.status("מעבד תמונה...", expanded=True) as status:
                target_size = 900 if image_size == "900x900" else None
                resized = resize_to_square(file_bytes, target_size)
                pil = Image.open(io.BytesIO(resized))
                images = [{"bytes": resized, "width": pil.width, "height": pil.height, "xref": 0}]
                status.update(label="תמונה עובדה", state="complete")

            with st.status("מייצר תוכן שיווקי מינימליסטי בעברית...", expanded=True) as status:
                hebrew_content = generate_minimal_hebrew_from_image(client, resized)
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
                        ref_img = Image.open(io.BytesIO(resized))
                        ref_buf = io.BytesIO()
                        ref_img.convert("RGB").save(ref_buf, format="JPEG", quality=92)
                        ref_bytes = ref_buf.getvalue()

                        with st.status("יוצר תיאורי סצנה...", expanded=True) as status:
                            scene_prompts = generate_scene_prompts(client, "", hebrew_content)
                            status.update(label="תיאורי סצנה מוכנים", state="complete")

                        atmosphere_errors = []
                        with st.status("מייצר תמונות אווירה...", expanded=True) as status:
                            for i, sp in enumerate(scene_prompts):
                                status.update(label=f"מייצר תמונת אווירה {i+1}/{len(scene_prompts)}...")
                                try:
                                    atm = generate_atmosphere_image(gemini_client, ref_bytes, sp)
                                    atmospheres_clean.append(atm)
                                except Exception as e:
                                    atmosphere_errors.append(f"תמונה {i+1}: {type(e).__name__}: {e}")
                            status.update(label=f"נוצרו {len(atmospheres_clean)} תמונות אווירה", state="complete")
                        for err in atmosphere_errors:
                            st.error(err)

                        if atmospheres_clean:
                            with st.status("מחלץ משפטי שיווק...", expanded=True) as status:
                                taglines = extract_marketing_taglines(client, hebrew_content)
                                status.update(label="משפטי שיווק מוכנים", state="complete")

                            with st.status("מוסיף פסי שיווק...", expanded=True) as status:
                                for i, atm in enumerate(atmospheres_clean):
                                    status.update(label=f"מעצב פס שיווקי {i+1}/{len(atmospheres_clean)}...")
                                    placement = analyze_strip_placement(client, atm)
                                    tagline = taglines[i] if i < len(taglines) else taglines[0]
                                    striped = draw_marketing_strip(atm, tagline, placement)
                                    atmospheres_striped.append(striped)
                                status.update(label="פסי שיווק מוכנים!", state="complete")
                    except Exception as e:
                        st.warning(f"כשל בייצור תמונות אווירה: {e}")

        st.session_state["results"] = {
            "images": images,
            "packaging_text": packaging_text,
            "hebrew_content": hebrew_content,
            "filename": uploaded.name,
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
            with st.status("מייצר תוכן שיווקי בעברית...", expanded=True) as status:
                hebrew_content = generate_hebrew_content(client, packaging_text)
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
                        # Use the largest product image (first in the sorted list)
                        # Must be original (not bg-removed PNG) - use JPEG-encoded version
                        ref_img = Image.open(io.BytesIO(images[0]["bytes"]))
                        ref_buf = io.BytesIO()
                        ref_img.convert("RGB").save(ref_buf, format="JPEG", quality=92)
                        ref_bytes = ref_buf.getvalue()

                        with st.status("יוצר תיאורי סצנה...", expanded=True) as status:
                            scene_prompts = generate_scene_prompts(client, packaging_text, hebrew_content)
                            status.update(label="תיאורי סצנה מוכנים", state="complete")

                        atmosphere_errors = []
                        with st.status("מייצר תמונות אווירה...", expanded=True) as status:
                            for i, sp in enumerate(scene_prompts):
                                status.update(label=f"מייצר תמונת אווירה {i+1}/{len(scene_prompts)}...")
                                try:
                                    atm = generate_atmosphere_image(gemini_client, ref_bytes, sp)
                                    atmospheres_clean.append(atm)
                                except Exception as e:
                                    atmosphere_errors.append(f"תמונה {i+1}: {type(e).__name__}: {e}")
                            status.update(label=f"נוצרו {len(atmospheres_clean)} תמונות אווירה", state="complete")
                        # Show errors OUTSIDE the status block so they're visible
                        for err in atmosphere_errors:
                            st.error(err)

                        if atmospheres_clean:
                            with st.status("מחלץ משפטי שיווק...", expanded=True) as status:
                                taglines = extract_marketing_taglines(client, hebrew_content)
                                status.update(label="משפטי שיווק מוכנים", state="complete")

                            with st.status("מוסיף פסי שיווק...", expanded=True) as status:
                                for i, atm in enumerate(atmospheres_clean):
                                    status.update(label=f"מעצב פס שיווקי {i+1}/{len(atmospheres_clean)}...")
                                    placement = analyze_strip_placement(client, atm)
                                    tagline = taglines[i] if i < len(taglines) else taglines[0]
                                    striped = draw_marketing_strip(atm, tagline, placement)
                                    atmospheres_striped.append(striped)
                                status.update(label="פסי שיווק מוכנים!", state="complete")
                    except Exception as e:
                        st.warning(f"כשל בייצור תמונות אווירה: {e}")

        # Save to session state so results survive reruns
        st.session_state["results"] = {
            "images": images,
            "packaging_text": packaging_text,
            "hebrew_content": hebrew_content,
            "filename": uploaded.name,
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
