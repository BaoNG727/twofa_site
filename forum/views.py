from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.cache import cache_page

from .models import Category, Thread, Post, Notification, Bookmark, Report, ThreadFollow, PostReaction, UserProfile, ThreadView
from .forms import ThreadCreateForm, PostForm, ReportForm

User = get_user_model()


@cache_page(60 * 5)  # Cache for 5 minutes
def home(request):
    """
    Trang chủ diễn đàn: liệt kê categories theo kiểu Voz.
    """
    from django.core.cache import cache
    
    # Try to get categories from cache
    categories = cache.get('forum_categories')
    if not categories:
        categories = (
            Category.objects
            .filter(parent__isnull=True)
            .prefetch_related('sub_forums')
            .order_by('order', 'title')
        )
        cache.set('forum_categories', categories, 60 * 10)  # Cache for 10 minutes
    
    featured_threads = (
        Thread.objects
        .select_related('author', 'category')
        .order_by('-views', '-created_at')[:5]
    )
    
    latest_posts = (
        Post.objects
        .select_related('author', 'thread', 'thread__category')
        .order_by('-created_at')[:5]
    )
    
    # Get stats from cache
    stats = cache.get('forum_stats')
    if not stats:
        stats = {
            'total_threads': Thread.objects.count(),
            'total_posts': Post.objects.count(),
            'total_members': User.objects.count(),
            'latest_member': User.objects.order_by('-date_joined').first(),
        }
        cache.set('forum_stats', stats, 60 * 5)  # Cache for 5 minutes
    
    return render(request, "forum/home.html", {
        "categories": categories,
        "featured_threads": featured_threads,
        "latest_posts": latest_posts,
        "total_threads": stats['total_threads'],
        "total_posts": stats['total_posts'],
        "total_members": stats['total_members'],
        "latest_member": stats['latest_member'],
    })


def category_view(request, slug):
    """
    Hiển thị tất cả threads trong một category với pagination
    """
    category = get_object_or_404(Category, slug=slug)
    
    threads_list = (
        Thread.objects
        .filter(category=category)
        .select_related('author', 'category')
        .order_by('-pinned', '-updated_at')
    )
    
    # Pagination
    paginator = Paginator(threads_list, 20)  # 20 threads per page
    page = request.GET.get('page')
    
    try:
        threads = paginator.page(page)
    except PageNotAnInteger:
        threads = paginator.page(1)
    except EmptyPage:
        threads = paginator.page(paginator.num_pages)
    
    return render(request, 'forum/category_threads.html', {
        'category': category,
        'threads': threads
    })


@login_required
def thread_create(request):
    """
    Tạo thread mới:
    - tạo record Thread (title/category/author)
    - tạo luôn Post đầu tiên là nội dung mở đầu
    """
    if request.method == "POST":
        form = ThreadCreateForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data["title"]
            category = form.cleaned_data["category"]
            content = form.cleaned_data["content"]
            prefix = form.cleaned_data.get("prefix", "")

            # tạo Thread
            thread = Thread.objects.create(
                title=title,
                category=category,
                author=request.user,
                prefix=prefix,
                created_at=timezone.now(),
                locked=False,
            )

            # tạo Post đầu tiên (nội dung mở đầu)
            Post.objects.create(
                thread=thread,
                author=request.user,
                content=content,
                created_at=timezone.now(),
            )

            return redirect("forum:thread_detail", pk=thread.id)
    else:
        form = ThreadCreateForm()

    return render(request, "forum/thread_create.html", {"form": form})


