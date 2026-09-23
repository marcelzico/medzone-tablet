# views.py - UPDATED WITH SECURITY CONTROLS
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import FlashcardSet, Flashcard, UserProgress
from .forms import FlashcardSetForm, FlashcardForm, BulkFlashcardForm
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
import json
from django.urls import reverse, reverse_lazy
from django.views.generic import UpdateView, DeleteView
from lecon.models import Chapter, Unite
from django.utils import timezone
from django.db.models import Q
from utilisateur.models import User
from subscriptions.decorators import (student_required, active_subscription_required,
                                      method_active_subscription_required, non_student_required,
                                      ActiveSubscriptionRequiredMixin)
from django.utils.decorators import method_decorator

# ========== PERMISSION CHECK FUNCTIONS ==========

def is_staff_or_superuser(user):
    """Check if user is staff or superuser"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_set_owner(user, flashcard_set):
    """Check if user owns the flashcard set"""
    return user.is_authenticated and flashcard_set.created_by == user


def can_modify_public_set(user, flashcard_set):
    """Check if user can modify a public set (staff/superuser or owner)"""
    if not user.is_authenticated:
        return False
    
    if flashcard_set.is_public:
        # For public sets: only staff/superuser or owner can modify
        return is_staff_or_superuser(user) or is_set_owner(user, flashcard_set)
    else:
        # For private sets: only owner can modify
        return is_set_owner(user, flashcard_set)


def can_modify_flashcard(user, flashcard):
    """Check if user can modify a flashcard"""
    return can_modify_public_set(user, flashcard.flashcard_set)


def can_view_set(user, flashcard_set):
    """Check if user can view a flashcard set"""
    if flashcard_set.is_public:
        # Public sets are visible to everyone
        return True
    else:
        # Private sets are only visible to owner
        return user.is_authenticated and is_set_owner(user, flashcard_set)


# ========== MIXIN CLASSES ==========

class StaffOrSuperuserRequiredMixin(UserPassesTestMixin):
    """Mixin to require staff or superuser status"""
    
    def test_func(self):
        return is_staff_or_superuser(self.request.user)
    
    def handle_no_permission(self):
        messages.error(self.request, "Vous n'avez pas la persmission d'effectuer cette action.")
        return redirect('quizlet_copy:home')


class SetOwnerOrStaffRequiredMixin(UserPassesTestMixin):
    """Mixin to require set ownership or staff status"""
    
    def test_func(self):
        obj = self.get_object()
        return can_modify_public_set(self.request.user, obj)
    
    def handle_no_permission(self):
        messages.error(self.request, "Vous n'avez pas la persmission d'effectuer cette action.")
        if self.request.user.is_authenticated:
            return redirect('quizlet_copy:my-sets')
        else:
            return redirect('utilisateur:dashboard')


class FlashcardOwnerOrStaffRequiredMixin(UserPassesTestMixin):
    """Mixin to require flashcard ownership or staff status"""
    
    def test_func(self):
        flashcard = self.get_object()
        return can_modify_flashcard(self.request.user, flashcard)
    
    def handle_no_permission(self):
        messages.error(self.request, "Vous n'avez pas la persmission d'effectuer cette action.")
        flashcard = self.get_object()
        return redirect('quizlet_copy:set-detail', pk=flashcard.flashcard_set.pk)



# ========== VIEW CLASSES WITH SECURITY ==========

class FlashcardSetListView(ActiveSubscriptionRequiredMixin, ListView):
    """Public flashcard sets list - visible to everyone"""
    model = FlashcardSet
    template_name = 'quizlet_copy/home.html'
    context_object_name = 'sets'

    
    def get_queryset(self):
        # Only show public sets to everyone
        return FlashcardSet.objects.filter(is_public=True).order_by('-created_at')


class UserFlashcardSetListView(LoginRequiredMixin, ListView):
    """User's private flashcard sets list"""
    model = FlashcardSet
    template_name = 'quizlet_copy/my_sets.html'
    context_object_name = 'sets'
    
    def get_queryset(self):
        # Show user's own sets (both public and private)
        return FlashcardSet.objects.filter(created_by=self.request.user).order_by('-created_at')
    

