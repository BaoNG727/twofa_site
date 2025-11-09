from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from unidecode import unidecode

class Category(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='sub_forums')
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class or emoji")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Auto-generate slug from title if not provided
        if not self.slug:
            # Convert Vietnamese to ASCII, then slugify
            ascii_title = unidecode(self.title)
            base_slug = slugify(ascii_title)
            slug = base_slug
            counter = 1
            
            # Ensure unique slug
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        super().save(*args, **kwargs)

    def thread_count(self):
        return self.threads.count()

    def post_count(self):
        return Post.objects.filter(thread__category=self).count()

    def latest_post(self):
        return Post.objects.filter(thread__category=self).select_related('author', 'thread').order_by('-created_at').first()

class Thread(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="threads")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    locked = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    
    PREFIX_CHOICES = (
        ('', 'None'),
        ('tin-tuc', 'Tin tức'),
        ('thao-luan', 'Thảo luận'),
        ('danh-gia', 'Đánh giá'),
        ('kien-thuc', 'Kiến thức'),
        ('thac-mac', 'Thắc mắc'),
        ('khoe', 'Khoe'),
        ('hoi', 'Hỏi'),
        ('ban', 'Bán'),
    )
    prefix = models.CharField(max_length=20, choices=PREFIX_CHOICES, blank=True)

    class Meta:
        ordering = ['-pinned', '-updated_at']

    def __str__(self):
        return self.title

    def post_count(self):
        return self.posts.count()

    def latest_post(self):
        return self.posts.select_related('author').order_by('-created_at').first()

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])

class Post(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    image = models.ImageField(upload_to='post_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.IntegerField(default=0)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Post by {self.author} on {self.thread}"

class PostReaction(models.Model):
    REACTION_TYPES = (
        ('like', '👍'),
        ('love', '❤️'),
        ('laugh', '😂'),
        ('angry', '😠'),
        ('sad', '😢'),
    )
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES, default='like')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('post', 'user')

class ProfilePost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile_posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_profile_posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Profile post by {self.author} on {self.user}'s profile"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('thread_reply', 'Có người reply thread của bạn'),
        ('mention', 'Bạn được mention'),
        ('profile_post', 'Có người post lên profile của bạn'),
        ('thread_follow', 'Thread bạn theo dõi có bài mới'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications', null=True)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, null=True, blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarks')
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'thread')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} bookmarked {self.thread.title}"


class Report(models.Model):
    REPORT_TYPES = (
        ('spam', 'Spam'),
        ('inappropriate', 'Nội dung không phù hợp'),
        ('harassment', 'Quấy rối'),
        ('misinformation', 'Thông tin sai lệch'),
        ('other', 'Khác'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Chờ xử lý'),
        ('reviewing', 'Đang xem xét'),
        ('resolved', 'Đã xử lý'),
        ('ignored', 'Bỏ qua'),
    )
    
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, null=True, blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_resolved')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.thread or self.post
        return f"Report by {self.reporter.username} - {self.report_type}"


class ThreadFollow(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followed_threads')
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'thread')

    def __str__(self):
        return f"{self.user.username} follows {self.thread.title}"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, max_length=500)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    reputation = models.IntegerField(default=0)
    post_count = models.IntegerField(default=0)
    thread_count = models.IntegerField(default=0)
    joined_date = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(default=timezone.now)
    signature = models.TextField(blank=True, max_length=200)
    avatar_url = models.URLField(blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    def update_counts(self):
        from django.db.models import Count
        self.thread_count = Thread.objects.filter(author=self.user).count()
        self.post_count = Post.objects.filter(author=self.user).count()
        self.save(update_fields=['thread_count', 'post_count'])
    
    def get_rank(self):
        if self.reputation >= 10000:
            return 'Huyền thoại'
        elif self.reputation >= 5000:
            return 'Chuyên gia'
        elif self.reputation >= 2000:
            return 'Cao thủ'
        elif self.reputation >= 500:
            return 'Trung cấp'
        elif self.reputation >= 100:
            return 'Sơ cấp'
        else:
            return 'Tân binh'


class ThreadView(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='thread_views')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    viewed_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"View on {self.thread.title}"
