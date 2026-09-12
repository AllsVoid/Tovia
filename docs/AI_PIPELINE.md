# Tovia 所至 — AI / OCR Pipeline v0.1

## 1. 原则

AI 是辅助整理层，不是事实来源。

禁止：

- AI 直接修改已确认数据
- AI 无审查创建 Booking / Expense / Activity
- 丢弃原始文档

必须：

- 保留原始文件
- 保留 OCR 文本
- 保留 AI 原始 structured output
- 保留 confidence
- 用户确认后入正式表

---

## 2. 导入流程

```text
Upload
  ↓
Document created
  ↓
OCR
  ↓
Document classifier
  ↓
Structured extraction
  ↓
Trip matcher
  ↓
Place matcher
  ↓
Candidate
  ↓
User review
  ↓
Confirmed entity
```

---

## 3. 文档分类

候选类型：

- FLIGHT
- TRAIN
- BUS
- HOTEL
- TICKET
- RESTAURANT
- EXPENSE
- GUIDE
- UNKNOWN

---

## 4. Structured Output

必须使用 schema 校验。

例如：

```json
{
  "type": "flight",
  "flight_no": "MU727",
  "departure_airport": "PVG",
  "arrival_airport": "NRT",
  "departure_at": "2026-08-27T08:55:00+08:00",
  "arrival_at": "2026-08-27T12:50:00+09:00",
  "booking_reference": null,
  "price": {
    "amount": 1324,
    "currency": "CNY"
  }
}
```

---

## 5. Trip Matching

匹配因子：

- 时间重叠
- 地点重叠
- 航班 / 酒店目的地
- 用户当前 selected trip
- 文件上传批次

输出：

```text
trip_id
confidence
reason[]
```

低置信度必须让用户手工选择。

---

## 6. Photo Reconstruction

后续阶段：

```text
Photos
 ↓
EXIF timestamp
 ↓
GPS cluster
 ↓
POI reverse geocode
 ↓
time cluster
 ↓
candidate trip
 ↓
candidate visits
```

第一版只需：

- EXIF
- 时间
- GPS
- 手工确认

---

## 7. AI Planner

输入：

- Trip dates
- Bookings
- Hotel location
- Confirmed activities
- Candidate places
- user preferences

必须考虑：

- booking hard constraints
- opening hours（后续）
- distance
- travel time
- timezone
- date

AI 输出：

- Candidate Day Plan
- Candidate Activity
- explanation
- warnings

禁止直接写正式 itinerary。

---

## 8. Provider Interface

```python
class AIProvider:
    async def extract_document(...)
    async def propose_itinerary(...)
    async def summarize_trip(...)
```

```python
class OCRProvider:
    async def extract_text(...)
```

---

## 9. Prompt 管理

禁止 prompt 散落业务代码。

统一目录：

```text
workers/ai/prompts/
```

每个 Prompt：

- id
- version
- expected schema
- examples
- test fixtures

---

## 10. AI 测试

必须准备固定 fixtures：

- 机票截图
- 酒店订单
- 火车票
- 支付截图

验证：

- schema valid
- date parsing
- currency
- timezone
- missing fields
- hallucination rate
