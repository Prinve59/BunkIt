from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(label="Library ID", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label="Password", max_length=100, widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    without_event = forms.BooleanField(
        label="Without Event and Medical",
        required=False,  # Optional field
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input ms-2 mt-2'}),
    )
