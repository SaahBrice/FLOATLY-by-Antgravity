"""
Management command to seed the database with default data.

Creates:
- Default networks (MTN, Orange, EU, YooMee)
- Default commission rates for MTN and Orange
- Optional: Sample kiosk and transactions for testing

Usage:
    python manage.py seed_data
    python manage.py seed_data --with-samples
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal

from core.models import Kiosk, KioskMember, Network, CommissionRate, Transaction
from core.services import (
    seed_default_networks,
    seed_default_commission_rates,
    create_kiosk_with_owner_as_admin
)


User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with default networks and commission rates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-samples',
            action='store_true',
            help='Also create sample user, kiosk, and transactions'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Seeding database...'))
        
        # Seed networks
        networks = seed_default_networks()
        self.stdout.write(self.style.SUCCESS(
            f'✓ Created/verified {len(networks)} networks'
        ))
        
        for network in networks:
            self.stdout.write(f'  - {network.name} ({network.code})')
        
        # Seed commission rates
        rates = seed_default_commission_rates()
        self.stdout.write(self.style.SUCCESS(
            f'✓ Created {len(rates)} commission rates'
        ))
        
        if options['with_samples']:
            self._create_samples()
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Database seeding complete!'))

    def _create_samples(self):
        """Create sample data for testing."""
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Creating sample data...'))
        
        # Create sample user if not exists
        email = 'demo@floatly.cm'
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': 'DemoAgent',
                'full_name': 'Demo Agent',
                'phone_number': '+237677123456',
                'email_verified': True
            }
        )
        
        if created:
            user.set_password('demo1234')
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'✓ Created demo user: {email} (password: demo1234)'
            ))
        else:
            self.stdout.write(f'  Demo user already exists: {email}')
        
        # Create sample kiosk
        if not Kiosk.objects.filter(owner=user).exists():
            kiosk = create_kiosk_with_owner_as_admin(
                name='Demo Kiosk Akwa',
                owner=user,
                location='Akwa, Douala'
            )
            self.stdout.write(self.style.SUCCESS(
                f'✓ Created kiosk: {kiosk.name}'
            ))
            
            # Create sample transactions
            mtn = Network.objects.get(code='MTN')
            om = Network.objects.get(code='OM')
            
            transactions = [
                {'type': 'DEPOSIT', 'amount': 5000, 'network': mtn},
                {'type': 'DEPOSIT', 'amount': 10000, 'network': mtn},
                {'type': 'WITHDRAWAL', 'amount': 8000, 'network': mtn},
                {'type': 'DEPOSIT', 'amount': 25000, 'network': om},
                {'type': 'WITHDRAWAL', 'amount': 15000, 'network': om},
            ]
            
            for tx_data in transactions:
                Transaction.objects.create(
                    kiosk=kiosk,
                    recorded_by=user,
                    network=tx_data['network'],
                    transaction_type=tx_data['type'],
                    amount=Decimal(str(tx_data['amount']))
                )
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ Created {len(transactions)} sample transactions'
            ))
            
            # Show balances
            balances = kiosk.get_balances()
            self.stdout.write('')
            self.stdout.write('  Current Balances:')
            self.stdout.write(f'    Cash:   {balances["cash_balance"]:,.0f} CFA')
            self.stdout.write(f'    Float:  {balances["float_balance"]:,.0f} CFA')
            self.stdout.write(f'    Profit: {balances["total_profit"]:,.0f} CFA')
        else:
            self.stdout.write('  Sample kiosk already exists')
