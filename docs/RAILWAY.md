# نشر تاسي فيجن على Railway.com

الهدف: مشروع Railway واحد بخدمات **Postgres + Redis + api + web**.

## الإنتاج الحالي

- **API:** https://dede-production-c796.up.railway.app/
- المستودع: `relax201/dede` · الفرع `main`
- بعد كل Push على `main` يعيد Railway البناء تلقائياً (إن كان مفعّلاً).

### تحقق سريع

```bash
curl -s https://dede-production-c796.up.railway.app/api/health
curl -s https://dede-production-c796.up.railway.app/api/health/detail
curl -s https://dede-production-c796.up.railway.app/api/stream/status
```

إذا ظهر `"postgres": false` أو `"redis": false` في `/api/health/detail`، اربط المتغيرات:

- `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
- `REDIS_URL` = `${{Redis.REDIS_URL}}` أو `${{Redis.REDIS_PRIVATE_URL}}`

## الطريقة أ — من لوحة Railway (موصى بها)

1. افتح [railway.app/new](https://railway.app/new) → **Deploy from GitHub repo**  
   اختر **`relax201/dede`** والفرع `main` (مستودع النشر المرتبط).
2. أضف قواعد البيانات:
   - **New → Database → PostgreSQL**
   - **New → Database → Redis**
3. أنشئ خدمة **api** من نفس المستودع:
   - Settings → **Dockerfile path** = `Dockerfile.railway.api`
   - Root Directory = `/` (جذر المستودع)
4. أنشئ خدمة **web** من نفس المستودع:
   - Dockerfile path = `Dockerfile.railway.web`
5. على **api** و **web**: Settings → Networking → **Generate Domain**
6. اضبط متغيرات **api** (Variables):

| المتغير | القيمة |
|---------|--------|
| `SECRET_KEY` | سلسلة عشوائية ≥ 32 حرفاً |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `SAHMK_API_KEY` | مفتاح سهمك `shmk_live_...` |
| `SAHMK_BASE_URL` | `https://api.sahmk.sa/api/v1` |
| `SAHMK_WS_URL` | `wss://api.sahmk.sa/ws/v1/stocks/` |
| `SAHMK_WS_ENABLED` | `true` |
| `SAHMK_WS_AUTO_UNIVERSE` | `true` |
| `SAHMK_WS_MAX_SYMBOLS` | `60` |
| `ALLOWED_ORIGINS` | `https://<web-domain>` |
| `RAILWAY_STATIC_URL` | `https://<web-domain>` |
| `DEBUG` | `false` |
| `ENVIRONMENT` | `production` |
| `API_V1_STR` | `/api` |
| `TIMEZONE` | `Asia/Riyadh` |

7. اضبط متغيرات **web** (Build / Variables — كـ Docker build args إن لزم):

| المتغير | القيمة |
|---------|--------|
| `VITE_API_URL` | `https://dede-production-c796.up.railway.app` |
| `VITE_WS_URL` | `wss://dede-production-c796.up.railway.app` |

8. أعد Deploy للواجهة بعد تثبيت الدومينات و`VITE_*`.

## الطريقة ب — عبر CLI (يحتاج توكن)

1. من Railway Dashboard → Account → **Tokens** أنشئ توكن.  
2. في بيئة الوكيل أو الطرفية:

```bash
export RAILWAY_TOKEN=...
railway whoami
```

بدون `RAILWAY_TOKEN` لا يمكن للوكيل إكمال النشر تلقائياً.

## ملاحظات

- Railway يحقن `PORT` تلقائياً — الـ Dockerfiles جاهزة لذلك.
- WebSocket على نفس نطاق الـ api عبر `wss://`.
- عند الإقلاع يُنشئ الـ API جداول Postgres تلقائياً إن لم تكن موجودة.
- لا ترفع `.env` إلى Git؛ الأسرار في Railway Variables فقط.
- أسماء خدمات Postgres/Redis في `${{...}}` قد تختلف قليلاً حسب تسمية الخدمة في المشروع — اختر المرجع من قائمة Variables في الواجهة.
