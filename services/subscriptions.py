# -*- coding: utf-8 -*-
"""
AIMagistr 3.1 - Трекер подписок: ручной ввод + парсинг форвардов
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

class SubscriptionStatus(Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAUSED = "paused"

class PaymentFrequency(Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    WEEKLY = "weekly"
    ONE_TIME = "one_time"

@dataclass
class Subscription:
    id: str
    name: str
    description: str
    provider: str
    amount: float
    currency: str
    payment_frequency: PaymentFrequency
    next_payment_date: datetime
    status: SubscriptionStatus
    created_at: datetime
    last_payment_date: Optional[datetime] = None
    auto_renewal: bool = True
    category: str = "other"
    tags: List[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class Payment:
    id: str
    subscription_id: str
    amount: float
    currency: str
    payment_date: datetime
    status: str  # paid, pending, failed
    method: str  # card, bank, paypal, etc.
    transaction_id: Optional[str] = None
    notes: str = ""

class SubscriptionsService:
    """Сервис трекера подписок"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.subscriptions_file = self.storage_dir / "subscriptions.json"
        self.payments_file = self.storage_dir / "subscription_payments.json"
        
        # Загружаем данные
        self.subscriptions = self._load_subscriptions()
        self.payments = self._load_payments()
    
    def _load_subscriptions(self) -> Dict[str, Subscription]:
        """Загрузка подписок из файла"""
        try:
            if self.subscriptions_file.exists():
                with open(self.subscriptions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    subscriptions = {}
                    for sub_id, sub_data in data.items():
                        sub_data['payment_frequency'] = PaymentFrequency(sub_data['payment_frequency'])
                        sub_data['status'] = SubscriptionStatus(sub_data['status'])
                        sub_data['next_payment_date'] = datetime.fromisoformat(sub_data['next_payment_date'])
                        sub_data['created_at'] = datetime.fromisoformat(sub_data['created_at'])
                        if sub_data.get('last_payment_date'):
                            sub_data['last_payment_date'] = datetime.fromisoformat(sub_data['last_payment_date'])
                        subscriptions[sub_id] = Subscription(**sub_data)
                    return subscriptions
        except Exception as e:
            print(f"Ошибка загрузки подписок: {e}")
        return {}
    
    def _save_subscriptions(self):
        """Сохранение подписок в файл"""
        try:
            data = {}
            for sub_id, subscription in self.subscriptions.items():
                sub_dict = asdict(subscription)
                sub_dict['payment_frequency'] = subscription.payment_frequency.value
                sub_dict['status'] = subscription.status.value
                sub_dict['next_payment_date'] = subscription.next_payment_date.isoformat()
                sub_dict['created_at'] = subscription.created_at.isoformat()
                if subscription.last_payment_date:
                    sub_dict['last_payment_date'] = subscription.last_payment_date.isoformat()
                data[sub_id] = sub_dict
            
            with open(self.subscriptions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения подписок: {e}")
    
    def _load_payments(self) -> Dict[str, Payment]:
        """Загрузка платежей из файла"""
        try:
            if self.payments_file.exists():
                with open(self.payments_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    payments = {}
                    for payment_id, payment_data in data.items():
                        payment_data['payment_date'] = datetime.fromisoformat(payment_data['payment_date'])
                        payments[payment_id] = Payment(**payment_data)
                    return payments
        except Exception as e:
            print(f"Ошибка загрузки платежей: {e}")
        return {}
    
    def _save_payments(self):
        """Сохранение платежей в файл"""
        try:
            data = {}
            for payment_id, payment in self.payments.items():
                payment_dict = asdict(payment)
                payment_dict['payment_date'] = payment.payment_date.isoformat()
                data[payment_id] = payment_dict
            
            with open(self.payments_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения платежей: {e}")
    
    def add_subscription(self, name: str, description: str, provider: str, 
                        amount: float, currency: str, payment_frequency: PaymentFrequency,
                        next_payment_date: datetime, category: str = "other", 
                        tags: List[str] = None, notes: str = "") -> str:
        """Добавление новой подписки"""
        try:
            subscription_id = str(uuid.uuid4())
            
            subscription = Subscription(
                id=subscription_id,
                name=name,
                description=description,
                provider=provider,
                amount=amount,
                currency=currency,
                payment_frequency=payment_frequency,
                next_payment_date=next_payment_date,
                status=SubscriptionStatus.ACTIVE,
                created_at=datetime.now(),
                category=category,
                tags=tags or [],
                notes=notes
            )
            
            self.subscriptions[subscription_id] = subscription
            self._save_subscriptions()
            
            return subscription_id
            
        except Exception as e:
            print(f"Ошибка добавления подписки: {e}")
            return None
    
    def parse_forwarded_message(self, message_text: str) -> Optional[Dict[str, Any]]:
        """Парсинг форвардированного сообщения о подписке"""
        try:
            # Паттерны для распознавания подписок
            patterns = {
                'netflix': r'(?i)netflix.*?(\d+\.?\d*)\s*(\w+)',
                'spotify': r'(?i)spotify.*?(\d+\.?\d*)\s*(\w+)',
                'youtube': r'(?i)youtube.*?(\d+\.?\d*)\s*(\w+)',
                'apple': r'(?i)apple.*?(\d+\.?\d*)\s*(\w+)',
                'google': r'(?i)google.*?(\d+\.?\d*)\s*(\w+)',
                'microsoft': r'(?i)microsoft.*?(\d+\.?\d*)\s*(\w+)',
                'amazon': r'(?i)amazon.*?(\d+\.?\d*)\s*(\w+)',
                'adobe': r'(?i)adobe.*?(\d+\.?\d*)\s*(\w+)',
                'dropbox': r'(?i)dropbox.*?(\d+\.?\d*)\s*(\w+)',
                'github': r'(?i)github.*?(\d+\.?\d*)\s*(\w+)'
            }
            
            for provider, pattern in patterns.items():
                match = re.search(pattern, message_text)
                if match:
                    amount = float(match.group(1))
                    currency = match.group(2).upper()
                    
                    # Определяем частоту платежа
                    if 'monthly' in message_text.lower() or 'ежемесячно' in message_text.lower():
                        frequency = PaymentFrequency.MONTHLY
                    elif 'yearly' in message_text.lower() or 'ежегодно' in message_text.lower():
                        frequency = PaymentFrequency.YEARLY
                    elif 'weekly' in message_text.lower() or 'еженедельно' in message_text.lower():
                        frequency = PaymentFrequency.WEEKLY
                    else:
                        frequency = PaymentFrequency.MONTHLY  # по умолчанию
                    
                    # Определяем дату следующего платежа
                    next_payment = datetime.now() + timedelta(days=30)  # по умолчанию через месяц
                    
                    return {
                        'name': f"{provider.title()} Subscription",
                        'description': f"Auto-detected {provider} subscription",
                        'provider': provider,
                        'amount': amount,
                        'currency': currency,
                        'payment_frequency': frequency,
                        'next_payment_date': next_payment,
                        'category': 'entertainment' if provider in ['netflix', 'spotify', 'youtube'] else 'software'
                    }
            
            return None
            
        except Exception as e:
            print(f"Ошибка парсинга сообщения: {e}")
            return None
    
    def get_subscriptions(self, status: SubscriptionStatus = None) -> List[Subscription]:
        """Получение списка подписок"""
        try:
            subscriptions = list(self.subscriptions.values())
            if status:
                subscriptions = [s for s in subscriptions if s.status == status]
            return sorted(subscriptions, key=lambda x: x.next_payment_date)
        except Exception as e:
            print(f"Ошибка получения подписок: {e}")
            return []
    
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Получение подписки по ID"""
        return self.subscriptions.get(subscription_id)
    
    def update_subscription_status(self, subscription_id: str, status: SubscriptionStatus):
        """Обновление статуса подписки"""
        try:
            if subscription_id in self.subscriptions:
                self.subscriptions[subscription_id].status = status
                self._save_subscriptions()
                return True
        except Exception as e:
            print(f"Ошибка обновления статуса подписки: {e}")
        return False
    
    def record_payment(self, subscription_id: str, amount: float, currency: str, 
                      payment_date: datetime, method: str = "card", 
                      transaction_id: str = None, notes: str = "") -> str:
        """Запись платежа"""
        try:
            payment_id = str(uuid.uuid4())
            
            payment = Payment(
                id=payment_id,
                subscription_id=subscription_id,
                amount=amount,
                currency=currency,
                payment_date=payment_date,
                status="paid",
                method=method,
                transaction_id=transaction_id,
                notes=notes
            )
            
            self.payments[payment_id] = payment
            
            # Обновляем подписку
            if subscription_id in self.subscriptions:
                subscription = self.subscriptions[subscription_id]
                subscription.last_payment_date = payment_date
                
                # Обновляем дату следующего платежа
                if subscription.payment_frequency == PaymentFrequency.MONTHLY:
                    subscription.next_payment_date = payment_date + timedelta(days=30)
                elif subscription.payment_frequency == PaymentFrequency.YEARLY:
                    subscription.next_payment_date = payment_date + timedelta(days=365)
                elif subscription.payment_frequency == PaymentFrequency.WEEKLY:
                    subscription.next_payment_date = payment_date + timedelta(days=7)
                
                self._save_subscriptions()
            
            self._save_payments()
            return payment_id
            
        except Exception as e:
            print(f"Ошибка записи платежа: {e}")
            return None
    
    def get_upcoming_payments(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Получение предстоящих платежей"""
        try:
            now = datetime.now()
            end_date = now + timedelta(days=days_ahead)
            
            upcoming = []
            for subscription in self.subscriptions.values():
                if (subscription.status == SubscriptionStatus.ACTIVE and 
                    subscription.next_payment_date <= end_date):
                    upcoming.append({
                        'subscription_id': subscription.id,
                        'name': subscription.name,
                        'amount': subscription.amount,
                        'currency': subscription.currency,
                        'next_payment_date': subscription.next_payment_date,
                        'days_until_payment': (subscription.next_payment_date - now).days
                    })
            
            return sorted(upcoming, key=lambda x: x['next_payment_date'])
        except Exception as e:
            print(f"Ошибка получения предстоящих платежей: {e}")
            return []
    
    def get_expenses_by_category(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Получение расходов по категориям"""
        try:
            expenses = {}
            for payment in self.payments.values():
                if (start_date <= payment.payment_date <= end_date and 
                    payment.status == "paid"):
                    subscription = self.get_subscription(payment.subscription_id)
                    if subscription:
                        category = subscription.category
                        if category not in expenses:
                            expenses[category] = 0
                        expenses[category] += payment.amount
            
            return expenses
        except Exception as e:
            print(f"Ошибка получения расходов по категориям: {e}")
            return {}
    
    def get_monthly_expenses(self, year: int, month: int) -> Dict[str, Any]:
        """Получение месячных расходов"""
        try:
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)
            
            total_expenses = 0
            category_expenses = {}
            subscription_expenses = {}
            
            for payment in self.payments.values():
                if (start_date <= payment.payment_date < end_date and 
                    payment.status == "paid"):
                    total_expenses += payment.amount
                    
                    subscription = self.get_subscription(payment.subscription_id)
                    if subscription:
                        category = subscription.category
                        if category not in category_expenses:
                            category_expenses[category] = 0
                        category_expenses[category] += payment.amount
                        
                        if subscription.name not in subscription_expenses:
                            subscription_expenses[subscription.name] = 0
                        subscription_expenses[subscription.name] += payment.amount
            
            return {
                'month': month,
                'year': year,
                'total_expenses': total_expenses,
                'category_expenses': category_expenses,
                'subscription_expenses': subscription_expenses,
                'payment_count': len([p for p in self.payments.values() 
                                    if start_date <= p.payment_date < end_date and p.status == "paid"])
            }
        except Exception as e:
            print(f"Ошибка получения месячных расходов: {e}")
            return {}
    
    def get_subscription_stats(self, subscription_id: str) -> Dict[str, Any]:
        """Получение статистики подписки"""
        try:
            subscription = self.get_subscription(subscription_id)
            if not subscription:
                return {}
            
            # Получаем все платежи по подписке
            subscription_payments = [p for p in self.payments.values() 
                                  if p.subscription_id == subscription_id and p.status == "paid"]
            
            total_paid = sum(p.amount for p in subscription_payments)
            payment_count = len(subscription_payments)
            avg_payment = total_paid / max(1, payment_count)
            
            # Последний платеж
            last_payment = max(subscription_payments, key=lambda x: x.payment_date) if subscription_payments else None
            
            return {
                'subscription_id': subscription_id,
                'name': subscription.name,
                'total_paid': total_paid,
                'payment_count': payment_count,
                'avg_payment': avg_payment,
                'last_payment_date': last_payment.payment_date.isoformat() if last_payment else None,
                'next_payment_date': subscription.next_payment_date.isoformat(),
                'status': subscription.status.value,
                'auto_renewal': subscription.auto_renewal
            }
        except Exception as e:
            print(f"Ошибка получения статистики подписки: {e}")
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Получение общей статистики"""
        try:
            active_subscriptions = len([s for s in self.subscriptions.values() 
                                       if s.status == SubscriptionStatus.ACTIVE])
            total_monthly_cost = sum(s.amount for s in self.subscriptions.values() 
                                   if s.status == SubscriptionStatus.ACTIVE and 
                                   s.payment_frequency == PaymentFrequency.MONTHLY)
            total_yearly_cost = sum(s.amount for s in self.subscriptions.values() 
                                  if s.status == SubscriptionStatus.ACTIVE and 
                                  s.payment_frequency == PaymentFrequency.YEARLY)
            
            return {
                'total_subscriptions': len(self.subscriptions),
                'active_subscriptions': active_subscriptions,
                'total_monthly_cost': total_monthly_cost,
                'total_yearly_cost': total_yearly_cost,
                'total_payments': len(self.payments),
                'total_paid': sum(p.amount for p in self.payments.values() if p.status == "paid")
            }
        except Exception as e:
            print(f"Ошибка получения общей статистики: {e}")
            return {}
    
    def export_subscriptions(self, format: str = "json") -> str:
        """Экспорт подписок"""
        try:
            if format == "json":
                return json.dumps({s.id: asdict(s) for s in self.subscriptions.values()}, 
                                 ensure_ascii=False, indent=2, default=str)
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Name", "Provider", "Amount", "Currency", "Frequency", "Status", "Next Payment"])
                for subscription in self.subscriptions.values():
                    writer.writerow([
                        subscription.name,
                        subscription.provider,
                        subscription.amount,
                        subscription.currency,
                        subscription.payment_frequency.value,
                        subscription.status.value,
                        subscription.next_payment_date.strftime("%Y-%m-%d")
                    ])
                return output.getvalue()
            else:
                return "Unsupported format"
        except Exception as e:
            print(f"Ошибка экспорта подписок: {e}")
            return ""

# Тестирование
if __name__ == "__main__":
    service = SubscriptionsService()
    
    # Добавляем тестовую подписку
    subscription_id = service.add_subscription(
        name="Netflix Premium",
        description="Streaming service",
        provider="Netflix",
        amount=15.99,
        currency="USD",
        payment_frequency=PaymentFrequency.MONTHLY,
        next_payment_date=datetime.now() + timedelta(days=30),
        category="entertainment"
    )
    
    print(f"Добавлена подписка: {subscription_id}")
    print(f"Статистика: {service.get_all_stats()}")
    print(f"Предстоящие платежи: {len(service.get_upcoming_payments())}")
