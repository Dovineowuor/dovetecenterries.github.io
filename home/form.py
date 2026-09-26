from django import forms
from froala_editor.widgets import FroalaEditor
from .models import Article, Profile, Tag, User

class BlogForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['is_verified', 'token']

class ArticleForm(forms.ModelForm):
    category = forms.CharField(max_length=100, required=False, label='Category')  # Add category field with a label
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # CheckboxSelectMultiple allows multiple selections
        required=False,
        label='Tags'  # Label for clarity
    )

    class Meta:
        model = Article
        fields = ['title', 'content', 'image', 'category', 'tags']  # Include category and tags
        widgets = {
            'content': FroalaEditor(),  # Use FroalaEditor for content field
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get('title')
        content = cleaned_data.get('content')

        if title and content:
            if 'Django' not in title and 'Django' not in content:
                self.add_error('title', 'Title or content must contain the word "Django"') # Add error to title field
                self.add_error('content', 'Title or content must contain the word "Django"')
        return cleaned_data
    
    def save(self, commit=True):
        article = super().save(commit=False)
        article.category = self.cleaned_data.get('category')
        if commit:
            article.save()
        return article
    
    def save_m2m(self):
        article = self.instance
        article.tags.set(self.cleaned_data['tags'])
        article.save()
        return article
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError('Image file too large ( > 2mb )')
        return image
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content:
            if 'bad word' in content:
                raise forms.ValidationError('Content contains inappropriate language')
        return content
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            if 'bad word' in title:
                raise forms.ValidationError('Title contains inappropriate language')
        return title
    
    def clean_tags(self):
        tags = self.cleaned_data.get('tags')
        if tags:
            if len(tags) > 3:
                raise forms.ValidationError('Maximum of 3 tags allowed')
        return tags
    
    def clean_category(self):
        category = self.cleaned_data.get('category')
        if category:
            if 'bad word' in category:
                raise forms.ValidationError('Category contains inappropriate language')
        return category
    
    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get('title')
        content = cleaned_data.get('content')

        if title and content:
            if 'Django' not in title and 'Django' not in content:
                self.add_error('title', 'Title or content must contain the word "Django"')

        return cleaned_data
    
class SearchForm(forms.Form):
    query = forms.CharField(max_length=100, label='Search')
    
    def clean_query(self):
        query = self.cleaned_data.get('query')
        if query:
            if 'bad word' in query:
                raise forms.ValidationError('Query contains inappropriate language')
        return query
    

class RegistrationForm(forms.Form):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

    def clean_email(self):
        """Validate that the email is not already in use."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email is already registered.')
        return email
          
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Passwords do not match')
            
        return cleaned_data
