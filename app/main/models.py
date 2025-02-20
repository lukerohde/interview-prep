from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from uuid import uuid4
from enum import Enum
import yaml
from .utils import do_something_handy
from .ai_helpers import generate_interview_questions

class TutorConfig:
    @staticmethod
    def load_config(config_path, user=None):
        """Load tutor config from YAML and apply user overrides"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if user:
            # Get user's overrides for this tutor
            overrides = {
                override.key: override.value 
                for override in user.prompt_overrides.filter(
                    tutor_url_path=config.get('url_path')
                )
            }
            
            # Apply overrides using dotted path notation
            for key, value in overrides.items():
                target = config
                *path_parts, final_key = key.split('.')
                
                # Navigate to the correct nested dictionary
                for part in path_parts:
                    if part not in target:
                        target[part] = {}
                    target = target[part]
                target[final_key] = value
                
        return config

class Tutor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='Name of the tutor')
    deck_name = models.CharField(max_length=255, help_text='Display name for decks of this type')
    url_path = models.CharField(max_length=255, unique=True, help_text='URL path for this tutor (e.g. interview-coach)')
    config_path = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text='Path to the YAML config file')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_config(self, user=None):
        """Get tutor config with optional user overrides"""
        if not self.config_path:
            raise ValueError("No config path set for this tutor")
        return TutorConfig.load_config(self.config_path, user)

    class Meta:
        ordering = ['name']

class TutorPromptOverride(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prompt_overrides')
    tutor_url_path = models.CharField(max_length=255, help_text='URL path of the tutor')
    key = models.CharField(max_length=255, help_text='Dotted path to the prompt key')
    value = models.TextField(help_text='Override value for the prompt')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'tutor_url_path', 'key']
        ordering = ['tutor_url_path', 'key']

    def __str__(self):
        return f"{self.user.username} - {self.tutor_url_path} - {self.key}"

class Document(models.Model):
    class DocumentType(models.TextChoices):
        RESUME = 'resume', 'Resume'
        JOB_DESCRIPTION = 'job_description', 'Job Description'
        STUDY_MATERIAL = 'study_material', 'Study Material'
        LANGUAGE_TEXT = 'language_text', 'Language Text'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='Name of the document')
    url = models.URLField(blank=True, null=True, help_text='URL to the document in S3')
    content = models.TextField(help_text='Extracted or provided text content')
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.STUDY_MATERIAL,
        help_text='Type of document'
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-updated_at']

class Deck(models.Model):
    class DeckType(models.TextChoices):
        JOB_APPLICATION = 'job_application', 'Job Application'
        STUDY = 'study', 'Study Materials'
        LANGUAGE = 'language', 'Language Learning'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='Name of the deck')
    deck_type = models.CharField(
        max_length=50,
        choices=DeckType.choices,
        default=DeckType.STUDY,
        help_text='Type of deck'
    )
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='decks')
    documents = models.ManyToManyField(Document, related_name='decks', blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=50,
        default='active',
        help_text='Status of the deck (e.g., active, archived)'
    )

    def __str__(self):
        return f"{self.name} ({self.tutor.deck_name})"

    @property
    def title(self):
        return str(self)

    class Meta:
        ordering = ['-updated_at']

    def get_existing_questions(self):
        """Get existing auto-generated questions to avoid duplicates"""
        return [
            {'question': card.front, 'suggested_answer': card.back}
            for card in self.flashcards.filter(tags__contains=['auto-generated'])
        ]

    def generate_questions(self):
        """Generate new AI interview questions without saving them"""
        existing_questions = self.get_existing_questions()
        
        # Combine all document content
        combined_content = "\n\n".join([doc.content for doc in self.documents.all()])
        
        return generate_interview_questions(
            content=combined_content,
            existing_questions=existing_questions
        )

    def save_questions(self, questions):
        """Save the generated questions as flashcards"""
        created_cards = []
        for q in questions:
            flashcard = FlashCard.objects.create(
                user=self.owner,
                front=q['question'],
                back=q['suggested_answer'],
                tags=[q['category'], 'auto-generated']
            )
            flashcard.decks.add(self)
            created_cards.append(flashcard)
        return created_cards

    def generate_and_save_questions(self):
        """Generate and save new AI interview questions from documents"""
        questions = self.generate_questions()
        return self.save_questions(questions)



class ReviewStatus(str, Enum):
    FORGOT = 'forgot'
    HARD = 'hard'
    EASY = 'easy'

class FlashCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    front = models.TextField()
    back = models.TextField()
    front_notes = models.TextField(blank=True, null=True, help_text='Notes for the front side of the card')
    back_notes = models.TextField(blank=True, null=True, help_text='Notes for the back side of the card')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.JSONField(default=list)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards')
    decks = models.ManyToManyField(Deck, related_name='flashcards', blank=True)

    # Front review fields
    front_last_review = models.DateTimeField(null=True, blank=True)
    front_interval = models.IntegerField(default=1)  # in minutes
    front_review_count = models.IntegerField(default=0)
    front_easiness_factor = models.FloatField(default=2.5)
    front_repetitions = models.IntegerField(default=0)

    # Back review fields
    back_last_review = models.DateTimeField(null=True, blank=True)
    back_interval = models.IntegerField(default=1)  # in minutes
    back_review_count = models.IntegerField(default=0)
    back_easiness_factor = models.FloatField(default=2.5)
    back_repetitions = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"FlashCard {self.id}: {self.front[:30]}..."

    def is_due_for_review(self, side=None):
        """Check if the card is due for review. If side is specified, checks only that side.
        Otherwise checks both sides and returns True if either side is due."""
        if side:
            last_review = getattr(self, f'{side}_last_review')
            interval = getattr(self, f'{side}_interval')
            if not last_review:
                return True
            return last_review + timezone.timedelta(minutes=interval) <= timezone.now()
        else:
            # Check both sides
            return self.is_due_for_review('front') or self.is_due_for_review('back')

    def update_review(self, status: ReviewStatus, side='front', notes=None):
        """Update review status and schedule next review using SM-2 algorithm
        
        Args:
            status (ReviewStatus): The review status (FORGOT, HARD, or EASY)
            side (str, optional): Which side of the card to update ('front' or 'back'). Defaults to 'front'.
            notes (str, optional): Notes to store for this side of the card. Defaults to None.
        """
        now = timezone.now()
        
        # Get current values
        ef = getattr(self, f'{side}_easiness_factor')
        reps = getattr(self, f'{side}_repetitions')
        interval = getattr(self, f'{side}_interval')
        review_count = getattr(self, f'{side}_review_count')

        # Update review count
        setattr(self, f'{side}_review_count', review_count + 1)
        setattr(self, f'{side}_last_review', now)

        # Update notes if provided
        if notes is not None:
            setattr(self, f'{side}_notes', notes)

        # Apply SM-2 algorithm
        if status == ReviewStatus.FORGOT:
            reps = 0
            interval = 1
            ef = max(1.3, ef - 0.3)
        else:
            reps += 1
            if status == ReviewStatus.HARD:
                ef = max(1.3, ef - 0.15)
            elif status == ReviewStatus.EASY:
                ef = min(2.5, ef + 0.15)

            if reps == 1:
                interval = 1
            elif reps == 2:
                interval = 6
            else:
                interval = round(interval * ef)

        # Update values
        setattr(self, f'{side}_easiness_factor', ef)
        setattr(self, f'{side}_repetitions', reps)
        setattr(self, f'{side}_interval', interval)
        
        self.save()
