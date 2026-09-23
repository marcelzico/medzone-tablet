from django import forms
from .models import FlashcardSet, Flashcard

class FlashcardSetForm(forms.ModelForm):
    class Meta:
        model = FlashcardSet
        fields = ['title', 'description', 'is_public']
        widgets = {
            'title': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FlashcardForm(forms.ModelForm):
    class Meta:
        model = Flashcard
        fields = ['term', 'definition',]
        widgets = {
            'term': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'definition': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            # 'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Form for creating multiple flashcards at once
class BulkFlashcardForm(forms.Form):
    bulk_data = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Enter terms and definitions separated by tabs or new lines.\nExample:\nTerm1\tDefinition1\nTerm2\tDefinition2'
        }),
        help_text="Enter terms and definitions separated by tabs or on separate lines."
    )



