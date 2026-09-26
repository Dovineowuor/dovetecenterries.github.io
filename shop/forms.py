from django import forms

class OrderForm(forms.Form):
    product_id = forms.IntegerField(label='Product ID', required=True)
    quantity = forms.IntegerField(label='Quantity', required=True, min_value=1)
    customer_name = forms.CharField(label='Customer Name', max_length=100, required=True)
    customer_email = forms.EmailField(label='Customer Email', required=True)
    shipping_address = forms.CharField(label='Shipping Address', widget=forms.Textarea, required=True)
    phone_number = forms.CharField(label='Phone Number', max_length=15, required=True)
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise forms.ValidationError('Quantity must be greater than zero.')
        return quantity