class FlashcardSetDetailView(ActiveSubscriptionRequiredMixin, DetailView):
    """Flashcard set detail view with permission check"""
    model = FlashcardSet
    template_name = 'quizlet_copy/set_detail.html'
    context_object_name = 'flashcard_set'
    
    def dispatch(self, request, *args, **kwargs):
        # Get the object first
        self.object = self.get_object()
        
        # Check if user can view this set
        if not can_view_set(request.user, self.object):
            if request.user.is_authenticated:
                messages.error(request, "vous n'avez pas la permission de regarder cet ensemble.")
                return redirect('quizlet_copy:my-sets')
            else:
                messages.error(request, "Vous devez vous connecter pour pouvoir regarder cette page.")
                return redirect('login')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add permission flags to template context
        context['can_modify_set'] = can_modify_public_set(self.request.user, self.object)
        context['is_owner'] = is_set_owner(self.request.user, self.object)
        return context


class FlashcardSetCreateView(ActiveSubscriptionRequiredMixin, CreateView):
    """Create flashcard set - logged in users only"""
    model = FlashcardSet
    form_class = FlashcardSetForm
    template_name = 'quizlet_copy/set_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "L'ensemble de la carte mentale a été créé avec succès")
        return super().form_valid(form)

    
class FlashcardSetUpdateView(LoginRequiredMixin, SetOwnerOrStaffRequiredMixin, UpdateView):
    """Update flashcard set - owner or staff only"""
    model = FlashcardSet
    fields = ['title', 'description', 'is_public']
    template_name = 'quizlet_copy/set_form.html'
    
    def form_valid(self, form):
        # Only staff/superuser can change is_public if they don't own the set
        if not is_set_owner(self.request.user, self.get_object()):
            if 'is_public' in form.changed_data:
                if not is_staff_or_superuser(self.request.user):
                    messages.warning(self.request, "Seul l'admin ou les membres du staff peuvent modifier la visibilité de l'ensemble qui ne leur appartient pas.")
                    form.instance.is_public = self.get_object().is_public  # Revert change
        
        messages.success(self.request, "L'ensemble a été modifié avec succès!")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_owner'] = is_set_owner(self.request.user, self.get_object())
        return context


class FlashcardSetDeleteView(LoginRequiredMixin, SetOwnerOrStaffRequiredMixin, DeleteView):
    """Delete flashcard set - owner or staff only"""
    model = FlashcardSet
    template_name = 'quizlet_copy/set_confirm_delete.html'
    
    def get_success_url(self):
        if is_set_owner(self.request.user, self.object):
            return reverse_lazy('quizlet_copy:my-sets')
        else:
            return reverse_lazy('quizlet_copy:home')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "L'ensemble a été supprimé avec succès!")
        return super().delete(request, *args, **kwargs)


# ========== FLASHCARD CRUD VIEWS ==========

@login_required
@active_subscription_required(feature="can_view_quizlet")
def add_flashcard(request, pk):
    """Add flashcard to set - owner or staff only"""
    flashcard_set = get_object_or_404(FlashcardSet, pk=pk)
    
    # Check permission
    if not can_modify_public_set(request.user, flashcard_set):
        messages.error(request, "Vous n'avez pas la permission d'ajouter des cartes mentales dans cet ensemble.")
        return redirect('quizlet_copy:set-detail', pk=pk)
    
    if request.method == 'POST':
        form = FlashcardForm(request.POST)
        if form.is_valid():
            flashcard = form.save(commit=False)
            flashcard.flashcard_set = flashcard_set
            flashcard.save()
            messages.success(request, "La carte mentale a été ajouté avec succès!")
            return redirect('quizlet_copy:set-detail', pk=pk)
    else:
        form = FlashcardForm()
    
    return render(request, 'quizlet_copy/flashcard_form.html', {
        'form': form,
        'set': flashcard_set,
        'can_modify': True
    })


