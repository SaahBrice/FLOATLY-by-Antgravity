"""
Report generation service for Floatly.

Calculates all analytics metrics for a kiosk on a given date.
"""

import logging
from decimal import Decimal
from datetime import timedelta
from collections import Counter
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import ExtractHour, Coalesce
from django.utils import timezone

logger = logging.getLogger('core')


def generate_report_data(kiosk, date=None):
    """
    Generate all analytics metrics for a kiosk on a given date.
    
    Returns a dictionary with all 13 metrics.
    """
    from .models import Transaction, Network, DailyOpeningBalance
    
    if date is None:
        date = timezone.now().date()
    
    # Get today's transactions
    today_txs = Transaction.objects.filter(
        kiosk=kiosk,
        timestamp__date=date
    )
    
    # Get yesterday's transactions
    yesterday = date - timedelta(days=1)
    yesterday_txs = Transaction.objects.filter(
        kiosk=kiosk,
        timestamp__date=yesterday
    )
    
    # Get last week's same day
    same_day_last_week = date - timedelta(days=7)
    last_week_txs = Transaction.objects.filter(
        kiosk=kiosk,
        timestamp__date=same_day_last_week
    )
    
    # Get last 30 days for comparison
    thirty_days_ago = date - timedelta(days=30)
    last_30_days_txs = Transaction.objects.filter(
        kiosk=kiosk,
        timestamp__date__gte=thirty_days_ago,
        timestamp__date__lt=date
    )
    
    # Get balances
    balances = kiosk.transactions.filter(
        timestamp__date=date
    ).calculate_balances(date=date, kiosk=kiosk)
    
    # Calculate metrics
    data = {}
    
    # 1. Total profit earned today
    data['total_profit'] = float(today_txs.aggregate(
        total=Coalesce(Sum('profit'), Decimal('0'))
    )['total'])
    
    # 2. Current cash balance
    data['cash_balance'] = float(balances.get('cash_balance', 0))
    
    # 3. Float balance per network and total
    data['float_balance'] = float(balances.get('float_balance', 0))
    float_per_network_raw = balances.get('float_per_network', {})
    data['float_per_network'] = [
        {
            'network_id': item['network'].id,
            'network_name': item['network'].name,
            'network_code': item['network'].code,
            'network_color': item['network'].color,
            'balance': float(item['balance']),
        }
        for item in float_per_network_raw.values() if isinstance(item, dict) and 'network' in item
    ]
    
    # 4. Transaction count by type
    tx_counts = today_txs.values('transaction_type').annotate(count=Count('id'))
    data['transaction_count'] = today_txs.count()
    data['deposit_count'] = 0
    data['withdrawal_count'] = 0
    for item in tx_counts:
        if item['transaction_type'] == 'DEPOSIT':
            data['deposit_count'] = item['count']
        elif item['transaction_type'] == 'WITHDRAWAL':
            data['withdrawal_count'] = item['count']
    
    # 5. Comparison to yesterday
    yesterday_profit = float(yesterday_txs.aggregate(
        total=Coalesce(Sum('profit'), Decimal('0'))
    )['total'])
    if yesterday_profit > 0:
        data['vs_yesterday_percent'] = round(
            ((data['total_profit'] - yesterday_profit) / yesterday_profit) * 100, 1
        )
    else:
        data['vs_yesterday_percent'] = 0 if data['total_profit'] == 0 else 100
    
    # 6. Week-over-week comparison
    last_week_profit = float(last_week_txs.aggregate(
        total=Coalesce(Sum('profit'), Decimal('0'))
    )['total'])
    if last_week_profit > 0:
        data['vs_last_week_percent'] = round(
            ((data['total_profit'] - last_week_profit) / last_week_profit) * 100, 1
        )
    else:
        data['vs_last_week_percent'] = 0 if data['total_profit'] == 0 else 100
    
    # Monthly average for comparison
    monthly_avg_profit = float(last_30_days_txs.aggregate(
        avg=Coalesce(Avg('profit'), Decimal('0'))
    )['avg'] or 0)
    data['monthly_avg_profit'] = monthly_avg_profit
    
    # 7. Top 3 customers by transaction value (this week)
    week_start = date - timedelta(days=7)
    top_customers = Transaction.objects.filter(
        kiosk=kiosk,
        timestamp__date__gte=week_start,
        timestamp__date__lte=date,
        customer_phone__isnull=False
    ).exclude(
        customer_phone=''
    ).values('customer_phone').annotate(
        total_amount=Sum('amount'),
        tx_count=Count('id')
    ).order_by('-total_amount')[:3]
    
    data['top_customers'] = [
        {
            'phone': c['customer_phone'],
            'total_amount': float(c['total_amount']),
            'transaction_count': c['tx_count']
        }
        for c in top_customers
    ]
    
    # 8. Busiest hour of the day
    hourly_counts = today_txs.annotate(
        hour=ExtractHour('timestamp')
    ).values('hour').annotate(count=Count('id')).order_by('-count')
    
    if hourly_counts:
        data['busiest_hour'] = hourly_counts[0]['hour']
        data['busiest_hour_count'] = hourly_counts[0]['count']
    else:
        data['busiest_hour'] = None
        data['busiest_hour_count'] = 0
    
    # 9. Float depletion rate (days until running out)
    # Calculate average daily float usage
    last_7_days = Transaction.objects.filter(
        kiosk=kiosk,
        transaction_type='DEPOSIT',  # Deposits consume float
        timestamp__date__gte=date - timedelta(days=7),
        timestamp__date__lte=date
    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
    
    avg_daily_float_usage = float(last_7_days) / 7 if last_7_days else 0
    
    if avg_daily_float_usage > 0 and data['float_balance'] > 0:
        data['float_days_remaining'] = round(data['float_balance'] / avg_daily_float_usage, 1)
    else:
        data['float_days_remaining'] = None  # Not enough data
    
    # 10. Cash runway (same concept for cash)
    last_7_days_cash = Transaction.objects.filter(
        kiosk=kiosk,
        transaction_type='WITHDRAWAL',  # Withdrawals consume cash
        timestamp__date__gte=date - timedelta(days=7),
        timestamp__date__lte=date
    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
    
    avg_daily_cash_usage = float(last_7_days_cash) / 7 if last_7_days_cash else 0
    
    if avg_daily_cash_usage > 0 and data['cash_balance'] > 0:
        data['cash_days_remaining'] = round(data['cash_balance'] / avg_daily_cash_usage, 1)
    else:
        data['cash_days_remaining'] = None
    
    # 11. Network distribution (percentage)
    network_breakdown = today_txs.values(
        'network__id', 'network__name', 'network__code', 'network__color'
    ).annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    ).order_by('-count')
    
    total_tx = data['transaction_count'] or 1  # Avoid division by zero
    data['network_distribution'] = [
        {
            'network_id': n['network__id'],
            'network_name': n['network__name'],
            'network_code': n['network__code'],
            'network_color': n['network__color'],
            'count': n['count'],
            'total_amount': float(n['total_amount']),
            'percentage': round((n['count'] / total_tx) * 100, 1)
        }
        for n in network_breakdown
    ]
    
    # 12. Average transaction size
    if data['transaction_count'] > 0:
        total_volume = float(today_txs.aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'))
        )['total'])
        data['avg_transaction_size'] = round(total_volume / data['transaction_count'], 2)
        data['total_volume'] = total_volume
    else:
        data['avg_transaction_size'] = 0
        data['total_volume'] = 0
    
    # 13. Low balance alerts
    LOW_BALANCE_THRESHOLD = 50000  # CFA
    data['low_balance_alerts'] = []
    
    for network_float in data['float_per_network']:
        if network_float['balance'] < LOW_BALANCE_THRESHOLD:
            data['low_balance_alerts'].append({
                'network_name': network_float['network_name'],
                'network_code': network_float['network_code'],
                'balance': network_float['balance'],
                'threshold': LOW_BALANCE_THRESHOLD
            })
    
    # Also check cash
    if data['cash_balance'] < LOW_BALANCE_THRESHOLD:
        data['low_balance_alerts'].append({
            'network_name': 'Cash',
            'network_code': 'CASH',
            'balance': data['cash_balance'],
            'threshold': LOW_BALANCE_THRESHOLD
        })
    
    # 14. Profit per transaction (efficiency metric)
    if data['transaction_count'] > 0:
        data['profit_per_transaction'] = round(data['total_profit'] / data['transaction_count'], 2)
    else:
        data['profit_per_transaction'] = 0
    
    # 15. Hourly activity breakdown (for chart)
    hourly_data = today_txs.annotate(
        hour=ExtractHour('timestamp')
    ).values('hour').annotate(
        count=Count('id'),
        amount=Coalesce(Sum('amount'), Decimal('0')),
        profit=Coalesce(Sum('profit'), Decimal('0'))
    ).order_by('hour')
    
    data['hourly_breakdown'] = [
        {
            'hour': h['hour'],
            'count': h['count'],
            'amount': float(h['amount']),
            'profit': float(h['profit']),
        }
        for h in hourly_data
    ]
    
    # 16. Profit trend (last 7 days)
    profit_trend = []
    for i in range(7):
        trend_date = date - timedelta(days=i)
        day_profit = float(Transaction.objects.filter(
            kiosk=kiosk,
            timestamp__date=trend_date
        ).aggregate(total=Coalesce(Sum('profit'), Decimal('0')))['total'])
        profit_trend.append({
            'date': trend_date.isoformat(),
            'day': trend_date.strftime('%a'),
            'profit': day_profit
        })
    data['profit_trend'] = list(reversed(profit_trend))
    
    # 17. Success streak (consecutive profitable days)
    streak = 0
    check_date = date
    while True:
        day_profit = Transaction.objects.filter(
            kiosk=kiosk,
            timestamp__date=check_date
        ).aggregate(total=Coalesce(Sum('profit'), Decimal('0')))['total']
        if day_profit > 0:
            streak += 1
            check_date = check_date - timedelta(days=1)
        else:
            break
        if streak >= 30:  # Cap at 30 days
            break
    data['profit_streak'] = streak
    
    # 18. Growth indicators
    data['is_growing'] = data['vs_yesterday_percent'] > 0 and data['vs_last_week_percent'] > 0
    data['needs_attention'] = len(data['low_balance_alerts']) > 0
    
    # Metadata
    data['generated_at'] = timezone.now().isoformat()
    data['kiosk_name'] = kiosk.name
    data['report_version'] = '2.0'
    
    return data
