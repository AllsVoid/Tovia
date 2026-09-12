# Tovia 所至 — 信息架构与 UX v0.1

## 1. 一级导航

```text
Map
Calendar
Trips
Inbox
Profile
```

---

## 2. Map

默认首页。

顶部：

```text
Tovia 所至
[国内] [海外]
```

地图：

- 极简轮廓
- 一级行政区
- travel points
- hover / click

状态建议：

- visited
- upcoming
- wishlist

下方摘要：

- Countries
- Cities
- Trips
- Days
- Photos

---

## 3. Calendar

月视图：

- Trip 日期：荧光笔带
- 照片：缩略图
- 多 Trip：最多显示 2 个视觉层
- 点击日期进入 Daily Memory

Daily Memory：

- 日期
- Trip
- Places
- Activities
- Photos
- Expenses
- Notes

---

## 4. Trips

分组：

- Upcoming
- Past
- Ideas

Card：

- cover
- title
- date
- duration
- places
- bookings
- budget / spend

---

## 5. Trip Detail

Tab：

```text
Overview
Map
Itinerary
Bookings
Expenses
Notes
Photos
```

---

## 6. Overview

展示：

- Trip title
- date
- status
- compact map
- next booking
- place count
- estimated budget
- upload / import shortcut

---

## 7. Itinerary

按 Day 分段。

Activity 可：

- drag
- reorder
- edit
- mark done
- candidate → planned

Candidate 与 Confirmed 必须视觉区分。

---

## 8. Inbox

卡片：

```text
[thumbnail]
Hotel booking
AI detected
Confidence 92%

[Review]
```

Review 页面：

- 左：原始图片 / PDF
- 右：结构化字段
- Confirm
- Edit
- Reject

---

## 9. Travel Mode

条件：

Trip.status == TRAVELING

展示优先级：

1. 当前日期
2. 下一项活动
3. Booking 快捷入口
4. 导航
5. Add Photo
6. Add Expense
7. Add Note

禁止在 Travel Mode 塞复杂编辑器。

---

## 10. Empty States

Map:

> 还没有点亮任何地方  
> 添加一次旅行，开始绘制你的所至。

Calendar:

> 这个月还没有旅行记录。

Inbox:

> 把机票、酒店、截图或 PDF 丢进来。

---

## 11. 视觉方向

关键词：

- 克制
- 极简
- 地图感
- 轻文艺
- 不做“OTA 蓝”
- 不做“旅游攻略黄”

地图应该是主视觉，不是普通地图底图。
