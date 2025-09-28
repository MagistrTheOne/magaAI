# -*- coding: utf-8 -*-
"""
AIMagistr 3.1 - Помощник путешествий: маршруты из билетов/отелей (PDF/скрины)
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

class TravelType(Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    TRAIN = "train"
    BUS = "bus"
    CAR_RENTAL = "car_rental"
    ACTIVITY = "activity"

class TravelStatus(Enum):
    CONFIRMED = "confirmed"
    PENDING = "pending"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

@dataclass
class TravelBooking:
    id: str
    travel_type: TravelType
    title: str
    description: str
    departure_location: str
    arrival_location: str
    departure_date: datetime
    arrival_date: Optional[datetime] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    booking_reference: str = ""
    status: TravelStatus = TravelStatus.CONFIRMED
    created_at: datetime = None
    price: Optional[float] = None
    currency: str = "USD"
    provider: str = ""
    confirmation_number: str = ""
    notes: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.tags is None:
            self.tags = []

@dataclass
class TravelItinerary:
    id: str
    title: str
    description: str
    start_date: datetime
    end_date: datetime
    destination: str
    bookings: List[str]  # IDs of bookings
    created_at: datetime
    status: str = "active"
    notes: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class TravelAssistantService:
    """Сервис помощника путешествий"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.bookings_file = self.storage_dir / "travel_bookings.json"
        self.itineraries_file = self.storage_dir / "travel_itineraries.json"
        
        # Загружаем данные
        self.bookings = self._load_bookings()
        self.itineraries = self._load_itineraries()
    
    def _load_bookings(self) -> Dict[str, TravelBooking]:
        """Загрузка бронирований из файла"""
        try:
            if self.bookings_file.exists():
                with open(self.bookings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    bookings = {}
                    for booking_id, booking_data in data.items():
                        booking_data['travel_type'] = TravelType(booking_data['travel_type'])
                        booking_data['status'] = TravelStatus(booking_data['status'])
                        booking_data['departure_date'] = datetime.fromisoformat(booking_data['departure_date'])
                        if booking_data.get('arrival_date'):
                            booking_data['arrival_date'] = datetime.fromisoformat(booking_data['arrival_date'])
                        booking_data['created_at'] = datetime.fromisoformat(booking_data['created_at'])
                        bookings[booking_id] = TravelBooking(**booking_data)
                    return bookings
        except Exception as e:
            print(f"Ошибка загрузки бронирований: {e}")
        return {}
    
    def _save_bookings(self):
        """Сохранение бронирований в файл"""
        try:
            data = {}
            for booking_id, booking in self.bookings.items():
                booking_dict = asdict(booking)
                booking_dict['travel_type'] = booking.travel_type.value
                booking_dict['status'] = booking.status.value
                booking_dict['departure_date'] = booking.departure_date.isoformat()
                if booking.arrival_date:
                    booking_dict['arrival_date'] = booking.arrival_date.isoformat()
                booking_dict['created_at'] = booking.created_at.isoformat()
                data[booking_id] = booking_dict
            
            with open(self.bookings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения бронирований: {e}")
    
    def _load_itineraries(self) -> Dict[str, TravelItinerary]:
        """Загрузка маршрутов из файла"""
        try:
            if self.itineraries_file.exists():
                with open(self.itineraries_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    itineraries = {}
                    for itinerary_id, itinerary_data in data.items():
                        itinerary_data['start_date'] = datetime.fromisoformat(itinerary_data['start_date'])
                        itinerary_data['end_date'] = datetime.fromisoformat(itinerary_data['end_date'])
                        itinerary_data['created_at'] = datetime.fromisoformat(itinerary_data['created_at'])
                        itineraries[itinerary_id] = TravelItinerary(**itinerary_data)
                    return itineraries
        except Exception as e:
            print(f"Ошибка загрузки маршрутов: {e}")
        return {}
    
    def _save_itineraries(self):
        """Сохранение маршрутов в файл"""
        try:
            data = {}
            for itinerary_id, itinerary in self.itineraries.items():
                itinerary_dict = asdict(itinerary)
                itinerary_dict['start_date'] = itinerary.start_date.isoformat()
                itinerary_dict['end_date'] = itinerary.end_date.isoformat()
                itinerary_dict['created_at'] = itinerary.created_at.isoformat()
                data[itinerary_id] = itinerary_dict
            
            with open(self.itineraries_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения маршрутов: {e}")
    
    def parse_booking_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Парсинг текста бронирования"""
        try:
            # Паттерны для распознавания бронирований
            patterns = {
                'flight': {
                    'pattern': r'(?i)(?:рейс|flight|авиабилет).*?(\w{2,3})\s*(\d+).*?(\w{3})\s*(\w{3}).*?(\d{1,2}[./]\d{1,2}[./]\d{2,4}).*?(\d{1,2}:\d{2})',
                    'groups': ['airline', 'flight_number', 'departure', 'arrival', 'date', 'time']
                },
                'hotel': {
                    'pattern': r'(?i)(?:отель|hotel|гостиница).*?([^,]+).*?(\d{1,2}[./]\d{1,2}[./]\d{2,4}).*?(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
                    'groups': ['hotel_name', 'check_in', 'check_out']
                },
                'train': {
                    'pattern': r'(?i)(?:поезд|train|поездка).*?(\w+)\s*(\d+).*?(\w+)\s*(\w+).*?(\d{1,2}[./]\d{1,2}[./]\d{2,4}).*?(\d{1,2}:\d{2})',
                    'groups': ['train_company', 'train_number', 'departure', 'arrival', 'date', 'time']
                }
            }
            
            for travel_type, pattern_info in patterns.items():
                match = re.search(pattern_info['pattern'], text)
                if match:
                    groups = match.groups()
                    result = {
                        'travel_type': travel_type,
                        'raw_text': text,
                        'confidence': 0.8
                    }
                    
                    # Заполняем поля в зависимости от типа
                    if travel_type == 'flight':
                        result.update({
                            'airline': groups[0],
                            'flight_number': groups[1],
                            'departure': groups[2],
                            'arrival': groups[3],
                            'date': groups[4],
                            'time': groups[5]
                        })
                    elif travel_type == 'hotel':
                        result.update({
                            'hotel_name': groups[0],
                            'check_in': groups[1],
                            'check_out': groups[2]
                        })
                    elif travel_type == 'train':
                        result.update({
                            'train_company': groups[0],
                            'train_number': groups[1],
                            'departure': groups[2],
                            'arrival': groups[3],
                            'date': groups[4],
                            'time': groups[5]
                        })
                    
                    return result
            
            return None
            
        except Exception as e:
            print(f"Ошибка парсинга текста бронирования: {e}")
            return None
    
    def add_booking(self, travel_type: TravelType, title: str, description: str,
                   departure_location: str, arrival_location: str, departure_date: datetime,
                   arrival_date: Optional[datetime] = None, departure_time: Optional[str] = None,
                   arrival_time: Optional[str] = None, booking_reference: str = "",
                   price: Optional[float] = None, currency: str = "USD", provider: str = "",
                   confirmation_number: str = "", notes: str = "", tags: List[str] = None) -> str:
        """Добавление нового бронирования"""
        try:
            booking_id = str(uuid.uuid4())
            
            booking = TravelBooking(
                id=booking_id,
                travel_type=travel_type,
                title=title,
                description=description,
                departure_location=departure_location,
                arrival_location=arrival_location,
                departure_date=departure_date,
                arrival_date=arrival_date,
                departure_time=departure_time,
                arrival_time=arrival_time,
                booking_reference=booking_reference,
                price=price,
                currency=currency,
                provider=provider,
                confirmation_number=confirmation_number,
                notes=notes,
                tags=tags or []
            )
            
            self.bookings[booking_id] = booking
            self._save_bookings()
            
            return booking_id
            
        except Exception as e:
            print(f"Ошибка добавления бронирования: {e}")
            return None
    
    def create_itinerary(self, title: str, description: str, start_date: datetime,
                        end_date: datetime, destination: str, booking_ids: List[str] = None,
                        notes: str = "", tags: List[str] = None) -> str:
        """Создание маршрута"""
        try:
            itinerary_id = str(uuid.uuid4())
            
            itinerary = TravelItinerary(
                id=itinerary_id,
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date,
                destination=destination,
                bookings=booking_ids or [],
                notes=notes,
                tags=tags or []
            )
            
            self.itineraries[itinerary_id] = itinerary
            self._save_itineraries()
            
            return itinerary_id
            
        except Exception as e:
            print(f"Ошибка создания маршрута: {e}")
            return None
    
    def get_bookings(self, travel_type: TravelType = None, status: TravelStatus = None) -> List[TravelBooking]:
        """Получение списка бронирований"""
        try:
            bookings = list(self.bookings.values())
            if travel_type:
                bookings = [b for b in bookings if b.travel_type == travel_type]
            if status:
                bookings = [b for b in bookings if b.status == status]
            return sorted(bookings, key=lambda x: x.departure_date)
        except Exception as e:
            print(f"Ошибка получения бронирований: {e}")
            return []
    
    def get_itineraries(self, status: str = None) -> List[TravelItinerary]:
        """Получение списка маршрутов"""
        try:
            itineraries = list(self.itineraries.values())
            if status:
                itineraries = [i for i in itineraries if i.status == status]
            return sorted(itineraries, key=lambda x: x.start_date)
        except Exception as e:
            print(f"Ошибка получения маршрутов: {e}")
            return []
    
    def get_upcoming_travels(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Получение предстоящих поездок"""
        try:
            now = datetime.now()
            end_date = now + timedelta(days=days_ahead)
            
            upcoming = []
            for booking in self.bookings.values():
                if (booking.status == TravelStatus.CONFIRMED and 
                    booking.departure_date <= end_date):
                    upcoming.append({
                        'booking_id': booking.id,
                        'title': booking.title,
                        'travel_type': booking.travel_type.value,
                        'departure_location': booking.departure_location,
                        'arrival_location': booking.arrival_location,
                        'departure_date': booking.departure_date,
                        'departure_time': booking.departure_time,
                        'days_until_departure': (booking.departure_date - now).days
                    })
            
            return sorted(upcoming, key=lambda x: x['departure_date'])
        except Exception as e:
            print(f"Ошибка получения предстоящих поездок: {e}")
            return []
    
    def get_travel_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Получение сводки по поездкам за период"""
        try:
            bookings_in_period = []
            for booking in self.bookings.values():
                if start_date <= booking.departure_date <= end_date:
                    bookings_in_period.append(booking)
            
            # Группируем по типам
            by_type = {}
            for booking in bookings_in_period:
                travel_type = booking.travel_type.value
                if travel_type not in by_type:
                    by_type[travel_type] = []
                by_type[travel_type].append(booking)
            
            # Подсчитываем статистику
            total_bookings = len(bookings_in_period)
            total_cost = sum(b.price for b in bookings_in_period if b.price)
            destinations = list(set(b.arrival_location for b in bookings_in_period))
            
            return {
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'total_bookings': total_bookings,
                'total_cost': total_cost,
                'destinations': destinations,
                'by_type': {k: len(v) for k, v in by_type.items()},
                'bookings': [asdict(b) for b in bookings_in_period]
            }
        except Exception as e:
            print(f"Ошибка получения сводки по поездкам: {e}")
            return {}
    
    def get_booking_stats(self, booking_id: str) -> Dict[str, Any]:
        """Получение статистики бронирования"""
        try:
            booking = self.bookings.get(booking_id)
            if not booking:
                return {}
            
            return {
                'booking_id': booking_id,
                'title': booking.title,
                'travel_type': booking.travel_type.value,
                'departure_location': booking.departure_location,
                'arrival_location': booking.arrival_location,
                'departure_date': booking.departure_date.isoformat(),
                'arrival_date': booking.arrival_date.isoformat() if booking.arrival_date else None,
                'departure_time': booking.departure_time,
                'arrival_time': booking.arrival_time,
                'price': booking.price,
                'currency': booking.currency,
                'provider': booking.provider,
                'status': booking.status.value,
                'booking_reference': booking.booking_reference,
                'confirmation_number': booking.confirmation_number
            }
        except Exception as e:
            print(f"Ошибка получения статистики бронирования: {e}")
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Получение общей статистики"""
        try:
            total_bookings = len(self.bookings)
            confirmed_bookings = len([b for b in self.bookings.values() if b.status == TravelStatus.CONFIRMED])
            total_cost = sum(b.price for b in self.bookings.values() if b.price)
            
            # Группируем по типам
            by_type = {}
            for booking in self.bookings.values():
                travel_type = booking.travel_type.value
                if travel_type not in by_type:
                    by_type[travel_type] = 0
                by_type[travel_type] += 1
            
            return {
                'total_bookings': total_bookings,
                'confirmed_bookings': confirmed_bookings,
                'total_cost': total_cost,
                'by_type': by_type,
                'total_itineraries': len(self.itineraries)
            }
        except Exception as e:
            print(f"Ошибка получения общей статистики: {e}")
            return {}
    
    def export_bookings(self, format: str = "json") -> str:
        """Экспорт бронирований"""
        try:
            if format == "json":
                return json.dumps({b.id: asdict(b) for b in self.bookings.values()}, 
                                 ensure_ascii=False, indent=2, default=str)
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Title", "Type", "Departure", "Arrival", "Date", "Time", "Price", "Status"])
                for booking in self.bookings.values():
                    writer.writerow([
                        booking.title,
                        booking.travel_type.value,
                        booking.departure_location,
                        booking.arrival_location,
                        booking.departure_date.strftime("%Y-%m-%d"),
                        booking.departure_time or "",
                        booking.price or "",
                        booking.status.value
                    ])
                return output.getvalue()
            else:
                return "Unsupported format"
        except Exception as e:
            print(f"Ошибка экспорта бронирований: {e}")
            return ""

# Тестирование
if __name__ == "__main__":
    service = TravelAssistantService()
    
    # Добавляем тестовое бронирование
    booking_id = service.add_booking(
        travel_type=TravelType.FLIGHT,
        title="Flight to Paris",
        description="Business trip",
        departure_location="Moscow",
        arrival_location="Paris",
        departure_date=datetime.now() + timedelta(days=30),
        arrival_date=datetime.now() + timedelta(days=30, hours=3),
        departure_time="10:30",
        arrival_time="13:30",
        price=500.0,
        currency="USD",
        provider="Aeroflot"
    )
    
    print(f"Добавлено бронирование: {booking_id}")
    print(f"Статистика: {service.get_all_stats()}")
    print(f"Предстоящие поездки: {len(service.get_upcoming_travels())}")
