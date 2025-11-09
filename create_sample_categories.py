import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twofa_site.settings')
django.setup()

from forum.models import Category

# Clear existing
Category.objects.all().delete()

# Create main categories
categories_data = [
    {
        'title': 'Đại sảnh',
        'icon': '🏛️',
        'description': 'Khu vực chung cho mọi thảo luận',
        'order': 1,
        'subforums': [
            {'title': 'Thông báo', 'icon': '📢', 'description': 'Thông báo chính thức từ BQT'},
            {'title': 'Góp ý', 'icon': '💡', 'description': 'Góp ý để cải thiện diễn đàn'},
            {'title': 'Tin tức', 'icon': '📰', 'description': 'Tin tức công nghệ mới nhất'},
        ]
    },
    {
        'title': 'Công nghệ',
        'icon': '💻',
        'description': 'Thảo luận về công nghệ, phần cứng, phần mềm',
        'order': 2,
        'subforums': [
            {'title': 'Máy tính', 'icon': '🖥️', 'description': 'PC, Laptop, linh kiện'},
            {'title': 'Điện thoại', 'icon': '📱', 'description': 'Smartphone, tablet'},
            {'title': 'Phần mềm', 'icon': '⚙️', 'description': 'Ứng dụng, tools, tips'},
        ]
    },
    {
        'title': 'Giải trí',
        'icon': '🎮',
        'description': 'Game, phim, nhạc và giải trí',
        'order': 3,
        'subforums': [
            {'title': 'Games', 'icon': '🎯', 'description': 'Thảo luận về games'},
            {'title': 'Phim ảnh', 'icon': '🎬', 'description': 'Review phim, series'},
            {'title': 'Âm nhạc', 'icon': '🎵', 'description': 'Chia sẻ nhạc yêu thích'},
        ]
    },
    {
        'title': 'Đời sống',
        'icon': '🌟',
        'description': 'Cuộc sống, sức khỏe, gia đình',
        'order': 4,
        'subforums': [
            {'title': 'Tâm sự', 'icon': '💭', 'description': 'Chia sẻ câu chuyện của bạn'},
            {'title': 'Sức khỏe', 'icon': '💪', 'description': 'Tips sống khỏe'},
            {'title': 'Ẩm thực', 'icon': '🍜', 'description': 'Món ngon mỗi ngày'},
        ]
    },
]

for cat_data in categories_data:
    parent = Category.objects.create(
        title=cat_data['title'],
        icon=cat_data['icon'],
        description=cat_data['description'],
        order=cat_data['order']
    )
    
    for i, sub_data in enumerate(cat_data.get('subforums', []), 1):
        Category.objects.create(
            title=sub_data['title'],
            icon=sub_data['icon'],
            description=sub_data.get('description', ''),
            parent=parent,
            order=i
        )

print("Da tao", Category.objects.filter(parent__isnull=True).count(), "categories chinh")
print("Da tao", Category.objects.filter(parent__isnull=False).count(), "sub-forums")
print("\nDanh sach categories:")
for cat in Category.objects.filter(parent__isnull=True).order_by('order'):
    print("\n", cat.title, "(slug:", cat.slug, ")")
    for sub in cat.sub_forums.all():
        print("   -", sub.title, "(slug:", sub.slug, ")")
