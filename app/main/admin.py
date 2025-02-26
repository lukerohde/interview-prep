from django.contrib import admin
from .models import Deck, FlashCard

@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('name', 'deck_type', 'owner', 'status', 'created_at', 'updated_at')
    list_filter = ('deck_type', 'status', 'owner')
    search_fields = ('name', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(FlashCard)
class FlashCardAdmin(admin.ModelAdmin):
    list_display = ('front', 'user', 'get_tags_display', 'created_at')
    list_filter = ('user',)
    search_fields = ('front', 'back', 'user__username')
    readonly_fields = ('created_at',)
    filter_horizontal = ('decks',)

    def get_tags_display(self, obj):
        return ', '.join(obj.tags) if obj.tags else ''
    get_tags_display.short_description = 'Tags'