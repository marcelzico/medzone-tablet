from django.db import models
from utilisateur.models import User
from django.urls import reverse
from lecon.models import Chapter, Unite
from django.utils import timezone

class FlashcardSet(models.Model):
    title = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)
    
    def __str__(self):
        return str(self.title)
    
    def get_absolute_url(self):
        return reverse('quizlet_copy:set-detail', kwargs={'pk': self.pk})
    class Meta:
        indexes = [
            # Enhanced indexes
            models.Index(fields=['created_by', 'is_public', '-created_at']),  # User's public sets
            models.Index(fields=['is_public', '-created_at']),  # Public sets by date
            models.Index(fields=['created_by', '-created_at']),  # User's all sets by date
            models.Index(fields=['title', 'is_public']),  # Chapter's public sets
            models.Index(fields=['updated_at']),  # For update tracking
            models.Index(fields=['created_by', 'title']),  # User's set for a chapter
        ]


class Flashcard(models.Model):
    flashcard_set = models.ForeignKey(FlashcardSet, on_delete=models.CASCADE, related_name='cards')
    term = models.TextField()
    definition = models.TextField()
    # order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            # Enhanced indexes
            models.Index(fields=['flashcard_set', '-created_at']),  # Cards in set by date
            models.Index(fields=['flashcard_set']),  # Search term within set
            models.Index(fields=['-created_at']),  # All cards by date
        ]
    
    def __str__(self):
        return f"{self.term} - {self.definition[:50]}..."


class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE)
    mastered = models.BooleanField(default=False)
    times_studied = models.IntegerField(default=0)
    last_studied = models.DateTimeField(auto_now=True)
    confidence_level = models.IntegerField(default=0)  # 1-3 scale
    next_review_date = models.DateTimeField(null=True, blank=True)
    
    # Add unique constraint to prevent duplicates
    class Meta:
        unique_together = ['user', 'flashcard']
        ordering = ['-last_studied']
        indexes = [
            # Enhanced indexes
            models.Index(fields=['user', 'mastered']),  # User's mastered cards
            models.Index(fields=['user', 'confidence_level']),  # User's confidence levels
            models.Index(fields=['user', 'next_review_date']),  # User's review schedule
            models.Index(fields=['next_review_date', 'user']),  # Global review schedule
            models.Index(fields=['user', 'times_studied']),  # User's study frequency
            models.Index(fields=['flashcard', 'mastered']),  # Card mastery statistics
            models.Index(fields=['last_studied']),  # Global last studied
            models.Index(fields=['user', '-last_studied']),  # User's recent study activity
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.flashcard.term[:20]}"
    
    def update_progress(self, confidence):
        """Update progress based on confidence rating (1-3)"""
        from django.utils import timezone
        
        self.times_studied += 1
        self.last_studied = timezone.now()
        self.confidence_level = confidence
        self.mastered = confidence == 3
        
        # Simple spaced repetition algorithm
        if confidence == 1:  # Didn't know - review soon
            self.next_review_date = timezone.now() + timezone.timedelta(minutes=30)
        elif confidence == 2:  # Almost knew - review later
            self.next_review_date = timezone.now() + timezone.timedelta(hours=24)
        elif confidence == 3:  # Knew it - review in a week
            self.next_review_date = timezone.now() + timezone.timedelta(days=7)
        
        self.save()
        return self