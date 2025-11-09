#!/usr/bin/env python
"""
Script to generate fake forum data for testing
"""

import os
import django
import random
from datetime import timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twofa_site.settings')
django.setup()

from django.contrib.auth import get_user_model
from forum.models import Category, Thread, Post, PostReaction, Bookmark, ThreadFollow, Notification, UserProfile
from faker import Faker

User = get_user_model()
fake = Faker(['vi_VN', 'en_US'])

# Vietnamese forum content samples
VIETNAMESE_TOPICS = {
    'công nghệ': [
        'Nên mua iPhone hay Samsung?',
        'Macbook Air M3 có đáng giá không?',
        'Laptop gaming tầm 20 triệu',
        'Review tai nghe Sony WH-1000XM5',
        'Cách tăng tốc máy tính cũ',
        'Tư vấn build PC gaming 2024',
        'So sánh Windows 11 vs Ubuntu',
        'Điện thoại flagship tốt nhất năm nay',
        'Smartwatch có cần thiết không?',
        'Máy ảnh mirrorless cho người mới',
    ],
    'giải trí': [
        'Phim hay nhất tháng này',
        'Bàn về One Piece arc Wano',
        'Game mobile nào đáng chơi?',
        'Nhạc Việt hay nhất 2024',
        'Review series Netflix mới',
        'Anime mùa này có gì hot?',
        'LMHT: Meta mùa mới',
        'Đánh giá phim Marvel mới nhất',
        'Kênh YouTube Việt Nam hay',
        'Podcast về marketing digital',
    ],
    'đời sống': [
        'Quán cafe đẹp ở Sài Gòn',
        'Kinh nghiệm du lịch Đà Lạt',
        'Tập gym cho người mới bắt đầu',
        'Làm thế nào để tăng thu nhập?',
        'Mẹo tiết kiệm tiền hàng tháng',
        'Review khóa học tiếng Anh online',
        'Chế độ ăn healthy cho dân văn phòng',
        'Kinh nghiệm thuê nhà trọ Hà Nội',
        'Cách học lập trình hiệu quả',
        'Tư vấn chọn trường đại học',
    ],
    'thảo luận': [
        'Các bạn nghĩ gì về remote work?',
        'AI có thay thế được lập trình viên?',
        'Bitcoin có nên đầu tư không?',
        'Gen Z vs Gen Millennials',
        'Xu hướng công nghệ 2025',
        'Làm thế nào để work-life balance?',
        'Nên học đại học hay đi làm sớm?',
        'Ý kiến về việc làm side hustle',
        'Freelance vs Full-time job',
        'Khởi nghiệp ở tuổi 25',
    ]
}

VIETNAMESE_COMMENTS = [
    'Mình cũng nghĩ vậy, ý kiến hay đấy!',
    'Hoàn toàn đồng ý với bạn',
    'Có thể giải thích rõ hơn không bạn?',
    'Thanks bạn đã chia sẻ, rất hữu ích!',
    'Mình đã thử cách này rồi, khá ổn',
    'Quan điểm hay, nhưng mình nghĩ còn một khía cạnh khác',
    'Chưa thử nhưng nghe có vẻ hay',
    'Có link tham khảo không bạn?',
    'Cảm ơn bạn nhiều, đúng là mình cần!',
    'Mình cũng gặp vấn đề tương tự',
    'Bạn có kinh nghiệm thực tế chưa?',
    'Đúng rồi, mình cũng nghĩ thế',
    'Hay quá, mình sẽ thử xem',
    'Chia sẻ hay, upvote cho bạn',
    'Thông tin rất bổ ích, saved!',
]

