from django.contrib import admin
from . models import Flashcard, FlashcardSet, UserProgress

# Register your models here.
@admin.register(FlashcardSet)
class FlashcardSetAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'is_public', 'created_at', 'updated_at')
    list_filter = ('title', 'created_by', 'is_public')
    search_fields = ('title', 'created_by', 'is_public')
    raw_id_fields = ('title',)

@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('flashcard_set', 'term', 'definition', 'created_at')
    list_filter = ('term', 'definition')
    search_fields = ('flashcard_set', 'term', 'definition')
    raw_id_fields = ('flashcard_set',)


@admin.register(UserProgress)
class UserProgress(admin.ModelAdmin):
    list_display = ('user', 'flashcard', 'mastered', 'times_studied')
