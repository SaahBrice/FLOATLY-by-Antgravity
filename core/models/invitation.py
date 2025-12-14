"""
KioskInvitation model for Floatly.

Handles team invitations for kiosks.
"""

import uuid
from django.db import models
from django.utils import timezone

from .kiosk import KioskMember


# =============================================================================
# KIOSK INVITATION MODEL
# =============================================================================

class KioskInvitation(models.Model):
    """
    Invitation to join a kiosk team.
    Supports inviting both existing and new users by email.
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        DECLINED = 'DECLINED', 'Declined'
        EXPIRED = 'EXPIRED', 'Expired'
    
    kiosk = models.ForeignKey(
        'Kiosk',
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text='The kiosk the user is being invited to'
    )
    email = models.EmailField(
        'invitee email',
        help_text='Email address of the person being invited'
    )
    role = models.CharField(
        'role',
        max_length=10,
        choices=KioskMember.Role.choices,
        default=KioskMember.Role.AGENT,
        help_text='Role the invitee will have upon acceptance'
    )
    invited_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        help_text='The user who sent the invitation'
    )
    token = models.UUIDField(
        'invitation token',
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text='Unique token for invitation link'
    )
    status = models.CharField(
        'status',
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    message = models.TextField(
        'personal message',
        blank=True,
        help_text='Optional message from inviter'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    expires_at = models.DateTimeField(
        'expires at',
        help_text='Invitation expiration date'
    )
    accepted_at = models.DateTimeField(
        'accepted at',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'kiosk invitation'
        verbose_name_plural = 'kiosk invitations'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invite {self.email} to {self.kiosk.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Set expiration to 7 days from now if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_pending(self):
        return self.status == self.Status.PENDING and not self.is_expired
    
    def accept(self, user):
        """Accept the invitation and add user to kiosk."""
        if not self.is_pending:
            raise ValueError("Invitation is no longer valid")
        
        # Create membership
        member, created = KioskMember.objects.get_or_create(
            kiosk=self.kiosk,
            user=user,
            defaults={'role': self.role}
        )
        
        # Update invitation status
        self.status = self.Status.ACCEPTED
        self.accepted_at = timezone.now()
        self.save()
        
        return member
    
    def decline(self):
        """Decline the invitation."""
        if self.status == self.Status.PENDING:
            self.status = self.Status.DECLINED
            self.save()