def thread_detail(request, pk):
    """
    Xem thread + tất cả post trong đó.
    Đồng thời xử lý form trả lời:
      - chỉ user login mới trả lời
      - nếu thread.locked == True thì chặn trả lời
    """
    thread = get_object_or_404(
        Thread.objects.select_related("author", "category"),
        pk=pk
    )
    
    # Track view
    thread.increment_views()
    
    # Record detailed view tracking
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    ThreadView.objects.create(
        thread=thread,
        user=request.user if request.user.is_authenticated else None,
        ip_address=get_client_ip(request)
    )

    posts_list = (
        Post.objects
        .filter(thread=thread)
        .select_related("author")
        .order_by("created_at")
    )
    
    # Pagination for posts
    paginator = Paginator(posts_list, 15)  # 15 posts per page
    page = request.GET.get('page')
    
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Bạn cần đăng nhập để trả lời.")

        if thread.locked:
            return HttpResponseForbidden("Chủ đề này đã bị khóa, không thể trả lời.")

        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.thread = thread
            reply.author = request.user
            reply.created_at = timezone.now()
            reply.save()

            # Tạo notification cho author của thread
            if reply.author != thread.author:
                Notification.objects.create(
                    user=thread.author,
                    notification_type='thread_reply',
                    sender=reply.author,
                    thread=thread,
                    post=reply,
                    message=f"{reply.author.username} đã reply thread của bạn: {thread.title}"
                )

            # Tạo notification cho users follow thread này
            followers = ThreadFollow.objects.filter(thread=thread).exclude(user=reply.author)
            for follow in followers:
                Notification.objects.create(
                    user=follow.user,
                    notification_type='thread_follow',
                    sender=reply.author,
                    thread=thread,
                    post=reply,
                    message=f"Thread bạn theo dõi có bài mới: {thread.title}"
                )

            return redirect("forum:thread_detail", pk=thread.id)
    else:
        form = PostForm()

    # Check if user has bookmarked or following this thread
    is_bookmarked = False
    is_following = False
    if request.user.is_authenticated:
        is_bookmarked = Bookmark.objects.filter(user=request.user, thread=thread).exists()
        is_following = ThreadFollow.objects.filter(user=request.user, thread=thread).exists()
    
    ctx = {
        "thread": thread,
        "posts": posts,
        "form": form,
        "is_bookmarked": is_bookmarked,
        "is_following": is_following,
    }
    return render(request, "forum/thread_detail.html", ctx)


def new_posts(request):
    posts = (
        Post.objects
        .select_related('author', 'thread', 'thread__category')
        .order_by('-created_at')[:50]
    )
    return render(request, 'forum/new_posts.html', {'posts': posts})


def latest_activity(request):
    threads = (
        Thread.objects
        .select_related('author', 'category')
        .prefetch_related('posts')
        .order_by('-updated_at')[:50]
    )
    return render(request, 'forum/latest_activity.html', {'threads': threads})


def featured_content(request):
    threads = (
        Thread.objects
        .filter(is_featured=True)
        .select_related('author', 'category')
        .order_by('-views', '-created_at')
    )
    return render(request, 'forum/featured_content.html', {'threads': threads})


def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile_posts = user.profile_posts.select_related('author').order_by('-created_at')
    
    post_count = Post.objects.filter(author=user).count()
    thread_count = Thread.objects.filter(author=user).count()
    
    ctx = {
        'profile_user': user,
        'profile_posts': profile_posts,
        'post_count': post_count,
        'thread_count': thread_count,
    }
    return render(request, 'forum/profile.html', ctx)


def search(request):
    query = request.GET.get('q', '')
    results = []
    
    if query:
        from django.db.models import Q
        threads = Thread.objects.filter(
            Q(title__icontains=query) | Q(posts__content__icontains=query)
        ).select_related('author', 'category').distinct()[:50]
        
        posts = Post.objects.filter(
            Q(content__icontains=query)
        ).select_related('author', 'thread', 'thread__category')[:50]
        
        results = {
            'threads': threads,
            'posts': posts,
            'query': query
        }
    
    return render(request, 'forum/search.html', results)


# ============================================================================
# NOTIFICATIONS VIEWS
# ============================================================================

@login_required
def notifications_list(request):
    """Danh sách thông báo của user"""
    notifications = request.user.notifications.all()[:50]
    
    # Mark all as read when viewing
    request.user.notifications.filter(is_read=False).update(is_read=True)
    
    return render(request, 'forum/notifications.html', {
        'notifications': notifications
    })


