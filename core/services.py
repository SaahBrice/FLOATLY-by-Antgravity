"""
Business logic services for Floatly.

Contains helper functions for:
- Commission calculation
- Kiosk balance management
- Unique name generation
- Notification creation
"""

from decimal import Decimal
from django.utils.text import slugify
from django.db.models import Q


def calculate_commission(network, amount):
    """
    Calculate commission for a transaction based on network and amount.
    
    Args:
        network: Network model instance
        amount: Transaction amount as Decimal or number
        
    Returns:
        Decimal: Calculated commission, or 0 if no matching rate found
    """
    from .models import CommissionRate
    
    amount = Decimal(str(amount))
    rate = CommissionRate.get_rate_for_amount(network, amount)
    
    if rate:
        return rate.calculate_commission(amount)
    return Decimal('0')


def get_kiosk_balances(kiosk):
    """
    Calculate current cash and float balances for a kiosk.
    
    The "Float Balancing Equation":
    - Deposit (Cash In): Physical Cash ↑ | Digital Float ↓
    - Withdrawal (Cash Out): Physical Cash ↓ | Digital Float ↑
    
    Args:
        kiosk: Kiosk model instance
        
    Returns:
        dict: {
            'cash_balance': Decimal,
            'float_balance': Decimal,
            'total_profit': Decimal
        }
    """
    return kiosk.transactions.all().calculate_balances()


def get_kiosk_daily_summary(kiosk, date=None):
    """
    Get transaction summary for a specific date.
    
    Args:
        kiosk: Kiosk model instance
        date: Date to summarize (defaults to today)
        
    Returns:
        dict: {
            'date': date,
            'deposits': { count, total_amount, total_profit },
            'withdrawals': { count, total_amount, total_profit },
            'net_cash_change': Decimal,
            'net_float_change': Decimal,
            'total_profit': Decimal
        }
    """
    from django.utils import timezone
    
    if date is None:
        date = timezone.now().date()
    
    day_transactions = kiosk.transactions.filter(timestamp__date=date)
    
    deposits = day_transactions.deposits().calculate_totals()
    withdrawals = day_transactions.withdrawals().calculate_totals()
    
    return {
        'date': date,
        'deposits': deposits,
        'withdrawals': withdrawals,
        'net_cash_change': deposits['total_amount'] - withdrawals['total_amount'],
        'net_float_change': withdrawals['total_amount'] - deposits['total_amount'],
        'total_profit': deposits['total_profit'] + withdrawals['total_profit'],
        'total_transactions': deposits['count'] + withdrawals['count']
    }


def generate_unique_kiosk_name(base_name, owner):
    """
    Generate a unique kiosk name for an owner.
    
    If the exact name already exists for this owner, 
    appends a number suffix.
    
    Args:
        base_name: Desired kiosk name
        owner: User model instance
        
    Returns:
        str: Unique kiosk name
    """
    from .models import Kiosk
    
    name = base_name.strip()
    if not name:
        name = f"{owner.display_name}'s Kiosk"
    
    # Check if name exists for this owner
    counter = 1
    unique_name = name
    
    while Kiosk.objects.filter(owner=owner, name__iexact=unique_name).exists():
        unique_name = f"{name} ({counter})"
        counter += 1
    
    return unique_name


def create_kiosk_with_owner_as_admin(name, owner, location=''):
    """
    Create a new kiosk and automatically add the owner as an admin member.
    
    Args:
        name: Kiosk name
        owner: User who will own and administer the kiosk
        location: Optional location description
        
    Returns:
        Kiosk: Created kiosk instance
    """
    from .models import Kiosk, KioskMember
    
    # Ensure unique name for this owner
    unique_name = generate_unique_kiosk_name(name, owner)
    
    # Create kiosk
    kiosk = Kiosk.objects.create(
        name=unique_name,
        owner=owner,
        location=location
    )
    
    # Add owner as admin member
    KioskMember.objects.create(
        kiosk=kiosk,
        user=owner,
        role=KioskMember.Role.ADMIN
    )
    
    return kiosk


def invite_user_to_kiosk(kiosk, email, role='AGENT', invited_by=None):
    """
    Invite a user to join a kiosk team.
    
    If user exists: Creates in-app notification
    If user doesn't exist: Should trigger email invitation (future)
    
    Args:
        kiosk: Kiosk to invite to
        email: Email address of invitee
        role: Role to assign (ADMIN or AGENT)
        invited_by: User who sent the invitation
        
    Returns:
        dict: {
            'status': 'existing_user' | 'new_user',
            'user': User instance if exists,
            'notification': Notification if created
        }
    """
    from .models import User, KioskMember, Notification
    
    try:
        user = User.objects.get(email__iexact=email)
        
        # Check if already a member
        if KioskMember.objects.filter(kiosk=kiosk, user=user).exists():
            return {
                'status': 'already_member',
                'user': user,
                'notification': None
            }
        
        # Create notification for existing user
        notification = Notification.create_invite(
            user=user,
            kiosk=kiosk,
            invited_by=invited_by or kiosk.owner
        )
        
        return {
            'status': 'existing_user',
            'user': user,
            'notification': notification
        }
        
    except User.DoesNotExist:
        # User doesn't exist - would send email invitation
        # For now, just return status
        return {
            'status': 'new_user',
            'email': email,
            'notification': None
        }


