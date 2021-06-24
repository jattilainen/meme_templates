from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from .models import Template

@admin.register(Template)
class TemplateAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    pass
