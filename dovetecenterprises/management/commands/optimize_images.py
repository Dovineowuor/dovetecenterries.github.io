import os
import sys
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Optimize images by converting them to WebP and creating responsive image sets'

    def add_arguments(self, parser):
        parser.add_argument('--quality', type=int, default=80, help='WebP quality (1-100)')
        parser.add_argument('--widths', type=str, default='300,600,900,1200', help='Comma-separated list of widths')

    def handle(self, *args, **options):
        static_dir = os.path.join(settings.BASE_DIR, 'static')
        image_extensions = ['.jpg', '.jpeg', '.png']
        quality = options['quality']
        widths = [int(w) for w in options['widths'].split(',')]

        for root, dirs, files in os.walk(static_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    try:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, static_dir)
                        
                        # Skip if WebP version already exists
                        webp_path = os.path.splitext(file_path)[0] + '.webp'
                        if os.path.exists(webp_path):
                            continue

                        # Open and optimize the image
                        with Image.open(file_path) as img:
                            # Convert to RGB if necessary (for PNGs with transparency)
                            if img.mode in ('RGBA', 'P'):
                                img = img.convert('RGB')
                            
                            # Save as WebP
                            img.save(webp_path, 'WEBP', quality=quality, method=6)
                            self.stdout.write(self.style.SUCCESS(f'Created: {os.path.relpath(webp_path, settings.BASE_DIR)}'))
                            
                            # Create responsive sizes
                            for width in widths:
                                if img.width > width:
                                    resized_img = img.copy()
                                    resized_img.thumbnail((width, img.height * (width / img.width)), Image.LANCZOS)
                                    
                                    # Save resized WebP
                                    resized_webp_path = f"{os.path.splitext(file_path)[0]}-{width}w.webp"
                                    resized_img.save(resized_webp_path, 'WEBP', quality=quality, method=6)
                                    self.stdout.write(self.style.SUCCESS(f'Created: {os.path.relpath(resized_webp_path, settings.BASE_DIR)}'))
                                    
                                    # Save resized original format
                                    resized_orig_path = f"{os.path.splitext(file_path)[0]}-{width}w{os.path.splitext(file_path)[1]}"
                                    resized_img.save(resized_orig_path, quality=quality, optimize=True)
                                    
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'Error processing {file}: {str(e)}'))
                        continue
