from django.contrib.auth import get_user_model
from .models import Thread, Post

User = get_user_model()

def admin_stats(request):
    """Context processor to add stats to admin dashboard"""
    if request.path.startswith('/admin/'):
        return {
            'user_count': User.objects.count(),
            'thread_count': Thread.objects.count(),
            'post_count': Post.objects.count(),
        }
    return {}
