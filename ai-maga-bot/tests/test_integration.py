"""
Интеграционные тесты для новых компонентов AI-Maga Enterprise.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
import os
from pathlib import Path


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Тест инициализации оркестратора с новыми компонентами"""
    from app.orchestrator import AIMagaOrchestrator

    orchestrator = AIMagaOrchestrator()

    # Проверяем что компоненты инициализированы
    assert orchestrator.rag_manager is None
    assert orchestrator.memory_palace is None
    assert orchestrator.vision_client is None

    # Проверяем circuit breakers
    assert orchestrator.llm_circuit_breaker is not None
    assert orchestrator.vision_circuit_breaker is not None
    assert orchestrator.stt_circuit_breaker is not None

    # Проверяем состояние circuit breakers
    assert orchestrator.llm_circuit_breaker.state == 'closed'
    assert orchestrator.llm_circuit_breaker.failure_count == 0


@pytest.mark.asyncio
async def test_rag_memory_integration():
    """Тест интеграции RAG и Memory Palace"""
    from app.orchestrator import AIMagaOrchestrator

    orchestrator = AIMagaOrchestrator()

    # Мокаем RAG и Memory компоненты
    with patch('app.orchestrator.RAG_AVAILABLE', True), \
         patch('app.orchestrator.MEMORY_AVAILABLE', True), \
         patch('brain.rag_index.RAGManager') as mock_rag_class, \
         patch('memory_palace.MemoryPalace') as mock_memory_class:

        mock_rag = MagicMock()
        mock_rag.initialize.return_value = True
        mock_rag.search_context.return_value = "Тестовый контекст из RAG"
        mock_rag_class.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory_class.return_value = mock_memory

        # Инициализируем
        await orchestrator._init_rag_memory()

        # Проверяем что компоненты созданы
        assert orchestrator.rag_manager is not None
        assert orchestrator.memory_palace is not None

        # Тестируем поиск контекста
        context = orchestrator.rag_manager.search_context("test query")
        assert context == "Тестовый контекст из RAG"


@pytest.mark.asyncio
async def test_vision_integration():
    """Тест интеграции Vision API"""
    from app.orchestrator import AIMagaOrchestrator

    orchestrator = AIMagaOrchestrator()

    # Мокаем Vision компонент
    with patch('app.orchestrator.VISION_AVAILABLE', True), \
         patch('integrations.yandex_vision.YandexVision') as mock_vision_class, \
         patch('app.settings.settings') as mock_settings:

        mock_settings.vision_enabled = True
        mock_vision = MagicMock()
        mock_vision.extract_text.return_value = "Распознанный текст из изображения"
        mock_vision_class.return_value = mock_vision

        # Инициализируем
        await orchestrator._init_rag_memory()

        # Проверяем что Vision создан
        assert orchestrator.vision_client is not None

        # Тестируем обработку изображения
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = await orchestrator.process_image(123, temp_path, "Тестовое изображение")

            assert result['type'] == 'text'
            assert 'Распознанный текст' in result['text']
            assert result['service'] == 'vision'

        finally:
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_circuit_breaker_functionality():
    """Тест работы circuit breaker"""
    from app.orchestrator import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

    # Тест успешного вызова
    def successful_func():
        return "success"

    result = cb.call(successful_func)
    assert result == "success"
    assert cb.state == 'closed'
    assert cb.failure_count == 0

    # Тест неудачных вызовов
    def failing_func():
        raise Exception("Test error")

    # Первый failure
    with pytest.raises(Exception):
        cb.call(failing_func)
    assert cb.failure_count == 1
    assert cb.state == 'closed'

    # Второй failure - circuit breaker должен открыться
    with pytest.raises(Exception):
        cb.call(failing_func)
    assert cb.failure_count == 2
    assert cb.state == 'open'

    # Попытка вызова когда circuit breaker открыт
    with pytest.raises(Exception, match="Circuit breaker is OPEN"):
        cb.call(successful_func)


