import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile


IMAGE_SPECS = {
    'blog':      {'width': 1200, 'height': 800,  'max_count': 5},
    'instagram': {'width': 1080, 'height': 1080, 'max_count': 10},
    'facebook':  {'width': 1200, 'height': 630,  'max_count': 5},
    'shorts':    {'width': 1080, 'height': 1920, 'max_count': 1},
    'reels':     {'width': 1080, 'height': 1920, 'max_count': 1},
    'tiktok':    {'width': 1080, 'height': 1920, 'max_count': 1},
    'card':      {'width': 1080, 'height': 1080, 'max_count': 10},
}

CATEGORY_COLORS = {
    '외식산업 뉴스':   ('#E8F5E9', '#2E7D32', '#1B5E20'),
    '창업/프랜차이즈': ('#E3F2FD', '#1565C0', '#0D47A1'),
    '부동산/상권분석': ('#FFF3E0', '#E65100', '#BF360C'),
    '비즈니스 정보':   ('#F3E5F5', '#6A1B9A', '#4A148C'),
    '일반':           ('#F5F5F5', '#424242', '#212121'),
}

DEFAULT_COLORS = ('#F5F5F5', '#424242', '#212121')


def get_colors(category):
    return CATEGORY_COLORS.get(category, DEFAULT_COLORS)


def resize_image(image_file, channel_type):
    spec = IMAGE_SPECS.get(channel_type, IMAGE_SPECS['blog'])
    width, height = spec['width'], spec['height']

    img = Image.open(image_file)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    img_ratio = img.width / img.height
    target_ratio = width / height

    if img_ratio > target_ratio:
        new_height = height
        new_width = int(height * img_ratio)
    else:
        new_width = width
        new_height = int(width / img_ratio)

    img = img.resize((new_width, new_height), Image.LANCZOS)

    left = (new_width - width) // 2
    top = (new_height - height) // 2
    img = img.crop((left, top, left + width, top + height))

    output = BytesIO()
    img.save(output, format='JPEG', quality=90)
    output.seek(0)
    return ContentFile(output.read())


def create_text_card(title, keyword, tags, category, channel_type, brand='postone'):
    spec = IMAGE_SPECS.get(channel_type, IMAGE_SPECS['blog'])
    width, height = spec['width'], spec['height']
    bg_color, main_color, dark_color = get_colors(category)

    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype('arial.ttf', size=int(height * 0.07))
        font_medium = ImageFont.truetype('arial.ttf', size=int(height * 0.045))
        font_small = ImageFont.truetype('arial.ttf', size=int(height * 0.03))
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large

    padding = int(width * 0.08)

    # 상단 브랜드 바
    draw.rectangle([0, 0, width, int(height * 0.12)], fill=main_color)
    draw.text(
        (padding, int(height * 0.06)),
        brand, fill='white', font=font_medium, anchor='lm'
    )

    # 카테고리 배지
    badge_y = int(height * 0.20)
    draw.rectangle(
        [padding, badge_y, padding + int(width * 0.25), badge_y + int(height * 0.06)],
        fill=main_color
    )
    draw.text(
        (padding + int(width * 0.125), badge_y + int(height * 0.03)),
        category, fill='white', font=font_small, anchor='mm'
    )

    # 제목
    title_y = int(height * 0.32)
    max_chars = int(width / (height * 0.07)) + 2
    wrapped = textwrap.wrap(title, width=max_chars)[:3]
    for i, line in enumerate(wrapped):
        draw.text(
            (padding, title_y + i * int(height * 0.10)),
            line, fill=dark_color, font=font_large
        )

    # 구분선
    line_y = int(height * 0.68)
    draw.rectangle([padding, line_y, width - padding, line_y + 3], fill=main_color)

    # 키워드
    draw.text(
        (padding, int(height * 0.73)),
        f'# {keyword}', fill=main_color, font=font_medium
    )

    # 태그
    tag_str = '  '.join([f'#{t}' for t in tags[:4]])
    draw.text(
        (padding, int(height * 0.82)),
        tag_str, fill=dark_color, font=font_small
    )

    # 하단 바
    draw.rectangle([0, height - int(height * 0.04), width, height], fill=main_color)

    output = BytesIO()
    img.save(output, format='JPEG', quality=92)
    output.seek(0)
    return ContentFile(output.read())


def process_images(generation, uploaded_files, channel_type, title, keyword, tags, category):
    if uploaded_files:
        thumbnail = resize_image(uploaded_files[0], channel_type)
        generation.thumbnail.save(
            f'{channel_type}_{generation.pk}_thumb.jpg', thumbnail, save=False
        )
        paths = []
        for i, f in enumerate(uploaded_files[1:10]):
            resized = resize_image(f, channel_type)
            fname = f'{channel_type}_{generation.pk}_img{i+1}.jpg'
            generation.thumbnail.storage.save(
                f'content/{channel_type}/{fname}', resized
            )
            paths.append(f'content/{channel_type}/{fname}')
        generation.extra_images = paths
    else:
        card = create_text_card(title, keyword, tags, category, channel_type)
        generation.text_card.save(
            f'card_{channel_type}_{generation.pk}.jpg', card, save=False
        )
    generation.save()