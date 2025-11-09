Hướng dẫn chạy nhanh (Windows)

1. Cài Python 3 và XAMPP (bật MySQL trong XAMPP)
2. Tạo database twofa_db và user twofa_user/twofa_pass trong phpMyAdmin
3. Mở terminal tại thư mục C:\code\twofa_site và tạo venv:

   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt

4. Tạo file .env từ .env.example (điền Gmail app password của bạn)
5. Chạy migrate và tạo superuser:

   python manage.py makemigrations accounts forum
   python manage.py migrate
   python manage.py createsuperuser

6. Chạy server dev:

   python manage.py runserver 127.0.0.1:8000

7. Mở http://127.0.0.1:8000/
