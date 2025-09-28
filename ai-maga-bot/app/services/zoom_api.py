"""
Zoom API клиент для Server-to-Server OAuth и управления встречами.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
import jwt
from app.settings import settings

logger = logging.getLogger(__name__)


class ZoomAPIClient:
    """Клиент для работы с Zoom API через Server-to-Server OAuth."""
    
    def __init__(self):
        self.account_id = settings.zoom_account_id
        self.client_id = settings.zoom_client_id
        self.client_secret = settings.zoom_client_secret
        self.default_user = settings.zoom_default_user
        self.base_url = "https://api.zoom.us/v2"
        self._access_token = None
        self._token_expires_at = None
        
    async def _get_access_token(self) -> str:
        """Получение access token через Server-to-Server OAuth."""
        if self._access_token and self._token_expires_at and datetime.now() < self._token_expires_at:
            return self._access_token
            
        if not all([self.account_id, self.client_id, self.client_secret]):
            raise ValueError("Zoom credentials not configured")
            
        # Создаем JWT для Server-to-Server OAuth
        now = datetime.utcnow()
        payload = {
            "iss": self.client_id,
            "exp": now + timedelta(hours=1),
            "aud": "zoom",
            "appKey": self.client_id,
            "tokenExp": int((now + timedelta(hours=1)).timestamp())
        }
        
        token = jwt.encode(payload, self.client_secret, algorithm="HS256")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                return self._access_token
            else:
                raise Exception(f"Failed to get access token: {response.status_code} {response.text}")
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Выполнение запроса к Zoom API с автоматическим обновлением токена."""
        token = await self._get_access_token()
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            
            if response.status_code == 401:
                # Токен истек, обновляем
                self._access_token = None
                self._token_expires_at = None
                token = await self._get_access_token()
                headers["Authorization"] = f"Bearer {token}"
                
                response = await client.request(method, url, **kwargs)
            
            if response.status_code >= 400:
                raise Exception(f"Zoom API error: {response.status_code} {response.text}")
                
            return response.json() if response.content else {}
    
    async def list_meetings(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Получение списка встреч пользователя."""
        user_id = user_id or self.default_user
        response = await self._make_request("GET", f"/users/{user_id}/meetings")
        return response.get("meetings", [])
    
    async def create_meeting(self, topic: str, start_time: str = None, duration: int = 60, 
                           user_id: str = None, **kwargs) -> Dict[str, Any]:
        """Создание новой встречи."""
        user_id = user_id or self.default_user
        
        meeting_data = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "duration": duration,
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": True,
                "waiting_room": True,
                **kwargs.get("settings", {})
            }
        }
        
        if start_time:
            meeting_data["start_time"] = start_time
            meeting_data["timezone"] = "UTC"
        
        response = await self._make_request(
            "POST", 
            f"/users/{user_id}/meetings",
            json=meeting_data
        )
        return response
    
    async def get_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """Получение информации о встрече."""
        return await self._make_request("GET", f"/meetings/{meeting_id}")
    
    async def update_meeting(self, meeting_id: str, **kwargs) -> Dict[str, Any]:
        """Обновление встречи."""
        return await self._make_request("PATCH", f"/meetings/{meeting_id}", json=kwargs)
    
    async def delete_meeting(self, meeting_id: str) -> bool:
        """Удаление встречи."""
        try:
            await self._make_request("DELETE", f"/meetings/{meeting_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete meeting {meeting_id}: {e}")
            return False
    
    async def get_meeting_participants(self, meeting_id: str) -> List[Dict[str, Any]]:
        """Получение участников встречи."""
        response = await self._make_request("GET", f"/meetings/{meeting_id}/participants")
        return response.get("participants", [])
    
    async def get_recording_files(self, meeting_id: str) -> List[Dict[str, Any]]:
        """Получение файлов записи встречи."""
        try:
            response = await self._make_request("GET", f"/meetings/{meeting_id}/recordings")
            return response.get("recording_files", [])
        except Exception as e:
            logger.warning(f"No recordings found for meeting {meeting_id}: {e}")
            return []
    
    async def get_transcript(self, meeting_id: str) -> Optional[str]:
        """Получение стенограммы встречи."""
        try:
            response = await self._make_request("GET", f"/meetings/{meeting_id}/transcript")
            return response.get("transcript", "")
        except Exception as e:
            logger.warning(f"No transcript found for meeting {meeting_id}: {e}")
            return None
    
    async def join_meeting(self, meeting_id: str, password: str = None) -> Dict[str, str]:
        """Получение ссылки для присоединения к встрече."""
        meeting = await self.get_meeting(meeting_id)
        join_url = meeting.get("join_url", "")
        
        if password and "?" in join_url:
            join_url += f"&pwd={password}"
        elif password:
            join_url += f"?pwd={password}"
            
        return {
            "join_url": join_url,
            "meeting_id": meeting_id,
            "password": password or meeting.get("password", "")
        }


# Глобальный экземпляр клиента
zoom_client = ZoomAPIClient()