def accept_kiosk_invitation(user, kiosk, role='AGENT'):
    """
    Accept a kiosk invitation and add user as member.
    
    Args:
        user: User accepting the invitation
        kiosk: Kiosk being joined
        role: Role to assign
        
    Returns:
        KioskMember: Created membership
    """
    from .models import KioskMember, Notification
    
    # Create membership
    member, created = KioskMember.objects.get_or_create(
        kiosk=kiosk,
        user=user,
        defaults={'role': role}
    )
    
    # Mark related invitation notifications as read
    Notification.objects.filter(
        user=user,
        related_kiosk=kiosk,
        notification_type=Notification.NotificationType.INVITE,
        is_read=False
    ).update(is_read=True)
    
    return member


def get_user_kiosks(user):
    """
    Get all kiosks a user has access to (owned + member of).
    
    Args:
        user: User model instance
        
    Returns:
        dict: {
            'owned': QuerySet of owned kiosks,
            'member_of': QuerySet of kiosks user is a member of (not owner)
        }
    """
    from .models import Kiosk
    
    owned = Kiosk.objects.filter(owner=user).active()
    member_of = Kiosk.objects.filter(
        members__user=user
    ).exclude(owner=user).active().distinct()
    
    return {
        'owned': owned,
        'member_of': member_of,
        'total_count': owned.count() + member_of.count()
    }


def get_unread_notification_count(user):
    """Get count of unread notifications for a user."""
    from .models import Notification
    return Notification.objects.filter(user=user, is_read=False).count()


def seed_default_networks():
    """
    Create default mobile money networks if they don't exist.
    
    Returns:
        list: Created or existing Network instances
    """
    from .models import Network
    
    default_networks = [
        {'name': 'MTN Mobile Money', 'code': 'MTN', 'color': '#ffcc00'},
        {'name': 'Orange Money', 'code': 'OM', 'color': '#ff6600'},
        {'name': 'Express Union', 'code': 'EU', 'color': '#1e40af'},
        {'name': 'YooMee', 'code': 'YOOMEE', 'color': '#8b5cf6'},
    ]
    
    networks = []
    for data in default_networks:
        network, created = Network.objects.get_or_create(
            code=data['code'],
            defaults={'name': data['name'], 'color': data['color']}
        )
        networks.append(network)
    
    return networks


def seed_default_commission_rates():
    """
    Create default commission rates for MTN and Orange.
    Based on typical Cameroonian mobile money commission structure.
    
    Returns:
        list: Created CommissionRate instances
    """
    from .models import Network, CommissionRate
    
    # Ensure networks exist
    seed_default_networks()
    
    rates_config = [
        # MTN Mobile Money rates
        {'network_code': 'MTN', 'min': 100, 'max': 5000, 'type': 'FIXED', 'value': 50},
        {'network_code': 'MTN', 'min': 5001, 'max': 10000, 'type': 'FIXED', 'value': 100},
        {'network_code': 'MTN', 'min': 10001, 'max': 50000, 'type': 'FIXED', 'value': 150},
        {'network_code': 'MTN', 'min': 50001, 'max': 500000, 'type': 'PERCENTAGE', 'value': 0.3},
        
        # Orange Money rates
        {'network_code': 'OM', 'min': 100, 'max': 5000, 'type': 'FIXED', 'value': 50},
        {'network_code': 'OM', 'min': 5001, 'max': 10000, 'type': 'FIXED', 'value': 100},
        {'network_code': 'OM', 'min': 10001, 'max': 50000, 'type': 'FIXED', 'value': 150},
        {'network_code': 'OM', 'min': 50001, 'max': 500000, 'type': 'PERCENTAGE', 'value': 0.3},
    ]
    
    created_rates = []
    for config in rates_config:
        try:
            network = Network.objects.get(code=config['network_code'])
            rate, created = CommissionRate.objects.get_or_create(
                network=network,
                min_amount=Decimal(str(config['min'])),
                max_amount=Decimal(str(config['max'])),
                defaults={
                    'rate_type': config['type'],
                    'rate_value': Decimal(str(config['value']))
                }
            )
            if created:
                created_rates.append(rate)
        except Network.DoesNotExist:
            continue
    
    return created_rates
