from django import forms
from django.utils.translation import gettext_lazy as _

from cove_ocds import models


class UploadForm(forms.ModelForm):
    class Meta:
        model = models.SuppliedData
        fields = ["original_file"]
        labels = {"original_file": _("Upload a file (.json, .csv, .xlsx, .ods)")}


class UrlForm(forms.ModelForm):
    source_url = forms.URLField(required=True, label=_("Supply a URL"))

    class Meta:
        model = models.SuppliedData
        fields = ["source_url"]


class TextForm(forms.Form):
    paste = forms.CharField(label=_("Paste (JSON only)"), widget=forms.Textarea)
