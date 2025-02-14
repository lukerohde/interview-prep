from django.contrib import admin
from .models import Application, FlashCard

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'owner')
    search_fields = ('name', 'owner__username', 'job_description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(FlashCard)
class FlashCardAdmin(admin.ModelAdmin):
    list_display = ('front', 'user', 'get_tags_display', 'created_at')
    list_filter = ('user',)
    search_fields = ('front', 'back', 'user__username')
    readonly_fields = ('created_at',)
    filter_horizontal = ('applications',)

    def get_tags_display(self, obj):
        return ', '.join(obj.tags) if obj.tags else ''
    get_tags_display.short_description = 'Tags'