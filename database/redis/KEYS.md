# Redis Key Design — منصة تاسي

نمط التخزين: **Cache-Aside** للقراءات + **Pub/Sub** للتحديثات اللحظية.

| المفتاح | النوع | TTL | الغرض |
|---------|-------|-----|-------|
| `quote:{symbol}` | HASH (`price`, `change_pct`, `volume`, `ts`) | 10s | آخر سعر لحظي من SAHMK |
| `indicators:{symbol}:{tf}` | HASH (rsi, macd, atr, ...) | 60s | مؤشرات فنية مخزّنة |
| `reco:{symbol}` | STRING (JSON) | 5m | آخر توصية Ensemble + SHAP |
| `portfolio:{id}:perf` | STRING (JSON) | 2m | أداء المحفظة المحسوب |
| `market:overview` | STRING (JSON) | 15s | مؤشر تاسي + رابحين/خاسرين |
| `symbols:all` | STRING (JSON array) | 1h | قائمة الرموز النشطة |
| `rl:user:{user_id}` | STRING (عداد) | 60s | Rate limit: 100 req/min |
| `session:{jti}` | STRING | = JWT TTL | جلسات MFA/JWT للإبطال |
| `ws:channel:live` | Pub/Sub channel | — | بث الأسعار والتوصيات |
| `ml:champion:{model}` | STRING (version) | 24h | إصدار النموذج البطل من MLflow |

## أمثلة أوامر

```bash
HSET quote:2222.SR price 32.15 change_pct 1.2 volume 1250000 ts 1723324800
EXPIRE quote:2222.SR 10

SET reco:2222.SR '{"action":"buy","confidence":0.74,...}' EX 300
PUBLISH ws:channel:live '{"type":"quote","symbol":"2222.SR","price":32.15}'

INCR rl:user:550e8400-e29b-41d4-a716-446655440000
EXPIRE rl:user:550e8400-e29b-41d4-a716-446655440000 60
```

## سياسات الفشل

- عند انقطاع Redis: القراءة تتم مباشرة من ClickHouse/PostgreSQL (graceful degradation).
- لا تُخزَّن كلمات المرور أو أسرار MFA كنص واضح في Redis.
