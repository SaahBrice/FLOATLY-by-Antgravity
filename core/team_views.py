"""
Team Management Views for Floatly.

Handles:
- Team management page (list members)
- Invite member
- Accept/decline invitation
- Remove member
- Change member role
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse, HttpResponse
from django.contrib import messages
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone

from .models import Kiosk, KioskMember, KioskInvitation, User
from .notification_service import notify_kiosk_invitation

logger = logging.getLogger('core.team')


# =============================================================================
# PERMISSION HELPERS
# =============================================================================

def get_user_role(user, kiosk):
    """Get user's role in a kiosk."""
    if kiosk.owner == user:
        return 'OWNER'
    try:
        member = KioskMember.objects.get(kiosk=kiosk, user=user)
        return member.role
    except KioskMember.DoesNotExist:
        return None


def can_manage_team(user, kiosk):
    """Check if user can manage team (owner or admin)."""
    role = get_user_role(user, kiosk)
    return role in ['OWNER', 'ADMIN']


def can_remove_member(user, kiosk, member):
    """Check if user can remove a member."""
    role = get_user_role(user, kiosk)
    
    # Only owner and admin can remove
    if role not in ['OWNER', 'ADMIN']:
        return False
    
    # Cannot remove owner
    if member.user == kiosk.owner:
        return False
    
    # Admin cannot remove other admins
    if role == 'ADMIN' and member.role == 'ADMIN':
        return False
    
    return True


# =============================================================================
# TEAM MANAGEMENT VIEW
# =============================================================================

class TeamManagementView(LoginRequiredMixin, View):
    """
    Main team management page.
    Shows list of members and pending invitations.
    """
    
    def get(self, request, slug):
        kiosk = get_object_or_404(Kiosk, slug=slug)
        
        # Check permission
        if not can_manage_team(request.user, kiosk):
            raise Http404("You don't have permission to manage this team")
        
        # Get members
        members = KioskMember.objects.filter(kiosk=kiosk).select_related('user')
        
        # Get pending invitations
        pending_invites = KioskInvitation.objects.filter(
            kiosk=kiosk,
            status=KioskInvitation.Status.PENDING,
            expires_at__gt=timezone.now()
        )
        
        user_role = get_user_role(request.user, kiosk)
        
        return render(request, 'team/manage.html', {
            'page_title': f'Team - {kiosk.name}',
            'kiosk': kiosk,
            'owner': kiosk.owner,
            'members': members,
            'pending_invites': pending_invites,
            'user_role': user_role,
            'can_invite': user_role in ['OWNER', 'ADMIN'],
        })


# =============================================================================
# INVITE MEMBER VIEW
# =============================================================================

