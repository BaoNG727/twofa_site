#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twofa_site.settings')
django.setup()

from forum.models import Category
from django.utils.text import slugify
from unidecode import unidecode

def fix_category_slugs():
    categories = Category.objects.all()
    
    print(f"Fixing slugs for {categories.count()} categories...")
    
    for cat in categories:
        old_slug = cat.slug
        # Convert to ASCII then slugify
        ascii_title = unidecode(cat.title)
        new_slug = slugify(ascii_title)
        
        # Ensure unique
        counter = 1
        temp_slug = new_slug
        while Category.objects.filter(slug=temp_slug).exclude(pk=cat.pk).exists():
            temp_slug = f"{new_slug}-{counter}"
            counter += 1
        
        cat.slug = temp_slug
        cat.save()
    
    print("[OK] Done!")

if __name__ == '__main__':
    fix_category_slugs()
