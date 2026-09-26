from django import forms
from django.contrib.auth import get_user_model

from app.models import Contact, Organization, ServiceInquiry


class MediaAssetUploadForm(forms.Form):
    file = forms.FileField(help_text='Images, PDFs, office files, text files, or ZIP archives up to 15 MiB.')
    alt_text = forms.CharField(max_length=255, required=False, label='Description')
    is_public = forms.BooleanField(required=False, label='Publicly usable')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget.attrs['class'] = 'form-control'
        self.fields['alt_text'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Describe this asset for staff and accessibility',
        })
        self.fields['is_public'].widget.attrs['class'] = 'form-check-input'


class ServiceInquiryForm(forms.ModelForm):
    """Admin form for creating / editing a sales-funnel lead (ServiceInquiry).

    Excludes auto-managed fields (created_at, stage_updated_at, converted_at)
    and the auto-linked questionnaire, and restricts ``assigned_to`` to staff
    users so the dropdown only lists real sales reps.
    """

    class Meta:
        model = ServiceInquiry
        fields = [
            "organization", "contact", "name", "email", "phone", "service", "message",
            "source", "industry", "budget_range", "timeline", "preferred_contact_method",
            "stage", "estimated_value", "assigned_to", "notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        User = get_user_model()

        # Only real sales reps appear in the assignee dropdown.
        self.fields["assigned_to"].queryset = (
            User.objects.filter(is_staff=True)
            .order_by("first_name", "last_name", "email")
        )
        self.fields["assigned_to"].label_from_instance = lambda obj: (
            f"{obj.get_full_name() or obj.email}"
        )
        self.fields["assigned_to"].empty_label = "— Unassigned —"

        # Present stages in pipeline order, with Lost kept last.
        stages = ServiceInquiry.PIPELINE_STAGES + [ServiceInquiry.STAGE_LOST]
        self.fields["stage"].choices = [
            (s, dict(ServiceInquiry.STAGE_CHOICES)[s]) for s in stages
        ]

        self.fields["name"].help_text = "Lead / prospect name."
        self.fields['organization'].queryset = Organization.objects.all()
        self.fields['contact'].queryset = Contact.objects.select_related('organization').all()
        self.fields['organization'].empty_label = '— No organization —'
        self.fields['contact'].empty_label = '— No contact record —'
        self.fields['organization'].help_text = 'Company or institution that owns this opportunity.'
        self.fields['contact'].help_text = 'Primary person associated with the enquiry.'
        self.fields["email"].help_text = "Contact email — also used to match the client portal."
        self.fields["phone"].help_text = "Optional phone number."
        self.fields["service"].help_text = "Service the lead is interested in."
        self.fields["message"].help_text = "Original inquiry / what they're looking for."
        self.fields["stage"].help_text = "Current stage in the sales funnel."
        self.fields["estimated_value"].help_text = "Estimated deal value (KES)."
        self.fields["assigned_to"].help_text = "Sales rep responsible for this lead."
        self.fields["notes"].help_text = "Internal follow-up notes (not shown to the client)."
