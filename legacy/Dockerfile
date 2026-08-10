# استخدام Python 3.11 slim كصورة أساسية
FROM python:3.11-slim

# تعيين متغيرات البيئة
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# تعيين مجلد العمل
WORKDIR /app

# تثبيت متطلبات النظام
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# إنشاء مستخدم غير root
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# نسخ ملف المتطلبات أولاً للاستفادة من Docker cache
COPY requirements.txt .

# تحديث pip وتثبيت المتطلبات
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# نسخ الكود المصدري
COPY . .

# إنشاء المجلدات المطلوبة
RUN mkdir -p logs data static && \
    chown -R appuser:appuser /app

# التبديل للمستخدم غير root
USER appuser

# تعريض المنفذ
EXPOSE 5002

# فحص الصحة
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5002/api/v1/health || exit 1

# الأمر الافتراضي لتشغيل التطبيق
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5002", "--workers", "1"]

