from django.urls import path
from . import views

app_name = "forum"

urlpatterns = [
    # Danh sách thread mới nhất
    path("", views.home, name="home"),
    
    # Category view
    path("category/<path:slug>/", views.category_view, name="category_view"),

    # Tạo thread mới
    path("new/", views.thread_create, name="thread_create"),

    # Xem chi tiết thread
    path("thread/<int:pk>/", views.thread_detail, name="thread_detail"),
    
    # Posts mới nhất
    path("new-posts/", views.new_posts, name="new_posts"),
    
    # Hoạt động gần đây
    path("latest/", views.latest_activity, name="latest_activity"),
    
    # Nội dung nổi bật
    path("featured/", views.featured_content, name="featured_content"),
    
    # Profile user
    path("profile/<str:username>/", views.profile_view, name="profile"),
    
    # Search
    path("search/", views.search, name="search"),
    
    # Notifications
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/count/', views.notification_count, name='notification_count'),

    # Bookmarks
    path('bookmarks/', views.bookmarks_list, name='bookmarks'),
    path('thread/<int:thread_id>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('thread/<int:thread_id>/follow/', views.thread_follow_toggle, name='thread_follow_toggle'),

    # Reports
    path('report/thread/<int:thread_id>/', views.report_create, name='report_thread'),
    path('report/post/<int:post_id>/', views.report_create, name='report_post'),
    
    # Reactions
    path('post/<int:post_id>/react/', views.toggle_reaction, name='toggle_reaction'),
    
    # User Profile (Enhanced)
    path('user/<str:username>/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Trending
    path('trending/', views.trending_threads, name='trending'),
]
