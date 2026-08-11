# Redis Key Design — تاسي فيجن

الرموز الداخلية في المفاتيح: **الشكل العاري** `2222` (بدون `.SR`).

| المفتاح | النوع | TTL | الغرض |
|---------|-------|-----|-------|
| `quote:{bare}` | HASH/JSON | ~12s (جلسة) / 30s+ | آخر سعر — مصدره SAHMK أو failover |
| `indicators:{bare}:{tf}` | HASH | 60s | مؤشرات فنية |
| `reco:{bare}:{horizon}` | STRING JSON | 5m | تحليل Ensemble لأفق 5/10/20 |
| `portfolio:{id}:perf` | STRING JSON | 2m | أداء المحفظة (تسعير حسب الجلسة) |
| `market:overview` | STRING JSON | 15s | مؤشر تاسي + رابحين/خاسرين |
| `symbols:all` | STRING JSON | 1h | قائمة 350+ |
| `symbols:advanced` | STRING JSON | 24h | قائمة 120 المتقدمة |
| `rl:user:{user_id}` | عداد | 60s | Rate limit 100/min |
| `session:{jti}` | STRING | = JWT TTL | إبطال جلسات |
| `ws:channel:live` | Pub/Sub | — | بث الأسعار والتحليلات |
| `ml:champion:{model}` | STRING | 24h | إصدار النموذج البطل |

## سياسة التسعير المخزّنة في `quote:{bare}`

```json
{
  "price": 32.15,
  "change_pct": 1.2,
  "volume": 1250000,
  "ts": "2026-08-10T10:15:03+03:00",
  "source": "sahmk"
}
```

`source` ∈ `sahmk | lseg | tadawul | redis_cache`