def create_users(num_users=300):
    """Create fake users"""
    print(f"Creating {num_users} users...")
    users = []
    
    for i in range(num_users):
        username = fake.user_name() + str(random.randint(1000, 9999))
        email = f"{username}@example.com"
        
        # Check if user exists
        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            continue
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123'  # Same password for all test users
            )
        except Exception as e:
            print(f"  Error creating user: {e}")
            continue
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            bio=fake.text(max_nb_chars=200) if random.random() > 0.5 else '',
            location=fake.city() if random.random() > 0.6 else '',
            website=fake.url() if random.random() > 0.7 else '',
            reputation=random.randint(0, 5000),
            joined_date=timezone.now() - timedelta(days=random.randint(1, 365)),
            last_activity=timezone.now() - timedelta(hours=random.randint(1, 72))
        )
        
        users.append(user)
        
        if (i + 1) % 50 == 0:
            print(f"  Created {i + 1} users...")
    
    print(f"[OK] Created {len(users)} users")
    return users

def create_threads_and_posts(users, num_threads=200, posts_per_thread=(3, 15)):
    """Create fake threads and posts"""
    categories = list(Category.objects.filter(parent__isnull=False))
    
    if not categories:
        print("⚠ No categories found! Please create categories first.")
        return
    
    print(f"Creating {num_threads} threads...")
    threads_created = 0
    posts_created = 0
    
    prefixes = ['', 'tin-tuc', 'thao-luan', 'danh-gia', 'kien-thuc', 'thac-mac', 'hoi']
    
    for i in range(num_threads):
        # Pick random category
        category = random.choice(categories)
        author = random.choice(users)
        
        # Get topic based on category name
        category_key = 'thảo luận'  # default
        category_lower = category.title.lower()
        if 'công nghệ' in category_lower or 'tech' in category_lower:
            category_key = 'công nghệ'
        elif 'giải trí' in category_lower or 'game' in category_lower:
            category_key = 'giải trí'
        elif 'đời sống' in category_lower or 'life' in category_lower:
            category_key = 'đời sống'
        
        title = random.choice(VIETNAMESE_TOPICS.get(category_key, VIETNAMESE_TOPICS['thảo luận']))
        
        # Add some variation to titles
        if random.random() > 0.7:
            title = f"{title} - {random.choice(['Cần tư vấn', 'Help', 'Chia sẻ', 'Review'])}"
        
        # Create thread
        created_at = timezone.now() - timedelta(days=random.randint(0, 90))
        
        thread = Thread.objects.create(
            category=category,
            author=author,
            title=title,
            created_at=created_at,
            updated_at=created_at,
            locked=random.random() > 0.95,
            pinned=random.random() > 0.97,
            views=random.randint(10, 5000),
            is_featured=random.random() > 0.95,
            prefix=random.choice(prefixes)
        )
        
        threads_created += 1
        
        # Create first post (thread content)
        first_post = Post.objects.create(
            thread=thread,
            author=author,
            content=fake.paragraph(nb_sentences=random.randint(3, 8)),
            created_at=created_at
        )
        posts_created += 1
        
        # Create replies
        num_posts = random.randint(posts_per_thread[0], posts_per_thread[1])
        
        for j in range(num_posts):
            reply_author = random.choice(users)
            reply_time = created_at + timedelta(minutes=random.randint(5, 10080))  # 5 mins to 7 days
            
            # Mix between Vietnamese comments and generated text
            if random.random() > 0.4:
                content = random.choice(VIETNAMESE_COMMENTS)
                if random.random() > 0.6:
                    content += "\n\n" + fake.paragraph(nb_sentences=random.randint(1, 3))
            else:
                content = fake.paragraph(nb_sentences=random.randint(2, 6))
            
            post = Post.objects.create(
                thread=thread,
                author=reply_author,
                content=content,
                created_at=reply_time
            )
            posts_created += 1
            
            # Add reactions to some posts
            if random.random() > 0.6:
                num_reactions = random.randint(1, 5)
                reaction_types = ['like', 'love', 'laugh', 'angry', 'sad']
                
                for _ in range(num_reactions):
                    reactor = random.choice(users)
                    reaction_type = random.choice(reaction_types)
                    
                    PostReaction.objects.get_or_create(
                        post=post,
                        user=reactor,
                        defaults={'reaction_type': reaction_type}
                    )
        
        # Update thread updated_at
        thread.updated_at = reply_time if num_posts > 0 else created_at
        thread.save()
        
        # Add bookmarks to some threads
        if random.random() > 0.8:
            num_bookmarks = random.randint(1, 5)
            for _ in range(num_bookmarks):
                bookmarker = random.choice(users)
                Bookmark.objects.get_or_create(user=bookmarker, thread=thread)
        
        # Add follows to some threads
        if random.random() > 0.7:
            num_follows = random.randint(1, 8)
            for _ in range(num_follows):
                follower = random.choice(users)
                ThreadFollow.objects.get_or_create(user=follower, thread=thread)
        
        if (i + 1) % 20 == 0:
            print(f"  Created {i + 1} threads with {posts_created} total posts...")
    
    print(f"[OK] Created {threads_created} threads")
    print(f"[OK] Created {posts_created} posts")