@login_required
def mark_notification_read(request, notification_id):
    """Đánh dấu 1 thông báo đã đọc"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('forum:notifications')


@login_required
def notification_count(request):
    """API trả về số thông báo chưa đọc (JSON)"""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})


# ============================================================================
# BOOKMARKS VIEWS
# ============================================================================

@login_required
def bookmarks_list(request):
    """Danh sách threads đã bookmark"""
    bookmarks = Bookmark.objects.filter(user=request.user).select_related('thread', 'thread__author', 'thread__category')
    return render(request, 'forum/bookmarks.html', {
        'bookmarks': bookmarks
    })


@login_required
def toggle_bookmark(request, thread_id):
    """Toggle bookmark cho thread (POST request)"""
    thread = get_object_or_404(Thread, pk=thread_id)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, thread=thread)
    
    if not created:
        bookmark.delete()
        message = "Đã bỏ lưu thread"
    else:
        message = "Đã lưu thread"
    
    messages.success(request, message)
    return redirect('forum:thread_detail', pk=thread_id)


@login_required
def thread_follow_toggle(request, thread_id):
    """Toggle follow thread"""
    thread = get_object_or_404(Thread, pk=thread_id)
    follow, created = ThreadFollow.objects.get_or_create(user=request.user, thread=thread)
    
    if not created:
        follow.delete()
        message = "Đã bỏ theo dõi thread"
    else:
        message = "Đã theo dõi thread"
    
    messages.success(request, message)
    return redirect('forum:thread_detail', pk=thread_id)


# ============================================================================
# REPORTS VIEWS
# ============================================================================

@login_required
def report_create(request, thread_id=None, post_id=None):
    """Tạo báo cáo vi phạm"""
    thread = None
    post = None
    
    if thread_id:
        thread = get_object_or_404(Thread, pk=thread_id)
    if post_id:
        post = get_object_or_404(Post, pk=post_id)
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.thread = thread
            report.post = post
            report.save()
            
            messages.success(request, 'Đã gửi báo cáo. Admin sẽ xem xét.')
            
            if thread:
                return redirect('forum:thread_detail', pk=thread.id)
            else:
                return redirect('forum:home')
    else:
        form = ReportForm()
    
    return render(request, 'forum/report_create.html', {
        'form': form,
        'thread': thread,
        'post': post
    })


# ============================================================================
# REACTIONS VIEWS
# ============================================================================

@login_required
def toggle_reaction(request, post_id):
    """Toggle reaction on a post (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    post = get_object_or_404(Post, pk=post_id)
    reaction_type = request.POST.get('reaction_type', 'like')
    
    # Check if user already reacted
    existing_reaction = PostReaction.objects.filter(user=request.user, post=post).first()
    
    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            # Remove reaction if same type
            existing_reaction.delete()
            action = 'removed'
        else:
            # Change reaction type
            existing_reaction.reaction_type = reaction_type
            existing_reaction.save()
            action = 'changed'
    else:
        # Create new reaction
        PostReaction.objects.create(user=request.user, post=post, reaction_type=reaction_type)
        action = 'added'
        
        # Create notification for post author
        if post.author != request.user:
            Notification.objects.create(
                user=post.author,
                notification_type='mention',
                sender=request.user,
                thread=post.thread,
                post=post,
                message=f"{request.user.username} đã react {reaction_type} bài viết của bạn"
            )
    
    # Get updated reaction counts
    from django.db.models import Count
    reactions = PostReaction.objects.filter(post=post).values('reaction_type').annotate(count=Count('reaction_type'))
    reaction_counts = {r['reaction_type']: r['count'] for r in reactions}
    
    return JsonResponse({
        'action': action,
        'reaction_counts': reaction_counts,
        'total': sum(reaction_counts.values())
    })


@login_required
def user_profile(request, username):
    """Enhanced user profile with statistics"""
    user = get_object_or_404(User, username=username)
    
    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(user=user)
    if created:
        profile.update_counts()
    
    # Get user's threads and posts
    user_threads = Thread.objects.filter(author=user).select_related('category').order_by('-created_at')[:10]
    user_posts = Post.objects.filter(author=user).select_related('thread', 'thread__category').order_by('-created_at')[:20]
    
    # Get bookmarked threads
    bookmarked_threads = []
    if request.user == user:
        bookmarked_threads = Bookmark.objects.filter(user=user).select_related('thread')[:10]
    
    ctx = {
        'profile_user': user,
        'profile': profile,
        'user_threads': user_threads,
        'user_posts': user_posts,
        'bookmarked_threads': bookmarked_threads,
    }
    return render(request, 'forum/user_profile.html', ctx)


def trending_threads(request):
    """Show trending threads based on views and recent activity"""
    from django.db.models import Count, F, Q
    from datetime import timedelta
    
    # Calculate trending score: recent views + recent posts
    recent_date = timezone.now() - timedelta(days=7)
    
    threads = Thread.objects.annotate(
        recent_views=Count('thread_views', filter=Q(thread_views__viewed_at__gte=recent_date)),
        recent_posts=Count('posts', filter=Q(posts__created_at__gte=recent_date)),
    ).annotate(
        trending_score=F('recent_views') + F('recent_posts') * 2
    ).filter(
        trending_score__gt=0
    ).select_related('author', 'category').order_by('-trending_score')[:50]
    
    return render(request, 'forum/trending.html', {'threads': threads})


@login_required
def edit_profile(request):
    """Edit user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile.bio = request.POST.get('bio', '')
        profile.location = request.POST.get('location', '')
        profile.website = request.POST.get('website', '')
        profile.signature = request.POST.get('signature', '')
        profile.save()
        
        messages.success(request, 'Đã cập nhật profile')
        return redirect('forum:user_profile', username=request.user.username)
    
    return render(request, 'forum/edit_profile.html', {'profile': profile})
