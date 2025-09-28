# -*- coding: utf-8 -*-
"""
Mail + Calendar Module
Outlook COM/SMTP/IMAP и .ics автослоты
"""

import os
import time
import threading
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Callable
import json
from datetime import datetime, timedelta
import icalendar
from pathlib import Path


class MailCalendar:
    """
    Управление почтой и календарем
    """
    
    def __init__(self, 
                 on_mail_received: Optional[Callable] = None,
                 on_calendar_event: Optional[Callable] = None):
        """
        Args:
            on_mail_received: Callback при получении письма
            on_calendar_event: Callback при событии календаря
        """
        self.on_mail_received = on_mail_received
        self.on_calendar_event = on_calendar_event
        
        # Конфигурация почты
        self.smtp_config = None
        self.imap_config = None
        self.outlook_config = None
        
        # Состояние
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_check_time = time.time()
        
        # История
        self.mail_history = []
        self.calendar_events = []
        
    def configure_smtp(self, 
                      smtp_server: str,
                      smtp_port: int,
                      username: str,
                      password: str,
                      use_tls: bool = True):
        """Настройка SMTP"""
        self.smtp_config = {
            'server': smtp_server,
            'port': smtp_port,
            'username': username,
            'password': password,
            'use_tls': use_tls
        }
        
    def configure_imap(self,
                      imap_server: str,
                      imap_port: int,
                      username: str,
                      password: str,
                      use_ssl: bool = True):
        """Настройка IMAP"""
        self.imap_config = {
            'server': imap_server,
            'port': imap_port,
            'username': username,
            'password': password,
            'use_ssl': use_ssl
        }
        
    def configure_outlook(self, profile_name: str = "Outlook"):
        """Настройка Outlook COM"""
        self.outlook_config = {
            'profile_name': profile_name,
            'com_available': False
        }
        
        # Проверяем доступность COM
        try:
            import win32com.client
            self.outlook_config['com_available'] = True
        except ImportError:
            print("[MailCalendar] win32com не установлен - Outlook COM недоступен")
            
    def start_monitoring(self):
        """Запуск мониторинга почты и календаря"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
            
    def _monitor_worker(self):
        """Поток мониторинга"""
        while self.is_monitoring:
            try:
                # Проверяем почту
                if self.imap_config:
                    self._check_mail()
                    
                # Проверяем календарь
                if self.outlook_config and self.outlook_config['com_available']:
                    self._check_calendar()
                    
            except Exception as e:
                print(f"[MailCalendar] Ошибка мониторинга: {e}")
                
            time.sleep(30)  # Проверяем каждые 30 секунд
            
    def _check_mail(self):
        """Проверка новых писем"""
        try:
            if self.imap_config['use_ssl']:
                mail = imaplib.IMAP4_SSL(self.imap_config['server'], self.imap_config['port'])
            else:
                mail = imaplib.IMAP4(self.imap_config['server'], self.imap_config['port'])
                
            mail.login(self.imap_config['username'], self.imap_config['password'])
            mail.select('inbox')
            
            # Поиск непрочитанных писем
            status, messages = mail.search(None, 'UNSEEN')
            
            if status == 'OK':
                for msg_id in messages[0].split():
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    
                    if status == 'OK':
                        email_message = email.message_from_bytes(msg_data[0][1])
                        
                        # Обрабатываем письмо
                        self._process_mail(email_message)
                        
            mail.close()
            mail.logout()
            
        except Exception as e:
            print(f"[MailCalendar] Ошибка проверки почты: {e}")
            
    def _process_mail(self, email_message):
        """Обработка полученного письма"""
        try:
            mail_info = {
                'from': email_message.get('From', ''),
                'to': email_message.get('To', ''),
                'subject': email_message.get('Subject', ''),
                'date': email_message.get('Date', ''),
                'body': self._extract_body(email_message),
                'timestamp': time.time()
            }
            
            # Добавляем в историю
            self.mail_history.append(mail_info)
            
            # Ограничиваем историю
            if len(self.mail_history) > 1000:
                self.mail_history = self.mail_history[-500:]
                
            # Вызываем callback
            if self.on_mail_received:
                self.on_mail_received(mail_info)
                
        except Exception as e:
            print(f"[MailCalendar] Ошибка обработки письма: {e}")
            
    def _extract_body(self, email_message) -> str:
        """Извлечение тела письма"""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        return part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                return email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        except Exception:
            return ""
            
    def _check_calendar(self):
        """Проверка календаря Outlook"""
        try:
            import win32com.client
            
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            calendar = namespace.GetDefaultFolder(9)  # olFolderCalendar
            
            # Получаем события на сегодня
            today = datetime.now().date()
            start_time = datetime.combine(today, datetime.min.time())
            end_time = start_time + timedelta(days=1)
            
            items = calendar.Items
            items.Sort("[Start]")
            items.IncludeRecurrences = True
            
            events = items.Restrict(f"[Start] >= '{start_time.strftime('%m/%d/%Y %H:%M %p')}' AND [Start] < '{end_time.strftime('%m/%d/%Y %H:%M %p')}'")
            
            for event in events:
                event_info = {
                    'subject': event.Subject,
                    'start': event.Start,
                    'end': event.End,
                    'location': event.Location,
                    'body': event.Body,
                    'organizer': event.Organizer,
                    'required_attendees': event.RequiredAttendees,
                    'optional_attendees': event.OptionalAttendees,
                    'timestamp': time.time()
                }
                
                # Проверяем, новое ли это событие
                if not any(e['subject'] == event_info['subject'] and 
                          e['start'] == event_info['start'] for e in self.calendar_events):
                    self.calendar_events.append(event_info)
                    
                    # Вызываем callback
                    if self.on_calendar_event:
                        self.on_calendar_event(event_info)
                        
        except Exception as e:
            print(f"[MailCalendar] Ошибка проверки календаря: {e}")
            
    def send_email(self, 
                   to: str,
                   subject: str,
                   body: str,
                   attachments: List[str] = None) -> bool:
        """Отправка письма"""
        try:
            if not self.smtp_config:
                print("[MailCalendar] SMTP не настроен")
                return False
                
            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['username']
            msg['To'] = to
            msg['Subject'] = subject
            
            # Добавляем тело
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Добавляем вложения
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        msg.attach(part)
                        
            # Отправляем
            server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
            
            if self.smtp_config['use_tls']:
                server.starttls()
                
            server.login(self.smtp_config['username'], self.smtp_config['password'])
            text = msg.as_string()
            server.sendmail(self.smtp_config['username'], to, text)
            server.quit()
            
            print(f"[MailCalendar] Письмо отправлено: {to}")
            return True
            
        except Exception as e:
            print(f"[MailCalendar] Ошибка отправки письма: {e}")
            return False
            
    def create_calendar_event(self,
                             subject: str,
                             start_time: datetime,
                             end_time: datetime,
                             location: str = "",
                             body: str = "",
                             attendees: List[str] = None) -> bool:
        """Создание события в календаре"""
        try:
            if not self.outlook_config or not self.outlook_config['com_available']:
                print("[MailCalendar] Outlook COM недоступен")
                return False
                
            import win32com.client
            
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            calendar = namespace.GetDefaultFolder(9)
            
            # Создаем событие
            appointment = outlook.CreateItem(1)  # olAppointmentItem
            appointment.Subject = subject
            appointment.Start = start_time
            appointment.End = end_time
            appointment.Location = location
            appointment.Body = body
            
            # Добавляем участников
            if attendees:
                for attendee in attendees:
                    appointment.Recipients.Add(attendee)
                    
            # Сохраняем
            appointment.Save()
            
            print(f"[MailCalendar] Событие создано: {subject}")
            return True
            
        except Exception as e:
            print(f"[MailCalendar] Ошибка создания события: {e}")
            return False
            
    def create_ics_file(self,
                       subject: str,
                       start_time: datetime,
                       end_time: datetime,
                       location: str = "",
                       description: str = "",
                       attendees: List[str] = None) -> str:
        """Создание .ics файла"""
        try:
            cal = icalendar.Calendar()
            cal.add('prodid', '-//AI Assistant//Calendar Event//EN')
            cal.add('version', '2.0')
            
            event = icalendar.Event()
            event.add('summary', subject)
            event.add('dtstart', start_time)
            event.add('dtend', end_time)
            event.add('location', location)
            event.add('description', description)
            event.add('uid', f"{subject}_{start_time.isoformat()}@ai-assistant.local")
            
            if attendees:
                for attendee in attendees:
                    event.add('attendee', f"mailto:{attendee}")
                    
            cal.add_component(event)
            
            # Сохраняем файл
            ics_filename = f"event_{int(time.time())}.ics"
            ics_path = Path(ics_filename)
            
            with open(ics_path, 'wb') as f:
                f.write(cal.to_ical())
                
            print(f"[MailCalendar] .ics файл создан: {ics_path}")
            return str(ics_path)
            
        except Exception as e:
            print(f"[MailCalendar] Ошибка создания .ics: {e}")
            return ""
            
    def get_mail_history(self) -> List[Dict]:
        """Получить историю писем"""
        return self.mail_history.copy()
        
    def get_calendar_events(self) -> List[Dict]:
        """Получить события календаря"""
        return self.calendar_events.copy()
        
    def clear_history(self):
        """Очистить историю"""
        self.mail_history.clear()
        self.calendar_events.clear()
        
    def is_configured(self) -> bool:
        """Проверить, настроен ли модуль"""
        return (self.smtp_config is not None or 
                self.imap_config is not None or 
                (self.outlook_config and self.outlook_config['com_available']))
