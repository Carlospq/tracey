from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.apps import apps
from django.db.models import Count

from .home.models import Sequences, Taxonomies


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login')


class TaxonomiesAdmin(admin.ModelAdmin):
    list_display  = ['taxonomy_id', 'scientificname', 'commonname', 'taxonomyrank',
                     'taxonomystatus', 'analysislevel', 'ncbi_taxonomy_id', 'sequence_count']
    search_fields = ['scientificname', 'commonname', 'taxonomyshortname', 'ncbi_taxonomy_id']
    list_filter   = ['taxonomyrank', 'taxonomystatus', 'analysislevel']
    ordering      = ['scientificname']
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(sequences_count=Count('sequences'))

    @admin.display(description='Sequences', ordering='sequences_count')
    def sequence_count(self, obj):
        return obj.sequences_count


class SequencesAdmin(admin.ModelAdmin):
    list_display  = ['sequence_id', 'sequenceshortname', 'sequencetype',
                     'sequencestatus', 'taxonomy', 'sourcedatabase', 'private']
    search_fields = ['sequenceshortname', 'annotation', 'foreignannotation', 'dbxref', 'aliases']
    list_filter   = ['sequencetype', 'sequencestatus', 'sourcedatabase', 'private']
    ordering      = ['sequenceshortname']
    list_per_page = 50
    raw_id_fields = ['taxonomy', 'gene']


CUSTOM_ADMINS = {
    'taxonomies': TaxonomiesAdmin,
    'sequences':  SequencesAdmin,
}

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

app = apps.get_app_config('apps')
for model_name, model in app.models.items():
    admin_class = CUSTOM_ADMINS.get(model_name, admin.ModelAdmin)
    admin.site.register(model, admin_class)
