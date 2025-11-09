from django.contrib import admin
from .models import (
    Category, Thread, Post, PostReaction, ProfilePost, 
    Notification, Bookmark, Report, ThreadFollow
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'parent', 'order', 'icon')
    list_filter = ('parent',)
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('order', 'title')

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'prefix', 'pinned', 'locked', 'is_featured', 'views', 'created_at')
    list_filter = ('category', 'pinned', 'locked', 'is_featured', 'created_at')
    search_fields = ('title', 'author__username')
    readonly_fields = ('created_at', 'updated_at', 'views')
    list_editable = ('pinned', 'locked', 'is_featured')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('thread', 'author', 'likes', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__username', 'thread__title')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'created_at')
    list_filter = ('created_at',)

@admin.register(ProfilePost)
class ProfilePostAdmin(admin.ModelAdmin):
    list_display = ('user', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'author__username', 'content')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'sender', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'thread', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'thread__title')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'report_type', 'status', 'created_at', 'resolved_by')
    list_filter = ('report_type', 'status', 'created_at')
    search_fields = ('reporter__username', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status',)

@admin.register(ThreadFollow)
class ThreadFollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'thread', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'thread__title')