@pytest.mark.asyncio
async def test_graceful_degradation():
    """Тест graceful degradation при недоступности компонентов"""
    from app.orchestrator import AIMagaOrchestrator

    orchestrator = AIMagaOrchestrator()

    # Мокаем недоступные компоненты
    with patch('app.orchestrator.RAG_AVAILABLE', False), \
         patch('app.orchestrator.MEMORY_AVAILABLE', False), \
         patch('app.orchestrator.VISION_AVAILABLE', False):

        # Инициализируем
        await orchestrator._init_rag_memory()

        # Проверяем что компоненты не созданы
        assert orchestrator.rag_manager is None
        assert orchestrator.memory_palace is None
        assert orchestrator.vision_client is None

        # Тестируем обработку сообщения - должно работать без RAG/Memory
        with patch('app.orchestrator.complete_text') as mock_llm:
            mock_llm.return_value = "Тестовый ответ ИИ"

            result = await orchestrator.process_message(123, "Тестовое сообщение", "text")

            assert result['type'] == 'text'
            assert 'Тестовый ответ ИИ' in result['text']


@pytest.mark.asyncio
async def test_health_checks():
    """Тест health check функциональности"""
    from app.orchestrator import AIMagaOrchestrator

    orchestrator = AIMagaOrchestrator()

    # Тестируем health check без инициализации
    health = await orchestrator.get_health_status()

    assert 'overall_status' in health
    assert 'components' in health
    assert 'circuit_breakers' in health
    assert 'timestamp' in health

    # Проверяем circuit breakers в health
    assert 'llm_circuit_breaker' in health['circuit_breakers']
    assert 'vision_circuit_breaker' in health['circuit_breakers']
    assert 'stt_circuit_breaker' in health['circuit_breakers']


@pytest.mark.asyncio
async def test_system_metrics():
    """Тест получения системных метрик"""
    from app.orchestrator import AIMagaOrchestrator

    orchestrator = AIMagaOrchestrator()

    metrics = orchestrator.get_system_metrics()

    assert 'timestamp' in metrics
    assert 'process' in metrics
    assert 'system' in metrics
    assert 'orchestrator' in metrics

    # Проверяем структуру метрик процесса
    process_metrics = metrics['process']
    assert 'pid' in process_metrics
    assert 'cpu_percent' in process_metrics
    assert 'memory_mb' in process_metrics
    assert 'threads' in process_metrics


@pytest.mark.asyncio
async def test_decision_profiles():
    """Тест профилей решений"""
    from app.orchestrator import AIMagaOrchestrator
    from app.settings import Settings

    orchestrator = AIMagaOrchestrator()

    # Тестируем разные профили
    test_cases = [
        ('conservative', 'Будь осторожен'),
        ('balanced', 'Отвечай кратко'),
        ('active', 'Будь инициативен')
    ]

    for profile, expected_text in test_cases:
        with patch('app.orchestrator.complete_text') as mock_llm:
            mock_llm.return_value = "Тестовый ответ"

            # Устанавливаем профиль через настройки
            with patch('app.orchestrator.settings') as mock_settings:
                mock_settings.ai_decision_profile = profile

                result = await orchestrator.process_message(123, "Тест", "text")

                # Проверяем что LLM был вызван
                mock_llm.assert_called_once()
                call_args = mock_llm.call_args[1]['system_prompt']

                # Проверяем что профиль учтен в промпте
                assert expected_text in call_args


@pytest.mark.asyncio
async def test_security_integration():
    """Тест интеграции с security_enhancement"""
    from app.orchestrator import AIMagaOrchestrator

    orchestrator = AIMagaOrchestrator()

    # Тестируем обработку сообщения с безопасностью
    with patch('app.services.security_enhancement.security_enhancement.validate_command_safety') as mock_security:
        mock_security.return_value = {'safe': True, 'warnings': []}

        # Это тест для OS команд, но проверяем что безопасность вызывается
        from app.services.os_controller import OSController
        os_controller = OSController()

        # Мокаем subprocess
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'output', b'')
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await os_controller.execute_command("echo test", 123)

            # Проверяем что безопасность была проверена
            mock_security.assert_called_once_with("echo test", 123)
            assert result['success'] is True
            assert result['output'] == 'output'


if __name__ == "__main__":
    pytest.main([__file__])
