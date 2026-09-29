from django import forms
from datetime import timedelta
from django_countries.fields import CountryField

class AdvertContactForm(forms.Form):
    name = forms.CharField(max_length=100, required=True, label='Your Name')
    email = forms.EmailField(required=True, label='Your Email')
    phone = forms.CharField(max_length=15, required=False, label='Your Phone Number')
    company = forms.CharField(max_length=100, required=False, label='Yoyr Company')
    interest = forms.CharField(max_length=100, required=False, label='Area of Interest')
    message = forms.CharField(widget=forms.Textarea, required=True, label='Your Message')
    timeline = forms.ChoiceField(choices=[
        ('1', 'Within 1 month'),
        ('2', '1-3 months'),
        ('3', '3-6 months'),
        ('4', '6+ months')
    ], required=True, label='Advert Timeline')
    start_date = forms.DateField(required=True, label='Start Date')
    end_date = forms.DateField(required=False, label='End Date')

    def clean_end_date(self):
        start_date = self.cleaned_data.get('start_date')
        timeline = self.cleaned_data.get('timeline')

        if not start_date or not timeline:
            return None


        if timeline == '1':
            end_date = start_date + timedelta(days=30)
        elif timeline == '2':
            end_date = start_date + timedelta(days=90)
        elif timeline == '3':
            end_date = start_date + timedelta(days=180)
        elif timeline == '4':
            end_date = start_date + timedelta(days=180)  # Assuming 6+ months means 6 months for default

        return end_date

    
    def send_email(self):
        """Notify the sales inbox about a new advert lead."""
        from django.conf import settings

        from home.email import send_styled_email

        data = self.cleaned_data
        subject = f"New advert lead from {data['name']}"
        recipient = getattr(settings, 'ADVERT_EMAIL', None) or getattr(
            settings, 'CONTACT_EMAIL', None
        ) or settings.DEFAULT_FROM_EMAIL
        timelines = dict(self.fields['timeline'].choices)

        return send_styled_email(
            subject,
            'emails/notification.html',
            {
                'heading': 'New advert lead',
                'preheader': f"{data['name']} enquired about advertising space",
                'intro': 'Someone submitted the advertise-with-us form.',
                'details': [
                    ('Name', data['name']),
                    ('Email', data['email']),
                    ('Phone', data.get('phone')),
                    ('Company', data.get('company')),
                    ('Interest', data.get('interest')),
                    ('Timeline', timelines.get(data.get('timeline'))),
                    ('Start date', data.get('start_date')),
                    ('End date', data.get('end_date')),
                ],
                'body': data['message'],
                'reply_hint': data['name'],
            },
            [recipient],
            reply_to=[data['email']] if data.get('email') else None,
            fail_silently=True,
        )

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    country = CountryField()
    email = forms.EmailField()
    phone = forms.CharField(max_length=15, required=False)
    message = forms.CharField(widget=forms.Textarea)