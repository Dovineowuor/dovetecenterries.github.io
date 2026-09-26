from django import forms
from django.core.mail import send_mail
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
        # Logic to send email
        subject = 'New Lead from Advert Contact Form'
        message = f"""
        <html>
        <head>
            <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container">
            <p class="mt-4">Hey {self.cleaned_data['name']},</p>
            <p>You have a new lead into your funnel via the Advert Contact Form.</p>
            <h2 class="mt-4">Lead Details:</h2>
            <table class="table table-bordered mt-3">
                <tr>
                <th>Name</th>
                <td>{self.cleaned_data['name']}</td>
                </tr>
                <tr>
                <th>Email</th>
                <td>{self.cleaned_data['email']}</td>
                </tr>
                <tr>
                <th>Phone</th>
                <td>{self.cleaned_data.get('phone', 'N/A')}</td>
                </tr>
                <tr>
                <th>Company</th>
                <td>{self.cleaned_data.get('company', 'N/A')}</td>
                </tr>
                <tr>
                <th>Interest</th>
                <td>{self.cleaned_data.get('interest', 'N/A')}</td>
                </tr>
                <tr>
                <th>Message</th>
                <td>{self.cleaned_data['message']}</td>
                </tr>
                <tr>
                <th>Advert Timeline</th>
                <td>{self.cleaned_data['timeline']}</td>
                </tr>
                <tr>
                <th>Start Date</th>
                <td>{self.cleaned_data['start_date']}</td>
                </tr>
                <tr>
                <th>End Date</th>
                <td>{self.cleaned_data.get('end_date', 'N/A')}</td>
                </tr>
            </table>
            </div>
        </body>
        </html>
        """
        from_email = 'owuordove@gmail.com'
        recipient_list = ['dovetecenterprises@gmail.com']
        
        send_mail(subject, message, from_email, recipient_list)

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    country = CountryField()
    email = forms.EmailField()
    phone = forms.CharField(max_length=15, required=False)
    message = forms.CharField(widget=forms.Textarea)