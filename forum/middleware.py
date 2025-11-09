"""
Middleware to redirect old slugs with Vietnamese characters to new ASCII slugs
"""
from django.shortcuts import redirect
from django.urls import resolve
from unidecode import unidecode
from django.utils.text import slugify
import urllib.parse


class SlugRedirectMiddleware:
    """Redirect URLs with Vietnamese slugs to ASCII slugs"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if URL contains encoded Vietnamese characters
        path = request.path
        
        # Decode URL to get actual Vietnamese text
        decoded_path = urllib.parse.unquote(path)
        
        # If path contains Vietnamese characters, redirect to ASCII version
        if decoded_path != path or any(ord(char) > 127 for char in decoded_path):
            # Convert Vietnamese to ASCII
            parts = decoded_path.split('/')
            new_parts = []
            
            for part in parts:
                if part and any(ord(char) > 127 for char in part):
                    # This part has Vietnamese chars, convert it
                    ascii_part = unidecode(part)
                    new_part = slugify(ascii_part)
                    new_parts.append(new_part)
                else:
                    new_parts.append(part)
            
            new_path = '/'.join(new_parts)
            
            # Only redirect if path actually changed
            if new_path != decoded_path:
                # Preserve query string
                query_string = request.META.get('QUERY_STRING', '')
                if query_string:
                    new_path = f"{new_path}?{query_string}"
                
                return redirect(new_path, permanent=True)
        
        response = self.get_response(request)
        return response
