from django import forms
from .models import Thread, Post, Report


class ThreadCreateForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'placeholder': 'Nội dung bài viết...',
            'rows': 8
        }),
        label='Nội dung'
    )
    
    class Meta:
        model = Thread
        fields = ['category', 'prefix', 'title']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input'}),
            'prefix': forms.Select(attrs={'class': 'form-input'}),
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Tiêu đề thread...'
            }),
        }
        labels = {
            'category': 'Chuyên mục',
            'prefix': 'Loại bài',
            'title': 'Tiêu đề',
        }


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Viết phản hồi của bạn...',
                'rows': 5
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-input'
            })
        }
        labels = {
            'content': 'Nội dung',
            'image': 'Hình ảnh'
        }


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['report_type', 'description']
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Mô tả chi tiết vấn đề...',
                'rows': 4
            })
        }
        labels = {
            'report_type': 'Loại vi phạm',
            'description': 'Mô tả'
        }
