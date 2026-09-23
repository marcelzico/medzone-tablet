# quizlet/urls.py
from django.urls import path
from . import views

app_name = 'quizlet_copy'

urlpatterns = [
    # FlashcardSet CRUD
    path('set/new/', views.FlashcardSetCreateView.as_view(), name='set-create'),
    path('set/<int:pk>/', views.FlashcardSetDetailView.as_view(), name='set-detail'),
    path('set/<int:pk>/update/', views.FlashcardSetUpdateView.as_view(), name='set-update'),
    path('set/<int:pk>/delete/', views.FlashcardSetDeleteView.as_view(), name='set-delete'),
     
    # Flashcard CRUD
    path('set/<int:pk>/add-card/', views.add_flashcard, name='add-card'),
    path('flashcard/<int:pk>/update/', views.FlashcardUpdateView.as_view(), name='flashcard-update'),
    path('flashcard/<int:pk>/delete/', views.FlashcardDeleteView.as_view(), name='flashcard-delete'),
    path('set/<int:pk>/bulk-add/', views.bulk_add_flashcards, name='bulk-add'),
    
    # Study Modes
    path('set/<int:pk>/study/', views.study_flashcards, name='study'),
    # path('set/<int:pk>/match/', views.match_game, name='match-game'),
    
    # Other views
    path('my-sets/', views.UserFlashcardSetListView.as_view(), name='my-sets'),
    path('', views.FlashcardSetListView.as_view(), name='home'),

    # Create set chapter
    path('create-set-chapter-private/<int:chapter_id>/', views.create_set_chapter_pivate, name= 'create-set-chapter-private'),
    path('create-set-chapter-public/<int:chapter_id>/', views.create_set_chapter_public, name= 'create-set-chapter-public'),

    path('api/record-progress/', views.record_progress, name='record-progress'),
    path('api/progress-summary/<int:pk>/', views.get_progress_summary, name='progress-summary'),
]
