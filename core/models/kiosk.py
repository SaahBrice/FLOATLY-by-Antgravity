"""
Kiosk and KioskMember models for Floatly.

Represents physical kiosk locations and team membership.
"""

from django.db import models
from django.utils.text import slugify

from ..managers import KioskManager


# =============================================================================
# KIOSK MODEL
# =============================================================================

class Kiosk(models.Model):
    """
    A kiosk represents a physical location where an agent operates.
    One user can own multiple kiosks.
    """
    
    name = models.CharField(
        'kiosk name',
        max_length=100,
        help_text='Unique name like "Akwa Shop" or "Molyko Kiosk"'
    )
    slug = models.SlugField(
        'URL slug',
        max_length=120,
        unique=True,
        help_text='Auto-generated unique identifier'
    )
    owner = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='owned_kiosks',
        help_text='The user who created and owns this kiosk'
    )
    location = models.CharField(
        'location description',
        max_length=255,
        blank=True,
        help_text='Physical location or address description'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Is this kiosk currently operational?'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'updated at',
        auto_now=True
    )
    
    objects = KioskManager()
    
    class Meta:
        verbose_name = 'kiosk'
        verbose_name_plural = 'kiosks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.owner.display_name})"
    
    def save(self, *args, **kwargs):
        """Auto-generate unique slug if not provided."""
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)
    
    def _generate_unique_slug(self):
        """Generate a unique slug for the kiosk."""
        base_slug = slugify(self.name)
        if not base_slug:
            base_slug = 'kiosk'
        
        slug = base_slug
        counter = 1
        
        # Check if slug exists (excluding self for updates)
        while Kiosk.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def get_balances(self):
        """Calculate current cash and float balances for this kiosk."""
        return self.transactions.calculate_balances()
    
    def get_today_stats(self):
        """Get today's transaction statistics."""
        return self.transactions.today().calculate_totals()
    
    @property
    def member_count(self):
        """Number of team members (excluding owner)."""
        return self.members.count()


# =============================================================================
# KIOSK MEMBER MODEL
# =============================================================================

class KioskMember(models.Model):
    """
    Represents a user's membership in a kiosk team.
    One user can be a member of multiple kiosks (and owner of others).
    """
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        AGENT = 'AGENT', 'Agent'
    
    kiosk = models.ForeignKey(
        Kiosk,
        on_delete=models.CASCADE,
        related_name='members',
        help_text='The kiosk this membership belongs to'
    )
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='kiosk_memberships',
        help_text='The user who is a member'
    )
    role = models.CharField(
        'role',
        max_length=10,
        choices=Role.choices,
        default=Role.AGENT,
        help_text='Admin has full access, Agent has limited access'
    )
    joined_at = models.DateTimeField(
        'joined at',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'kiosk member'
        verbose_name_plural = 'kiosk members'
        ordering = ['-joined_at']
        # Ensure a user can only be added once per kiosk
        unique_together = ['kiosk', 'user']
        constraints = [
            models.UniqueConstraint(
                fields=['kiosk', 'user'],
                name='unique_kiosk_member'
            )
        ]
    
    def __str__(self):
        return f"{self.user.display_name} @ {self.kiosk.name} ({self.role})"
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
