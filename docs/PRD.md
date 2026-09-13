# Tovia 所至 — PRD v0.1

## 当前实现：Phase 2

首页地图、国内/海外/全部筛选、曾至/将至/未至、旅行月历与当天详情已连接真实数据库。旅行详情提供日期/状态编辑、地点与访问、Day 和 Activity 录入；未至采用独立愿望清单。曾至与将至依抵达时间计算，可以在同一地点共存。

本阶段使用内置轮廓底图；地点检索只查询已有 Place，支持手工或地图点选坐标录入。街道地图、在线地点供应商、媒体、Booking / Expense 与 AI 按 Roadmap 后续交付。具体时区与计数语义见 DATA_MODEL 的 Phase 2 约定。

## 1. 产品定位

Tovia 是一个个人旅行数据库与旅行生命周期管理产品。

它同时服务两类核心需求：

1. **记录过去**
   - 去过哪里
   - 什么时候去
   - 看过什么
   - 花了多少钱
   - 拍了哪些照片
   - 当时有哪些故事与资料

2. **规划未来**
   - 想去哪里
   - 如何安排行程
   - 机票、住宿、车票、门票如何组织
   - 如何利用 AI 从杂乱资料中生成结构化行程

核心产品语言：

- **曾至**：已去过
- **将至**：已经规划 / 即将出发
- **未至**：愿望清单 / 想去

---

## 2. 核心价值主张

### 2.1 地图不是导航地图，而是“我的世界”

首页优先展示极简地图：

- 国内 / 海外 Banner 切换
- 仅保留行政区轮廓
- 不展示道路、商店、普通 POI
- 去过 / 将去 / 收藏的地点使用不同视觉状态
- 点大小可根据访问次数变化
- 点击国家、省份、城市可继续钻取

### 2.2 日历不是日程表，而是“我的旅行时间线”

按月查看：

- 有旅行数据的日期使用荧光笔风格标注
- 有照片的日期显示缩略图
- 连续旅行日期可形成跨日带状标记
- 点击日期进入 Daily Memory

### 2.3 AI 不是聊天机器人，而是“旅行数据整理助手”

用户可以上传：

- 机票截图
- 火车票 / 高铁票
- 酒店订单
- 门票
- PDF
- 旅行攻略截图
- 小票
- 支付截图
- 照片

系统执行：

OCR → 分类 → 结构化提取 → 旅行匹配 → 生成 Candidate → 用户确认 → 入库

AI 还可辅助：

- 生成结构化行程
- 推荐候选地点
- 检查时间冲突
- 基于已订交通和住宿做现实约束
- 旅行结束后生成 recap

---

## 3. 用户画像

### 3.1 主要用户

- 有持续旅行习惯
- 喜欢记录照片、消费、路线
- 使用截图、支付工具、地图收藏等多个系统
- 对长期数据积累有价值感
- 愿意整理过去旅行，也希望规划未来旅行

### 3.2 次要用户

- 想快速生成行程但不希望手工录入大量预订信息
- 希望把旅行资料集中管理
- 喜欢年度旅行报告、个人地图、旅行档案

---

## 4. 核心用户流程

### 4.1 新建未来旅行

1. 用户创建 Trip 或上传一批资料
2. AI 识别出航班、住宿、车票、景点
3. 系统建议创建 Trip
4. 用户确认
5. 自动生成日期范围与基础 Timeline
6. AI 根据现实约束生成建议行程
7. 用户调整、拖拽、确认
8. 出发后进入 Travel Mode
9. 旅行结束后生成 Memory

### 4.2 补录历史旅行

1. 用户选择一批旧照片
2. 系统读取 EXIF 时间 / GPS
3. 按时间与地理聚类
4. 推断可能属于同一次旅行
5. 用户确认 Trip
6. 自动形成日期、地点与照片时间线
7. 用户补充文字、费用和故事

### 4.3 首页探索

1. 打开首页
2. 查看“国内 / 海外”极简地图
3. 点击某个访问点
4. 查看该地区访问次数、旅行、照片、消费
5. 继续进入具体 Trip 或日期

---

## 5. 一级导航

Web MVP 建议：

- `Map`
- `Calendar`
- `Trips`
- `Inbox`
- `Profile`

移动端后续保持相同信息架构。

---

## 6. 功能模块

### 6.1 My World 地图

必须：

- 国内 / 海外切换
- 一级行政区轮廓
- 地点点位
- 状态：
  - visited
  - upcoming
  - wishlist
- 点击地点进入详情
- 显示访问次数

后续：

- 路线
- 按年份过滤
- 国家 / 城市统计
- Heatmap

### 6.2 Calendar

必须：

- 月视图
- Trip 日期高亮
- 连续日期可成条带
- 有照片时显示缩略图
- 点击进入 Day Detail

后续：

- Year view
- Travel density
- 自动精选封面

### 6.3 Trips

状态：

- IDEA
- PLANNING
- BOOKED
- TRAVELING
- COMPLETED
- ARCHIVED

详情 Tab：

- Overview
- Map
- Itinerary
- Bookings
- Expenses
- Notes
- Photos

### 6.4 Inbox

支持：

- 图片
- PDF
- 文本
- URL

每个上传项具备：

- 原始文件
- 解析状态
- Candidate
- Confirm / Edit / Reject

### 6.5 Booking Hub

类型：

- Flight
- Train
- Bus
- Hotel
- Ticket
- Restaurant
- Other

每个 Booking 必须保留：

- 原始文件
- 结构化字段
- 来源
- 置信度
- 手工修改记录

### 6.6 Expenses

字段：

- 原币金额
- 原币币种
- 实际结算金额
- 结算币种
- 实际汇率
- 类别
- 支付方式
- 日期
- 地点
- Trip
- 凭证

### 6.7 Photos

必须：

- 上传
- EXIF
- 拍摄时间
- GPS
- Trip 关联
- Day 关联
- Place 关联
- SHA256
- perceptual hash

### 6.8 Travel Mode

旅行进行中时简化 UI：

- Today
- Next activity
- Navigate
- Add photo
- Add expense
- Add note
- Check-in

### 6.9 Memory

Trip 完成后：

- Route
- Timeline
- Photos
- Expenses
- Highlights
- Notes

后续导出：

- PDF
- Markdown
- Static HTML
- Long image

### 6.10 Stats

后续：

- Countries
- Cities
- Trips
- Days away
- Distance
- Photos
- Total spend
- Spend by category
- Spend by city
- Year in Travel

---

## 7. 非目标

MVP 不做：

- 社交 Feed
- 公共社区
- 酒店 / 机票比价
- OTA 下单
- 实时聊天
- 多人复杂协作
- 自动后台 GPS 连续追踪
- 完整小程序 / Native App
- 大规模推荐算法

---

## 8. MVP 成功标准

MVP 能完整完成以下闭环：

1. 创建一个 Trip
2. 在地图上显示去过 / 将去地点
3. 在日历中看到 Trip 日期
4. 上传机票或酒店截图
5. AI/OCR 生成可确认 Candidate
6. 确认后生成 Booking
7. 添加照片并关联日期 / 地点
8. 添加费用
9. 查看 Trip Timeline
10. Trip 完成后查看 Memory 汇总

---

## 9. 体验原则

- 默认少信息，按需展开
- Travel Mode 只显示“此刻最有用的信息”
- AI 输出必须可解释、可修改
- 原始数据不可丢
- 地图和日历是第一公民
- 不让用户为了录入数据而理解复杂类型
- Inbox 是低门槛入口
