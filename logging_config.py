"""
إعدادات التسجيل المتقدمة
Advanced Logging Configuration
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    """مُنسق JSON للسجلات"""
    
    def format(self, record: logging.LogRecord) -> str:
        """تنسيق السجل كـ JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # إضافة معلومات إضافية إذا كانت متوفرة
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'client_ip'):
            log_data['client_ip'] = record.client_ip
        
        # إضافة معلومات الاستثناء إذا كانت موجودة
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)

class ColoredFormatter(logging.Formatter):
    """مُنسق ملون للسجلات في وحدة التحكم"""
    
    # ألوان ANSI
    COLORS = {
        'DEBUG': '\033[36m',      # سماوي
        'INFO': '\033[32m',       # أخضر
        'WARNING': '\033[33m',    # أصفر
        'ERROR': '\033[31m',      # أحمر
        'CRITICAL': '\033[35m',   # بنفسجي
        'RESET': '\033[0m'        # إعادة تعيين
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """تنسيق السجل مع الألوان"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # تنسيق الرسالة
        formatted = super().format(record)
        return f"{color}{formatted}{reset}"

def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    app_name: str = "tasi_platform",
    enable_json: bool = True,
    enable_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """إعداد نظام التسجيل المتقدم"""
    
    # إنشاء مجلد السجلات
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # إعداد المستوى
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # إعداد الـ root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # إزالة المعالجات الموجودة
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # معالج وحدة التحكم
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # استخدام المُنسق الملون للوحة التحكم
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # معالج الملف العام
    general_log_file = log_path / f"{app_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        general_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)
    
    if enable_json:
        file_formatter = JSONFormatter()
    else:
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # معالج الأخطاء المنفصل
    error_log_file = log_path / f"{app_name}_errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # معالج الطلبات المنفصل
    requests_log_file = log_path / f"{app_name}_requests.log"
    requests_handler = logging.handlers.RotatingFileHandler(
        requests_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    requests_handler.setLevel(logging.INFO)
    requests_handler.setFormatter(file_formatter)
    
    # إعداد logger منفصل للطلبات
    requests_logger = logging.getLogger("requests")
    requests_logger.addHandler(requests_handler)
    requests_logger.setLevel(logging.INFO)
    requests_logger.propagate = False
    
    # إعداد loggers للمكتبات الخارجية
    external_loggers = [
        "uvicorn.access",
        "uvicorn.error", 
        "fastapi",
        "sqlalchemy.engine",
        "aiohttp.access"
    ]
    
    for logger_name in external_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)  # تقليل مستوى التسجيل للمكتبات الخارجية
    
    # تسجيل بداية التشغيل
    logger = logging.getLogger(__name__)
    logger.info(f"تم إعداد نظام التسجيل - المستوى: {log_level}")
    logger.info(f"مجلد السجلات: {log_path.absolute()}")

class RequestLogger:
    """فئة لتسجيل الطلبات مع معلومات إضافية"""
    
    def __init__(self, logger_name: str = "requests"):
        self.logger = logging.getLogger(logger_name)
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        process_time: float,
        client_ip: str = None,
        user_id: str = None,
        request_id: str = None,
        **kwargs
    ) -> None:
        """تسجيل طلب HTTP"""
        
        # إنشاء سجل مع معلومات إضافية
        extra = {
            'client_ip': client_ip,
            'user_id': user_id,
            'request_id': request_id
        }
        
        message = f"{method} {path} - {status_code} - {process_time:.3f}s"
        
        # إضافة معلومات إضافية
        if kwargs:
            details = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            message += f" - {details}"
        
        # اختيار مستوى التسجيل حسب حالة الاستجابة
        if status_code >= 500:
            self.logger.error(message, extra=extra)
        elif status_code >= 400:
            self.logger.warning(message, extra=extra)
        else:
            self.logger.info(message, extra=extra)
    
    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        request_id: str = None
    ) -> None:
        """تسجيل خطأ مع السياق"""
        
        extra = {'request_id': request_id}
        
        message = f"خطأ في التطبيق: {str(error)}"
        if context:
            message += f" - السياق: {context}"
        
        self.logger.error(message, exc_info=True, extra=extra)

# إنشاء مثيل عام لتسجيل الطلبات
request_logger = RequestLogger()

def get_logger(name: str) -> logging.Logger:
    """الحصول على logger مُعد مسبقاً"""
    return logging.getLogger(name)

