from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from forum import views as forum_views

urlpatterns = [
    # admin Django
    path("admin/", admin.site.urls),

    # Trang chủ site -> cũng xài forum_views.home
    path("", forum_views.home, name="root_home"),

    # /forum/... -> include forum.urls dùng cùng home()
    path("forum/", include(("forum.urls", "forum"), namespace="forum")),

    # /accounts/... -> login/register/2FA/email/...
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
