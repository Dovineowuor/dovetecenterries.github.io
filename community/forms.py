from django import forms
from .models import Post, Comment, Reply, Topic


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['topic', 'content']  # Assuming you want to select a topic when creating a post
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your post here...'}),
        }
        labels = {
            'topic': 'Select or Add Topic',
            'content': 'Post Content',
        }

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['topic'].widget = forms.Select(attrs={'class': 'select-or-add'})
        self.fields['topic'].widget.attrs.update({'data-placeholder': 'Select or add a topic'})
        self.fields['topic'].queryset = Topic.objects.all()  # Assuming you have a Topic model
        

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Add a comment...',
                'class': 'form-control'  # Add Bootstrap styling
            }),
        }
        labels = {
            'content': 'Comment',
        }

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if not content or len(content) < 5:  # Minimum length validation
            raise forms.ValidationError('Comment content must be at least 5 characters long.')
        return content

class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Reply to this comment...',
                'class': 'form-control'  # Add Bootstrap styling
            }),
        }
        labels = {
            'content': 'Reply',
        }

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if not content or len(content) < 5:  # Minimum length validation
            raise forms.ValidationError('Reply content must be at least 5 characters long.')
        return content