def create_notifications(users, num_notifications=100):
    """Create fake notifications"""
    print(f"Creating {num_notifications} notifications...")
    
    notification_types = ['thread_reply', 'mention', 'thread_follow']
    threads = list(Thread.objects.all()[:50])
    posts = list(Post.objects.all()[:100])
    
    created = 0
    for _ in range(num_notifications):
        user = random.choice(users)
        sender = random.choice(users)
        
        if user == sender:
            continue
        
        notif_type = random.choice(notification_types)
        thread = random.choice(threads) if threads else None
        post = random.choice(posts) if posts else None
        
        messages = {
            'thread_reply': f"{sender.username} đã reply thread của bạn",
            'mention': f"{sender.username} đã nhắc đến bạn",
            'thread_follow': f"Thread bạn theo dõi có bài mới từ {sender.username}",
        }
        
        Notification.objects.create(
            user=user,
            notification_type=notif_type,
            sender=sender,
            thread=thread,
            post=post,
            message=messages[notif_type],
            is_read=random.random() > 0.5,
            created_at=timezone.now() - timedelta(hours=random.randint(1, 168))
        )
        created += 1
    
    print(f"[OK] Created {created} notifications")

def update_user_profile_counts():
    """Update post and thread counts for all user profiles"""
    print("Updating user profile counts...")
    
    profiles = UserProfile.objects.all()
    for profile in profiles:
        profile.update_counts()
    
    print(f"[OK] Updated {profiles.count()} user profiles")

def main():
    print("=" * 60)
    print("GENERATING FAKE FORUM DATA")
    print("=" * 60)
    
    # Create users
    users = list(User.objects.all())
    if len(users) < 50:
        new_users = create_users(num_users=300)
        users = list(User.objects.all())
    else:
        print(f"Already have {len(users)} users, skipping user creation...")
    
    print(f"\nTotal users in database: {len(users)}")
    
    # Create threads and posts
    print("\n" + "=" * 60)
    create_threads_and_posts(users, num_threads=200, posts_per_thread=(5, 20))
    
    # Create notifications
    print("\n" + "=" * 60)
    create_notifications(users, num_notifications=150)
    
    # Update profile counts
    print("\n" + "=" * 60)
    update_user_profile_counts()
    
    # Print stats
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)
    print(f"Total Users: {User.objects.count()}")
    print(f"Total Threads: {Thread.objects.count()}")
    print(f"Total Posts: {Post.objects.count()}")
    print(f"Total Reactions: {PostReaction.objects.count()}")
    print(f"Total Bookmarks: {Bookmark.objects.count()}")
    print(f"Total Follows: {ThreadFollow.objects.count()}")
    print(f"Total Notifications: {Notification.objects.count()}")
    print("=" * 60)
    print("[OK] DONE! Fake data generated successfully!")
    print("=" * 60)

if __name__ == '__main__':
    main()
