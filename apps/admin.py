from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.apps import apps

from .home.models import Sequences, Taxonomies

# Register your models here.
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login') # Added last_login

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

app = apps.get_app_config('apps')
for model_name, model in app.models.items():
    admin.site.register(model)

# admin.site.register(Sequences)
# admin.site.register(Taxonomies)
