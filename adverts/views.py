from django.shortcuts import render

# Create your views here.
# adverts/views.py

from django.shortcuts import render
from .models import Advertisement
from django import forms
from django.http import HttpResponseRedirect
from .forms import ContactForm  # Import ContactForm from forms module

def advertise_view(request):
    # Fetch all active advertisements from the database
    ads = Advertisement.objects.all()  # You can add filtering criteria if needed
    return render(request, 'advertise.html', {'ads': ads})

def company_view(request):
    return render(request, 'company.html')



def advert_contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Process the data in form.cleaned_data
            # For example, send an email or save to the database
            return HttpResponseRedirect('/thanks/')
    else:
        form = ContactForm()

    return render(request, 'advert_contact.html', {'form': form})

def test_session_view(request):
    if request.method == 'POST':
        request.session['test_key'] = request.POST.get('test_value', 'default_value')
    
    test_value = request.session.get('test_key', 'Not set')
    return render(request, 'test_session.html', {'test_value': test_value})

def test_cookie_view(request):
    response = render(request, 'test_cookie.html')
    response.set_cookie('test_cookie', 'cookie_value')
    return response


