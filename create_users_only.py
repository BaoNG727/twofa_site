#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django
import random
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twofa_site.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from forum.models import UserProfile
from faker import Faker

User = get_user_model()
fake = Faker(['vi_VN', 'en_US'])

def create_users(num_users=250):
    print(f"Creating {num_users} users...")
    created = 0
    
    for i in range(num_users):
        username = fake.user_name() + str(random.randint(1000, 9999))
        email = f"{username}@example.com"
        
        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            continue
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123'
            )
            
            UserProfile.objects.create(
                user=user,
                bio=fake.text(max_nb_chars=200) if random.random() > 0.5 else '',
                location=fake.city() if random.random() > 0.6 else '',
                website=fake.url() if random.random() > 0.7 else '',
                reputation=random.randint(0, 5000),
                joined_date=timezone.now() - timedelta(days=random.randint(1, 365)),
                last_activity=timezone.now() - timedelta(hours=random.randint(1, 72))
            )
            
            created += 1
            
            if created % 50 == 0:
                print(f"  Created {created} users...")
                
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    print(f"[OK] Created {created} users")
    print(f"Total users now: {User.objects.count()}")

if __name__ == '__main__':
    create_users(250)
