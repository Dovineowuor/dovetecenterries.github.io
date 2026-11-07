import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ["DJANGO_SETTINGS_MODULE"] = "_test_settings"
django.setup()
from home.models import Newsletter, NewsletterSubscription
n = Newsletter.objects.get(subject="Q3 Innovation Digest - rendering test")
sub = NewsletterSubscription.objects.get(email="owuordove@gmail.com")
url = f"https://dovetecenterprises.site/newsletter/unsubscribe/{sub.token}/"
text = n._build_text_content(tracking_id="TEST-TRACK", unsubscribe_url=url)
os.makedirs("/tmp/opencode/preview", exist_ok=True)
open("/tmp/opencode/preview/newsletter.txt","w").write(text)
print(text)
print("=" * 60)
print("bytes:", len(text), "| css leaked:", "font-family" in text)
