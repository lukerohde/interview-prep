from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from uuid import uuid4
from enum import Enum
from .utils import do_something_handy
from .ai_helpers import generate_interview_questions

class Application(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='Name of the position or company')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    resume = models.TextField(help_text='Your resume or CV content')
    job_description = models.TextField(help_text='Full job description')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.status}"

    class Meta:
        ordering = ['-updated_at']

    def get_existing_questions(self):
        """Get existing auto-generated questions to avoid duplicates"""
        return [
            {'question': card.front, 'suggested_answer': card.back}
            for card in self.flashcards.filter(tags__contains=['auto-generated'])
        ]

    def generate_and_save_questions(self):
        """Generate and save new AI interview questions"""
        existing_questions = self.get_existing_questions()
        questions = generate_interview_questions(
            job_description=self.job_description,
            resume=self.resume,
            existing_questions=existing_questions
        )

        created_cards = []
        for q in questions:
            flashcard = FlashCard.objects.create(
                user=self.owner,
                front=q['question'],
                back=q['suggested_answer'],
                tags=[q['category'], 'auto-generated']
            )
            flashcard.applications.add(self)
            created_cards.append(flashcard)

        return created_cards



class ReviewStatus(str, Enum):
    FORGOT = 'forgot'
    HARD = 'hard'
    EASY = 'easy'

class FlashCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    front = models.TextField()
    back = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.JSONField(default=list)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards')
    applications = models.ManyToManyField(Application, related_name='flashcards', blank=True)

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

    def update_review(self, status: ReviewStatus, side='front'):
        """Update review status and schedule next review using SM-2 algorithm"""
        now = timezone.now()
        
        # Get current values
        ef = getattr(self, f'{side}_easiness_factor')
        reps = getattr(self, f'{side}_repetitions')
        interval = getattr(self, f'{side}_interval')
        review_count = getattr(self, f'{side}_review_count')

        # Update review count
        setattr(self, f'{side}_review_count', review_count + 1)
        setattr(self, f'{side}_last_review', now)

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