class InviteMemberView(LoginRequiredMixin, View):
    """
    Invite a new member to the kiosk.
    If user exists, send notification. Otherwise, send email.
    """
    
    def get(self, request, slug):
        kiosk = get_object_or_404(Kiosk, slug=slug)
        
        if not can_manage_team(request.user, kiosk):
            raise Http404("Permission denied")
        
        return render(request, 'team/invite_form.html', {
            'page_title': 'Invite Member',
            'kiosk': kiosk,
            'roles': KioskMember.Role.choices,
        })
    
    def post(self, request, slug):
        kiosk = get_object_or_404(Kiosk, slug=slug)
        
        if not can_manage_team(request.user, kiosk):
            raise Http404("Permission denied")
        
        email = request.POST.get('email', '').strip().lower()
        role = request.POST.get('role', 'AGENT')
        message_text = request.POST.get('message', '')
        
        if not email:
            messages.error(request, 'Please enter an email address')
            return redirect('core:team_invite', slug=slug)
        
        # Check if already a member
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            if KioskMember.objects.filter(kiosk=kiosk, user=user).exists():
                messages.warning(request, f'{email} is already a member')
                return redirect('core:team_manage', slug=slug)
            if user == kiosk.owner:
                messages.warning(request, 'Cannot invite the owner')
                return redirect('core:team_manage', slug=slug)
        
        # Check for existing pending invitation
        existing = KioskInvitation.objects.filter(
            kiosk=kiosk,
            email=email,
            status=KioskInvitation.Status.PENDING,
            expires_at__gt=timezone.now()
        ).first()
        
        if existing:
            messages.info(request, f'Invitation already pending for {email}')
            return redirect('core:team_manage', slug=slug)
        
        # Create invitation
        invitation = KioskInvitation.objects.create(
            kiosk=kiosk,
            email=email,
            role=role,
            invited_by=request.user,
            message=message_text
        )
        
        # Check if user exists
        try:
            invitee = User.objects.get(email=email)
            # Send in-app notification
            self._send_notification(invitation, invitee)
            messages.success(request, f'Invitation sent to {email}')
        except User.DoesNotExist:
            # Send email invitation
            self._send_email(invitation)
            messages.success(request, f'Invitation email sent to {email}')
        
        logger.info(
            f"Invitation created: kiosk={kiosk.name}, email={email}, "
            f"role={role}, invited_by={request.user.email}"
        )
        
        return redirect('core:team_manage', slug=slug)
    
    def _send_notification(self, invitation, user):
        """Send in-app notification to existing user."""
        try:
            notify_kiosk_invitation(
                user=user,
                kiosk=invitation.kiosk,
                invited_by=invitation.invited_by,
                invitation=invitation
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def _send_email(self, invitation):
        """Send email to non-registered user."""
        try:
            invite_url = f"{settings.SITE_URL}/invite/{invitation.token}/"
            
            context = {
                'invitation': invitation,
                'kiosk': invitation.kiosk,
                'invited_by': invitation.invited_by,
                'invite_url': invite_url,
            }
            
            html_message = render_to_string('emails/invitation.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f"You're invited to join {invitation.kiosk.name} on Floatly",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
                html_message=html_message,
            )
            
            logger.info(f"Invitation email sent to {invitation.email}")
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")


# =============================================================================
# ACCEPT INVITATION VIEW
# =============================================================================

class AcceptInvitationView(LoginRequiredMixin, View):
    """
    Accept or decline an invitation.
    Accessible via token in URL.
    """
    
    def get(self, request, token):
        invitation = get_object_or_404(KioskInvitation, token=token)
        
        if invitation.status != KioskInvitation.Status.PENDING:
            return render(request, 'team/invitation_invalid.html', {
                'page_title': 'Invalid Invitation',
                'invitation': invitation,
            })
        
        if invitation.is_expired:
            return render(request, 'team/invitation_expired.html', {
                'page_title': 'Invitation Expired',
                'invitation': invitation,
            })
        
        return render(request, 'team/invitation_accept.html', {
            'page_title': f'Join {invitation.kiosk.name}',
            'invitation': invitation,
            'kiosk': invitation.kiosk,
        })
    
    def post(self, request, token):
        invitation = get_object_or_404(KioskInvitation, token=token)
        action = request.POST.get('action', 'decline')
        
        if action == 'accept':
            try:
                member = invitation.accept(request.user)
                messages.success(
                    request,
                    f"🎉 You've joined {invitation.kiosk.name}!"
                )
                logger.info(
                    f"Invitation accepted: user={request.user.email}, "
                    f"kiosk={invitation.kiosk.name}"
                )
                return redirect('core:dashboard')
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('core:dashboard')
        else:
            invitation.decline()
            messages.info(request, 'Invitation declined')
            return redirect('core:dashboard')


# =============================================================================
# REMOVE MEMBER VIEW
# =============================================================================

class RemoveMemberView(LoginRequiredMixin, View):
    """Remove a member from the kiosk."""
    
    def post(self, request, slug, member_id):
        kiosk = get_object_or_404(Kiosk, slug=slug)
        member = get_object_or_404(KioskMember, id=member_id, kiosk=kiosk)
        
        if not can_remove_member(request.user, kiosk, member):
            messages.error(request, "You cannot remove this member")
            return redirect('core:team_manage', slug=slug)
        
        member_name = member.user.display_name
        member.delete()
        
        messages.success(request, f'{member_name} has been removed from the team')
        logger.info(
            f"Member removed: user={member.user.email}, kiosk={kiosk.name}, "
            f"removed_by={request.user.email}"
        )
        
        return redirect('core:team_manage', slug=slug)


# =============================================================================
# CHANGE ROLE VIEW
# =============================================================================

class ChangeMemberRoleView(LoginRequiredMixin, View):
    """Change a member's role."""
    
    def post(self, request, slug, member_id):
        kiosk = get_object_or_404(Kiosk, slug=slug)
        member = get_object_or_404(KioskMember, id=member_id, kiosk=kiosk)
        
        # Only owner can change roles
        if kiosk.owner != request.user:
            messages.error(request, "Only the owner can change roles")
            return redirect('core:team_manage', slug=slug)
        
        new_role = request.POST.get('role', 'AGENT')
        if new_role not in ['ADMIN', 'AGENT']:
            messages.error(request, "Invalid role")
            return redirect('core:team_manage', slug=slug)
        
        old_role = member.role
        member.role = new_role
        member.save()
        
        messages.success(
            request,
            f"{member.user.display_name}'s role changed from {old_role} to {new_role}"
        )
        
        logger.info(
            f"Role changed: user={member.user.email}, kiosk={kiosk.name}, "
            f"old_role={old_role}, new_role={new_role}"
        )
        
        return redirect('core:team_manage', slug=slug)


# =============================================================================
# CANCEL INVITATION VIEW
# =============================================================================

class CancelInvitationView(LoginRequiredMixin, View):
    """Cancel a pending invitation."""
    
    def post(self, request, slug, invite_id):
        kiosk = get_object_or_404(Kiosk, slug=slug)
        
        if not can_manage_team(request.user, kiosk):
            raise Http404("Permission denied")
        
        invitation = get_object_or_404(
            KioskInvitation,
            id=invite_id,
            kiosk=kiosk,
            status=KioskInvitation.Status.PENDING
        )
        
        invitation.status = KioskInvitation.Status.EXPIRED
        invitation.save()
        
        messages.success(request, f'Invitation to {invitation.email} cancelled')
        
        return redirect('core:team_manage', slug=slug)
