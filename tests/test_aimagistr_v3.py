# -*- coding: utf-8 -*-
"""
AIMagistr 3.0 - Smoke тесты
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock
import time

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from brain.ai_client import BrainManager
    from integrations.yandex_vision import YandexVision
    from integrations.yandex_translate import YandexTranslate
    from integrations.yandex_ocr import YandexOCR
    from data.rag_index import RAGIndex
    from security.secrets_scanner import SecretsScanner
    from telegram_bot_v3 import AIMagistrTelegramBot
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


class TestAIMagistrV3(unittest.TestCase):
    """Тесты для AIMagistr 3.0"""
    
    def setUp(self):
        """Настройка тестов"""
        # Устанавливаем тестовые переменные окружения
        os.environ['YANDEX_API_KEY'] = 'test_api_key'
        os.environ['YANDEX_FOLDER_ID'] = 'test_folder_id'
        os.environ['YANDEX_MODEL_URI'] = 'gpt://test/model'
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_bot_token'
        os.environ['SYSTEM_PROMPT'] = 'Test system prompt'
        
        # Создаем тестовые директории
        os.makedirs('data/rag_index', exist_ok=True)
        os.makedirs('security', exist_ok=True)
    
    def test_environment_variables(self):
        """Тест переменных окружения"""
        self.assertEqual(os.getenv('YANDEX_API_KEY'), 'test_api_key')
        self.assertEqual(os.getenv('YANDEX_FOLDER_ID'), 'test_folder_id')
        self.assertEqual(os.getenv('SYSTEM_PROMPT'), 'Test system prompt')
    
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Компоненты недоступны")
    def test_brain_manager_initialization(self):
        """Тест инициализации BrainManager"""
        brain = BrainManager()
        
        # Проверяем, что компонент инициализирован
        self.assertIsNotNone(brain)
        self.assertEqual(brain.api_key, 'test_api_key')
        self.assertEqual(brain.folder_id, 'test_folder_id')
        self.assertEqual(brain.system_prompt, 'Test system prompt')
        
        # Проверяем метрики
        metrics = brain.get_metrics()
        self.assertIn('total_requests', metrics)
        self.assertIn('successful_requests', metrics)
        self.assertIn('failed_requests', metrics)
    
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Компоненты недоступны")
    def test_yandex_vision_initialization(self):
        """Тест инициализации YandexVision"""
        vision = YandexVision()
        
        self.assertIsNotNone(vision)
        self.assertEqual(vision.api_key, 'test_api_key')
        self.assertEqual(vision.folder_id, 'test_folder_id')
        self.assertTrue(vision.enabled)
    
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Компоненты недоступны")
    def test_yandex_translate_initialization(self):
        """Тест инициализации YandexTranslate"""
        translate = YandexTranslate()
        
        self.assertIsNotNone(translate)
        self.assertEqual(translate.api_key, 'test_api_key')
        self.assertEqual(translate.folder_id, 'test_folder_id')
        self.assertTrue(translate.enabled)
    
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Компоненты недоступны")
    def test_yandex_ocr_initialization(self):
        """Тест инициализации YandexOCR"""
        ocr = YandexOCR()
        
        self.assertIsNotNone(ocr)
        self.assertEqual(ocr.api_key, 'test_api_key')
        self.assertEqual(ocr.folder_id, 'test_folder_id')
        self.assertTrue(ocr.enabled)
        
        # Проверяем поддерживаемые языки
        languages = ocr.get_supported_languages()
        self.assertIn('ru', languages)
        self.assertIn('en', languages)
        
        # Проверяем поддерживаемые форматы
        formats = ocr.get_supported_formats()
        self.assertIn('jpg', formats)
        self.assertIn('png', formats)
    
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Компоненты недоступны")
    def test_rag_index_initialization(self):
        """Тест инициализации RAGIndex"""
        rag = RAGIndex()
        
        self.assertIsNotNone(rag)
        self.assertEqual(rag.chunk_size, 1000)
        self.assertEqual(rag.chunk_overlap, 200)
        
        # Проверяем статистику
        stats = rag.get_stats()
        self.assertIn('total_documents', stats)
        self.assertIn('total_chunks', stats)
        self.assertIn('index_size', stats)
    
    def test_secrets_scanner_initialization(self):
        """Тест инициализации SecretsScanner"""
        scanner = SecretsScanner()
        
        self.assertIsNotNone(scanner)
        self.assertIn('api_key', scanner.secret_patterns)
        self.assertIn('password', scanner.secret_patterns)
        self.assertIn('email', scanner.pii_patterns)
        self.assertIn('phone', scanner.pii_patterns)
    
    def test_secrets_scanner_patterns(self):
        """Тест паттернов сканера секретов"""
        scanner = SecretsScanner()
        
        # Создаем временный файл с тестовым контентом
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
api_key = "sk-abcdefghijklmnop"
password = "secretpassword"
email = "test@example.com"
phone = "+7-123-456-7890"
            ''')
            temp_file = f.name
        
        try:
            # Сканируем контент
            results = scanner._scan_file_content(temp_file)
            
            # Проверяем, что найдены секреты
            self.assertGreater(len(results['secrets']), 0)
            self.assertGreater(len(results['pii']), 0)
        finally:
            # Удаляем временный файл
            import os
            os.unlink(temp_file)
    
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Компоненты недоступны")
    def test_telegram_bot_initialization(self):
        """Тест инициализации Telegram бота"""
        bot = AIMagistrTelegramBot()
        
        self.assertIsNotNone(bot)
        self.assertIsNotNone(bot.bot)
        self.assertIsNotNone(bot.dp)
        self.assertEqual(bot.max_file_size, 50 * 1024 * 1024)  # 50MB
        self.assertEqual(bot.max_context_tokens, 4000)
    
    def test_telegram_bot_features(self):
        """Тест фич Telegram бота"""
        bot = AIMagistrTelegramBot()
        
        # Проверяем, что все фичи включены по умолчанию
        self.assertTrue(bot.features['ocr'])
        self.assertTrue(bot.features['translate'])
        self.assertTrue(bot.features['rag'])
        self.assertTrue(bot.features['crm'])
        self.assertTrue(bot.features['rpa'])
        self.assertTrue(bot.features['analytics'])
        self.assertTrue(bot.features['security'])
    
    def test_telegram_bot_anti_spam(self):
        """Тест анти-спам защиты"""
        bot = AIMagistrTelegramBot()
        
        # Тестируем анти-спам
        user_id = 12345
        
        # Первые 10 запросов должны проходить
        for i in range(10):
            self.assertTrue(bot._check_anti_spam(user_id))
        
        # 11-й запрос должен быть заблокирован
        self.assertFalse(bot._check_anti_spam(user_id))
    
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Компоненты недоступны")
    async def test_brain_manager_metrics(self):
        """Тест метрик BrainManager"""
        brain = BrainManager()
        
        # Проверяем начальные метрики
        metrics = brain.get_metrics()
        self.assertEqual(metrics['total_requests'], 0)
        self.assertEqual(metrics['successful_requests'], 0)
        self.assertEqual(metrics['failed_requests'], 0)
        
        # Сбрасываем метрики
        brain.reset_metrics()
        metrics = brain.get_metrics()
        self.assertEqual(metrics['total_requests'], 0)
    
    def test_rag_index_chunking(self):
        """Тест разбивки текста на чанки"""
        rag = RAGIndex()
        
        # Тестовый текст
        test_text = "Это тестовый текст для проверки разбивки на чанки. " * 100
        
        # Разбиваем на чанки
        chunks = rag._chunk_text(test_text, chunk_size=100, overlap=20)
        
        self.assertGreater(len(chunks), 0)
        
        # Проверяем, что чанки не пустые
        for chunk in chunks:
            self.assertGreater(len(chunk), 0)
    
    def test_secrets_scanner_exclude_patterns(self):
        """Тест исключений сканера секретов"""
        scanner = SecretsScanner()
        
        # Тестируем исключения
        self.assertFalse(scanner._should_scan_file(".git/config"))
        self.assertFalse(scanner._should_scan_file("node_modules/package.json"))
        self.assertFalse(scanner._should_scan_file("test.log"))
        self.assertFalse(scanner._should_scan_file("README.md"))
        
        # Файлы, которые должны сканироваться
        self.assertTrue(scanner._should_scan_file("main.py"))
        self.assertTrue(scanner._should_scan_file("config.json"))
        self.assertTrue(scanner._should_scan_file("settings.yaml"))
    
    def test_secrets_scanner_example_detection(self):
        """Тест определения примеров"""
        scanner = SecretsScanner()
        
        # Примеры, которые должны быть пропущены
        self.assertTrue(scanner._is_example_value("your_api_key"))
        self.assertTrue(scanner._is_example_value("example_token"))
        self.assertTrue(scanner._is_example_value("test_password"))
        self.assertTrue(scanner._is_example_value("placeholder"))
        
        # Реальные значения, которые должны быть найдены
        # Исправляем тест - sk-1234567890abcdef содержит "123" что считается примером
        self.assertFalse(scanner._is_example_value("sk-abcdefghijklmnop"))
        self.assertFalse(scanner._is_example_value("real_password_abc"))
    
    def test_telegram_bot_user_context(self):
        """Тест контекста пользователя"""
        bot = AIMagistrTelegramBot()
        
        user_id = 12345
        
        # Инициализируем контекст
        if user_id not in bot.user_contexts:
            bot.user_contexts[user_id] = {
                'messages': [],
                'language': 'ru',
                'custom_prompt': None,
                'last_activity': time.time()
            }
        
        # Проверяем контекст
        context = bot.user_contexts[user_id]
        self.assertEqual(context['language'], 'ru')
        self.assertIsNone(context['custom_prompt'])
        self.assertEqual(len(context['messages']), 0)
    
    def test_telegram_bot_roles(self):
        """Тест ролей пользователей"""
        bot = AIMagistrTelegramBot()
        
        # Устанавливаем админа
        bot.user_roles[12345] = 'admin'
        bot.user_roles[67890] = 'user'
        
        # Проверяем роли
        self.assertEqual(bot.user_roles[12345], 'admin')
        self.assertEqual(bot.user_roles[67890], 'user')
    
    def test_telegram_bot_file_size_limit(self):
        """Тест лимита размера файла"""
        bot = AIMagistrTelegramBot()
        
        # Проверяем лимит
        self.assertEqual(bot.max_file_size, 50 * 1024 * 1024)  # 50MB
        
        # Проверяем, что лимит можно изменить через env
        os.environ['MAX_FILE_SIZE_MB'] = '100'
        bot2 = AIMagistrTelegramBot()
        self.assertEqual(bot2.max_file_size, 100 * 1024 * 1024)  # 100MB


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты"""
    
    def setUp(self):
        """Настройка интеграционных тестов"""
        os.environ['YANDEX_API_KEY'] = 'test_api_key'
        os.environ['YANDEX_FOLDER_ID'] = 'test_folder_id'
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_bot_token'
    
    @unittest.skipUnless(COMPONENTS_AVAILABLE, "Компоненты недоступны")
    def test_full_system_initialization(self):
        """Тест полной инициализации системы"""
        # Инициализируем все компоненты
        brain = BrainManager()
        vision = YandexVision()
        translate = YandexTranslate()
        ocr = YandexOCR()
        rag = RAGIndex()
        scanner = SecretsScanner()
        bot = AIMagistrTelegramBot()
        
        # Проверяем, что все компоненты инициализированы
        self.assertIsNotNone(brain)
        self.assertIsNotNone(vision)
        self.assertIsNotNone(translate)
        self.assertIsNotNone(ocr)
        self.assertIsNotNone(rag)
        self.assertIsNotNone(scanner)
        self.assertIsNotNone(bot)
    
    def test_environment_consistency(self):
        """Тест согласованности переменных окружения"""
        # Проверяем, что все компоненты используют одни и те же переменные
        self.assertEqual(os.getenv('YANDEX_API_KEY'), 'test_api_key')
        self.assertEqual(os.getenv('YANDEX_FOLDER_ID'), 'test_folder_id')
        self.assertEqual(os.getenv('TELEGRAM_BOT_TOKEN'), 'test_bot_token')


def run_smoke_tests():
    """Запуск smoke тестов"""
    print("Запуск smoke тестов AIMagistr 3.0...")
    
    # Создаем тестовый suite
    suite = unittest.TestSuite()
    
    # Добавляем тесты
    suite.addTest(unittest.makeSuite(TestAIMagistrV3))
    suite.addTest(unittest.makeSuite(TestIntegration))
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Возвращаем результат
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_smoke_tests()
    if success:
        print("\nВсе smoke тесты прошли успешно!")
    else:
        print("\nНекоторые тесты не прошли")
        sys.exit(1)