class FlashcardUpdateView(LoginRequiredMixin, FlashcardOwnerOrStaffRequiredMixin, UpdateView):
    """Update flashcard - owner or staff only"""
    model = Flashcard
    form_class = FlashcardForm
    template_name = 'quizlet_copy/flashcard_form.html'
    
    def get_success_url(self):
        messages.success(self.request, "La carte mentale a été modifiée avec succès!")
        return reverse_lazy('quizlet_copy:set-detail', kwargs={'pk': self.object.flashcard_set.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['set'] = self.object.flashcard_set
        context['can_modify'] = can_modify_public_set(self.request.user, self.object.flashcard_set)
        return context


class FlashcardDeleteView(LoginRequiredMixin, FlashcardOwnerOrStaffRequiredMixin, DeleteView):
    """Delete flashcard - owner or staff only"""
    model = Flashcard
    template_name = 'quizlet_copy/flashcard_confirm_delete.html'
    
    def get_success_url(self):
        messages.success(self.request, "La carte mentale a été supprimée avec succès!")
        return reverse_lazy('quizlet_copy:set-detail', kwargs={'pk': self.object.flashcard_set.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['set'] = self.object.flashcard_set
        context['can_modify'] = can_modify_public_set(self.request.user, self.object.flashcard_set)
        return context


# ========== BULK OPERATIONS ==========

@login_required
@active_subscription_required(feature="can_view_quizlet")
def bulk_add_flashcards(request, pk):
    """Bulk add flashcards - owner or staff only"""
    flashcard_set = get_object_or_404(FlashcardSet, pk=pk)
    
    # Check permission
    if not can_modify_public_set(request.user, flashcard_set):
        messages.error(request, "Vous n'avez pas la permission d'ajouter des cartes mentales dans cet ensemble.")
        return redirect('quizlet_copy:set-detail', pk=pk)
    
    if request.method == 'POST':
        bulk_data = request.POST.get('bulk_data', '')
        lines = bulk_data.strip().split('\n')
        count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try different separators
            if ':' in line:
                parts = line.split(':', 1)
            elif '\t' in line:
                parts = line.split('\t', 1)
            elif '|' in line:
                parts = line.split('|', 1)
            elif '-' in line:
                parts = line.split('-', 1)
            else:
                continue
            
            if len(parts) == 2:
                term = parts[0].strip()
                definition = parts[1].strip()
                
                if term and definition:
                    Flashcard.objects.create(
                        flashcard_set=flashcard_set,
                        term=term,
                        definition=definition,
                    )
                    count += 1
        
        messages.success(request, f"{count} cartes mentales ont été ajoutée avec succès!" )
        return redirect('quizlet_copy:set-detail', pk=pk)
    
    return render(request, 'quizlet_copy/bulk_add.html', {
        'set': flashcard_set,
        'can_modify': True
    })


# ========== STUDY MODES ==========

# In views.py, update the study_flashcards function or add a new parameter

@login_required
@active_subscription_required(feature="can_practice_quizlet_learning_mode")
def study_flashcards(request, pk):
    """Study flashcards - requires view permission"""
    flashcard_set = get_object_or_404(FlashcardSet, pk=pk)
    
    # Check if user can view this set
    if not can_view_set(request.user, flashcard_set):
        messages.error(request, "Vous n'avez pas la permission de voir cet ensemble!")
        return redirect('quizlet_copy:my-sets')
    
    cards = flashcard_set.cards.all()
    
    # Get user's progress for these flashcards
    user_progress = UserProgress.objects.filter(
        user=request.user,
        flashcard__in=cards
    ).select_related('flashcard')
    
    # Create a dictionary for quick lookup
    progress_dict = {}
    for progress in user_progress:
        progress_dict[progress.flashcard_id] = {
            'times_studied': progress.times_studied,
            'mastered': progress.mastered,
            'confidence_level': progress.confidence_level,
        }
    
    # Get study mode from URL parameter
    mode = request.GET.get('mode', 'flashcards')
    
    # Check if we need to reset progress for restart
    reset = request.GET.get('reset', 'false') == 'true'
    
    # Prepare cards data with progress info for JavaScript
    cards_with_progress = []
    for card in cards:
        progress = progress_dict.get(card.id)
        # If reset is requested, reset mastered status
        mastered_status = False if reset else (progress['mastered'] if progress else False)
        times_studied_val = 0 if reset else (progress['times_studied'] if progress else 0)
        confidence_val = 0 if reset else (progress['confidence_level'] if progress else 0)
        
        cards_with_progress.append({
            'id': card.id,
            'term': card.term,
            'definition': card.definition,
            'timesStudied': times_studied_val,
            'mastered': mastered_status,
            'confidence': confidence_val,
        })
    
    context = {
        'set': flashcard_set,
        'cards': cards,
        'cards_json': json.dumps(cards_with_progress),
        'progress_data': progress_dict,
        'mode': mode,
        'can_modify_set': can_modify_public_set(request.user, flashcard_set),
        'reset_requested': reset,
    }
    
    # If mode is learn and reset is requested, ensure we show learn mode
    if mode == 'learn' and reset:
        return render(request, 'quizlet_copy/study_mode.html', context)
    
    return render(request, 'quizlet_copy/study_mode.html', context)


@login_required
@active_subscription_required(feature="can_practice_quizlet_learning_mode")
def learn_mode(request, pk):
    """Learn mode - requires view permission"""
    flashcard_set = get_object_or_404(FlashcardSet, pk=pk)
    
    # Check if user can view this set
    if not can_view_set(request.user, flashcard_set):
        messages.error(request, "Vous n'avez pas la permission de voir cet ensemble!")
        return redirect('quizlet_copy:my-sets')
    
    cards = flashcard_set.cards.all()
    cards_to_review = cards.order_by('?')[:5]
    
    context = {
        'set': flashcard_set,
        'cards_to_review': cards_to_review,
        'can_modify_set': can_modify_public_set(request.user, flashcard_set),
    }
    
    return render(request, 'quizlet_copy/learn_mode.html', context)


# @login_required
# @active_subscription_required(feature="can_view_quizlet")
# def match_game(request, pk):
#     """Match game - requires view permission"""
#     flashcard_set = get_object_or_404(FlashcardSet, pk=pk)
    
#     # Check if user can view this set
#     if not can_view_set(request.user, flashcard_set):
#         messages.error(request, "Vous n'avez pas la permission de jouer aux de cet ensemble!")
#         return redirect('quizlet_copy:my-sets')
    
#     cards = list(flashcard_set.cards.all())
    
#     context = {
#         'set': flashcard_set,
#         'cards': cards,
#         'can_modify_set': can_modify_public_set(request.user, flashcard_set),
#     }
    
#     return render(request, 'quizlet_copy/match_game.html', context)


# # ========== API VIEWS ==========

# @require_POST
# @login_required
# @active_subscription_required(feature="can_view_quizlet")
# def check_match(request):
#     """Check match in game - requires view permission for the set"""
#     try:
#         data = json.loads(request.body)
#         term_id = data.get('term_id')
#         definition_id = data.get('definition_id')
        
#         # Get flashcards
#         term = get_object_or_404(Flashcard, id=term_id)
#         definition = get_object_or_404(Flashcard, id=definition_id)
        
#         # Check if user can view both cards' sets
#         if not can_view_set(request.user, term.flashcard_set) or \
#            not can_view_set(request.user, definition.flashcard_set):
#             return JsonResponse({'error': 'Permission denied'}, status=403)
        
#         # Check if they match
#         is_match = (term.id == definition.id)
        
#         return JsonResponse({
#             'is_match': is_match,
#             'term': term.term,
#             'definition': definition.definition
#         })
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
@active_subscription_required(feature="can_view_quizlet")
def record_progress(request):
    """Record user progress - requires view permission"""
    try:
        data = json.loads(request.body)
        flashcard_id = data.get('flashcard_id')
        confidence = int(data.get('confidence', 2))
        
        flashcard = get_object_or_404(Flashcard, id=flashcard_id)
        
        # Check if user can view this flashcard's set
        if not can_view_set(request.user, flashcard.flashcard_set):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get or create user progress
        progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            flashcard=flashcard,
            defaults={
                'times_studied': 1,
                'confidence_level': confidence,
                'mastered': confidence == 3
            }
        )
        
        if not created:
            # Update existing progress
            progress.update_progress(confidence)
        else:
            # For new records, set the next review date
            progress.update_progress(confidence)
        
        return JsonResponse({
            'success': True,
            'progress': {
                'times_studied': progress.times_studied,
                'mastered': progress.mastered,
                'confidence_level': progress.confidence_level,
                'next_review_date': progress.next_review_date.isoformat() if progress.next_review_date else None
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@active_subscription_required(feature="can_view_quizlet")
def get_progress_summary(request, pk):
    """Get progress summary - requires view permission"""
    flashcard_set = get_object_or_404(FlashcardSet, pk=pk)
    
    # Check if user can view this set
    if not can_view_set(request.user, flashcard_set):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get all cards in the set
    cards = flashcard_set.cards.all()
    
    # Get user's progress
    user_progress = UserProgress.objects.filter(
        user=request.user,
        flashcard__in=cards
    )
    
    # Calculate statistics
    total_cards = cards.count()
    mastered_cards = user_progress.filter(mastered=True).count()
    studied_cards = user_progress.count()
    
    # Cards due for review
    cards_due = user_progress.filter(
        Q(next_review_date__lte=timezone.now()) | Q(next_review_date__isnull=True)
    ).count()
    
    return JsonResponse({
        'total_cards': total_cards,
        'mastered_cards': mastered_cards,
        'studied_cards': studied_cards,
        'cards_due': cards_due,
        'mastery_percentage': round((mastered_cards / total_cards * 100) if total_cards > 0 else 0, 1)
    })


# ========== CHAPTER-BASED FLASHCARD SET CREATION ==========

@login_required
@active_subscription_required(feature="can_view_quizlet")
def create_set_chapter_private(request, chapter_id):
    """Create private flashcard set for chapter - logged in users only"""
    chapter = get_object_or_404(Chapter, id=chapter_id)
    user = request.user
    
    # Check if user already has a private set for this chapter
    set_chapter = FlashcardSet.objects.filter(
        created_by=user, 
        title=chapter, 
        is_public=False
    ).first()

    if not set_chapter:
        # Create private set
        FlashcardSet.objects.create(
            title=chapter,
            created_by=user,
            is_public=False,
        )
        messages.success(request, "Votre ensemble personnel a été créé avec succès!")
    else:
        messages.error(request, "Vous avez déjà un ensemble pour ce chapitre!")
    
    return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)


@login_required
@active_subscription_required(feature="can_view_quizlet")
def create_set_chapter_public(request, chapter_id):
    """Create public flashcard set for chapter - staff/superuser only"""
    chapter = get_object_or_404(Chapter, id=chapter_id)
    user = request.user
    
    # Check permission - only staff/superuser can create public sets
    if not is_staff_or_superuser(user):
        messages.error(request, "Only staff members can create public flashcard sets.")
        return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    
    # Check if public set already exists for this chapter
    set_chapter = FlashcardSet.objects.filter(
        title=chapter, 
        is_public=True
    ).first()

    if not set_chapter:
        # Create public set
        FlashcardSet.objects.create(
            title=chapter,
            created_by=user,
            is_public=True,
        )
        messages.success(request, "Public flashcard set created successfully!")
    else:
        messages.error(request, "A public flashcard set for this chapter already exists!")
    
    return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)


# ========== ADMIN DASHBOARD VIEW ========== (not functioning yet)

@login_required
def admin_dashboard(request):
    """Admin dashboard - staff/superuser only"""
    if not is_staff_or_superuser(request.user):
        messages.error(request, "Cette page est réserver au admin ou membre du staff.")
        return redirect('quizlet_copy:home')
    
    # Get all public sets
    public_sets = FlashcardSet.objects.filter(is_public=True)
    
    # Get all private sets (staff can see all)
    private_sets = FlashcardSet.objects.filter(is_public=False)
    
    # Get user statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(last_login__gte=timezone.now() - timezone.timedelta(days=30)).count()
    
    context = {
        'public_sets': public_sets,
        'private_sets': private_sets,
        'total_users': total_users,
        'active_users': active_users,
        'total_sets': FlashcardSet.objects.count(),
        'total_flashcards': Flashcard.objects.count(),
    }
    
    return render(request, 'quizlet_copy/admin_dashboard.html', context)


# ========== HELPER VIEW FOR TEMPLATE CONTEXT ==========

@login_required
@active_subscription_required(feature="can_view_quizlet")
def create_set_chapter_pivate (request, chapter_id):
    chapter = get_object_or_404(Chapter, id = chapter_id)
    user = request.user
    set_chapter = FlashcardSet.objects.filter(created_by = user, title = chapter, is_public=False)

    if not set_chapter:
        if user.is_authenticated:
            FlashcardSet.objects.create(
                title = chapter,
                created_by = user,
                is_public = False,
            )
            messages.success (request, "La carte mentale a été créée avec succès!")
            return redirect ('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    else:
        messages.error (request, "Désolé, vous avez déjà créé votre propre carte metale pour ce chapitre!")
        return redirect ('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)

    return redirect ('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)


@login_required
@non_student_required
def create_set_chapter_public (request, chapter_id):
    chapter = get_object_or_404(Chapter, id = chapter_id)
    user = request.user
    set_chapter = FlashcardSet.objects.filter(title = chapter, is_public=True)

    if not set_chapter:
        if user.is_authenticated and (user.is_staff or user.is_teacher):
            FlashcardSet.objects.create(
                title = chapter,
                created_by = user,
                is_public = True,
            )
            messages.success (request, "La carte mentale a été créée avec succès!")
            return redirect ('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    else:
        messages.error (request, "Désolé, la carte metale publique pour ce chapitre existe déjà !")
        return redirect ('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    
    return redirect ('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)


