# Device & Platform Integration Research — TrailPilot MCP Server

> **Date:** 2026-03-19
> **Purpose:** Evaluate fitness watches, cycling computers, and fitness platforms for integration with our MTB MCP server
> **User context:** The user owns a Huawei watch. Strava integration is already planned.

---

## Table of Contents

1. [Fitness Watches & Wearables](#1-fitness-watches--wearables)
2. [Cycling Computers](#2-cycling-computers)
3. [Fitness Platforms & Apps](#3-fitness-platforms--apps)
4. [Priority Ranking](#4-priority-ranking-for-mtb-mcp-server)
5. [Recommended Integration Strategy](#5-recommended-integration-strategy)
6. [Sources](#sources)

---

## 1. Fitness Watches & Wearables

### 1.1 Huawei (GT series, Band series) — USER'S DEVICE

**API Availability:**
- **Huawei Health Kit REST API** — Official cloud REST API available at `health-api.cloud.huawei.com`
- **Auth:** OAuth 2.0 via HMS Core. Requires registration on HUAWEI Developers Console and scope approval.
- **On-device SDK:** Also available for Android/HarmonyOS (JavaScript), but REST API is what we need for server-side MCP integration.

**Data Available via REST API:**
- Heart rate (continuous, exercise)
- GPS tracks and activity records (cycling supported as a sport type)
- Sleep data (stages, duration)
- Steps, calories, distance
- HRV (heart rate variability) — available on newer GT models
- Stress levels
- SpO2 (blood oxygen)
- Activity records: Walk, Run, Cycle, Swim, and more

**Rate Limits & Pricing:**
- Free for developers after approval
- Specific rate limits not publicly documented; likely generous for individual use
- Historical data limited to 1 year before authorization date
- Weekly/monthly/yearly aggregation available

**MTB-Specific Value:**
- Cycling activity type supported (road cycling, mountain biking)
- Heart rate zones during rides
- GPS track recording
- No power meter support (watch-only, no ANT+ power)
- No MTB-specific metrics (grit, flow, jump count) — these are Garmin-exclusive features

**Integration Complexity:** Medium
- Requires HMS developer account and app approval
- OAuth 2.0 flow needed
- REST API is well-documented
- Scope approval process may take time

**Priority: HIGH** — This is the user's device.

---

### 1.2 Garmin (Forerunner, Fenix, Enduro, Instinct, Venu)

**API Availability:**
- **Garmin Connect Developer Program** — Official REST API suite
- **APIs:** Health API, Activity API, Training API, Courses API
- **Auth:** OAuth 1.0a consumer key model
- Free for approved **business** developers (no personal use)

**Data Available:**
- Heart rate (resting, active, continuous)
- HRV status (overnight collection)
- GPS tracks with 5 Hz recording on MTB profiles
- Sleep (score, stages, Body Battery recharge)
- Body Battery, Stress (1-100 scale, 3-min averages)
- Training Load, Training Status, VO2 Max
- Recovery Time estimates
- Respiration rate, Pulse Ox
- Activity details for 30+ sport types including MTB
- **MTB-specific:** Grit (trail difficulty score), Flow (riding smoothness), Jump Count/Distance

**Rate Limits:**
- Evaluation: 100 requests/min per partner, 200 requests/day per user
- Production: 6,000 requests/min per partner, 6,000 requests/day per user

**Pricing:** Free (no licensing fees), but business approval required. Some metrics may require license fee or minimum device orders for commercial use.

**MTB-Specific Value: EXCELLENT**
- Purpose-built MTB profiles on Edge and watch devices
- Grit/Flow scores are unique to Garmin
- Mountain Bike Dynamics (on Edge devices)
- Trailforks integration built into device
- Jump detection and metrics
- Connect IQ SDK allows custom MTB data fields

**Integration Complexity:** Medium-High
- Business developer approval required (2 business days)
- OAuth 1.0a (slightly older pattern)
- Excellent documentation and developer tools
- Sample data and backfill capabilities in eval environment

**Priority: HIGH** — Best MTB data ecosystem, dominant among serious cyclists.

---

### 1.3 Apple Watch (Series, Ultra)

**API Availability:**
- **NO server-side REST API** — Apple HealthKit is on-device only
- Data lives on user's iPhone/Watch, never uploaded to Apple cloud
- Server access requires a mobile intermediary app (reads HealthKit, pushes to your server)
- Third-party aggregators (Terra, Thryve) can bridge this gap

**Data Available (via intermediary):**
- Heart rate, HRV
- GPS tracks (via Workout app)
- Sleep stages
- VO2 Max estimates
- Activity rings (Move, Exercise, Stand)
- Cycling metrics: speed, cadence, power (with paired sensor)

**Rate Limits:** N/A (no cloud API)

**Pricing:** Free (HealthKit SDK), but requires iOS app development

**MTB-Specific Value:** Low-Medium
- Basic cycling workout recording
- No MTB-specific metrics
- Fragile glass not ideal for MTB crashes
- Apple Watch Ultra more suitable for outdoor sports

**Integration Complexity:** Very High
- Requires native iOS app or third-party bridge
- No direct server-to-Apple path
- Would need to use Terra API (~$0.10/user/month) or similar

**Priority: LOW** — No server API makes direct MCP integration impractical.

---

### 1.4 Samsung Galaxy Watch (Watch series, Classic)

**API Availability:**
- **Samsung Health SDK for Android** — Deprecated as of July 2025
- **Samsung Health Data SDK** — Replacement, requires partner approval
- **Health Connect (Android)** — Google's unified health platform, Samsung contributing
- **NO cloud REST API** for server-side access

**Data Available:**
- Heart rate, sleep, steps, stress
- Exercise records (cycling supported)
- SpO2, body composition
- Data accessible only on-device (Android SDK)

**Rate Limits:** N/A (on-device SDK)

**Pricing:** Free (SDK), partner approval required

**MTB-Specific Value:** Low
- Basic cycling recording
- No MTB-specific features
- On-device only, same limitation as Apple

**Integration Complexity:** Very High
- Requires Android app as bridge
- SDK migration in progress (deprecated -> new SDK)
- No server-side API path

**Priority: VERY LOW** — No server API, SDK in transition, minimal MTB value.

---

### 1.5 Polar (Vantage, Grit X, Pacer, Ignite)

**API Availability:**
- **Polar AccessLink API** — Official REST API, free and open
- **Auth:** OAuth 2.0
- Register at `admin.polaraccesslink.com` with Polar Flow account

**Data Available:**
- Heart rate (continuous, 5-min intervals)
- GPS tracks
- Sleep (duration, stages)
- Training Load Pro (available for supported wrist units)
- Activity samples
- Exercise data in multiple formats

**Rate Limits:**
- Activity samples: last 28 days only
- Date range queries: max 28 days, from date max 365 days old
- Only exercises uploaded to Flow after user registration with your client are available

**Pricing:** Free

**MTB-Specific Value:** Medium
- Grit X Pro designed for outdoor sports
- Training Load Pro for recovery management
- Hill Splitter feature (auto-detects climbs/descents)
- No MTB-specific metrics like Garmin's Grit/Flow

**Integration Complexity:** Low-Medium
- Open API, free registration
- Good Python examples available (`polar-accesslink` package on PyPI)
- OAuth 2.0 standard flow
- 28-day data window is a limitation

**Priority: MEDIUM** — Good open API, decent data, but limited MTB specifics.

---

### 1.6 Suunto (Vertical, Race, Peak)

**API Availability:**
- **Suunto Cloud API** via Azure API Management (`apizone.suunto.com`)
- **Auth:** Formal application and contract required
- Not available for personal use — organizations only

**Data Available:**
- Workout data in FIT format
- GPS tracks
- Heart rate, R-R intervals, power
- Altitude, temperature
- Duration, distance, calories
- Sleep data NOT yet available via Cloud API

**Rate Limits:** Not publicly documented

**Pricing:** Requires business contract with Suunto

**MTB-Specific Value:** Medium
- Good outdoor sports focus
- Trail-oriented watches (Vertical, Peak)
- FusedTrack GPS for challenging terrain
- No MTB-specific computed metrics

**Integration Complexity:** High
- Formal business application required
- Contract signing needed for production access
- API hosted on Azure API Management

**Priority: LOW** — Business-only access, high barrier, limited unique data.

---

### 1.7 COROS (APEX, VERTIX, PACE, DURA)

**API Availability:**
- **Private API** — Documentation shared only after application approval
- Apply at COROS Help Center
- No public REST API documentation

**Data Available (via approved API):**
- Activity data (FIT, TCX export)
- Daily metrics, sleep, heart rate
- GPS tracks
- Training load, fitness/fatigue
- Cycling-specific modes (road, MTB, gravel, e-bike)

**Rate Limits:** Not publicly documented

**Pricing:** Free (after approval)

**MTB-Specific Value:** Medium-High
- Dedicated mountain biking and e-MTB activity modes
- COROS DURA cycling computer entering market
- Fastest growing watch brand (Strava 2025 Year in Sport)
- APEX 4 marketed as "mountain sports watch"

**Integration Complexity:** Medium-High
- Private API, must apply and wait for approval
- Documentation not publicly available
- Unofficial `coros-api` Python package exists but uses undocumented endpoints
- Third-party aggregators (Terra, Spike) offer COROS integration

**Priority: LOW-MEDIUM** — Growing brand, but private API and less cycling-specific data than Garmin.

---

### 1.8 Wahoo RIVAL

**API Availability:**
- **Wahoo Cloud API** — OAuth 2.0 based REST API
- Available at `cloud-api.wahooligan.com`
- Access is request-based (email `partnerships@wahoofitness.com`)

**Data Available:**
- Workout data (upload/download)
- Heart rate, speed, cadence, power
- Calories, training load

**Rate Limits:**
- Starting January 2026: max 10 unrevoked access tokens per user per app

**Pricing:** Free (after approval)

**MTB-Specific Value:** Low
- RIVAL is a multisport watch, not MTB-focused
- Wahoo's strength is cycling computers (ELEMNT series), not watches
- RIVAL had limited market traction

**Integration Complexity:** Medium
- OAuth 2.0 standard
- API documentation available
- Limited to approved partners

**Priority: VERY LOW** — Limited watch product, Wahoo's value is in ELEMNT computers (see Section 2).

---

## 2. Cycling Computers

### 2.1 Garmin Edge (540, 840, 1040, Explore 2)

**API/Connectivity:**
- **Garmin Connect Developer Program** — Same API suite as watches
- **Courses API** — Push GPX/FIT routes to device via Garmin Connect (auto-sync)
- **Training API** — Push structured workouts to device
- **Activity API** — Pull ride data after sync
- **Connect IQ SDK** — Build custom data fields and apps for the device

**Route Push Capability: YES**
- Courses API: publish courses to Garmin Connect, auto-sync to device
- Supports GPX and FIT formats
- Limit: 50 courses per sync instance
- Legacy devices (6+ years): 100-mile course limit for TCX/GPX

**Live Data Access:**
- Not via cloud API (data syncs post-ride)
- Connect IQ apps can access live sensor data on-device
- ANT+ and Bluetooth sensor broadcasting

**MTB-Specific Features:**
- Edge 540/840/1040 have dedicated MTB dynamics
- Grit, Flow, Jump metrics
- Trailforks map overlay
- ClimbPro for ascent tracking
- 5 Hz GPS on enduro/DH profiles
- Forked mount designed for MTB handlebars

**Priority: HIGH** — Best-in-class MTB cycling computer, excellent API.

---

### 2.2 Wahoo ELEMNT (ACE, BOLT 3, ROAM 3)

**API/Connectivity:**
- **Wahoo Cloud API** — OAuth 2.0 REST API for workout data
- Route import via companion app (FIT, GPX, TCX)
- Third-party route sync from Strava, Komoot, RideWithGPS, TrailForks
- Wi-Fi and Bluetooth sync

**Route Push Capability: PARTIAL**
- No direct API for route push to device
- Routes sync via linked third-party accounts (Komoot, Strava, RideWithGPS)
- Manual import via companion app or USB
- Wahoo Cloud converts route files for device compatibility

**Live Data Access:**
- No cloud-based live data
- Bluetooth sensor data on-device only
- Companion app shows live ride data on phone

**MTB-Specific Features:**
- Basic cycling metrics (no MTB-specific dynamics)
- Robust hardware for off-road use
- Limited MTB-specific software features compared to Garmin

**Priority: LOW-MEDIUM** — Good hardware, but limited API for route push and no MTB-specific data.

---

### 2.3 Hammerhead Karoo (Karoo 3)

**API/Connectivity:**
- **Karoo SDK** — Public SDK on GitHub (`hammerheadnav/karoo-sdk`)
- Android-based platform allows extension development
- Auto-upload to Strava, TrainingPeaks, Suunto, TrainerRoad, Komoot, RideWithGPS, Xert
- Dashboard for route syncing from third-party platforms

**Route Push Capability: PARTIAL**
- Routes sync from linked accounts (Strava, Komoot, RideWithGPS)
- No direct REST API for pushing routes
- Dashboard web interface for route management

**Live Data Access:**
- Karoo SDK allows building custom data field extensions
- Extensions can access live sensor data (power, HR, cadence, speed)
- Java/Kotlin SDK with example apps

**MTB-Specific Features:**
- Climbing/descent detection
- Clean map display suitable for trail navigation
- Durable touchscreen

**Priority: LOW** — Interesting SDK for extensions, but no REST API for server-side integration.

---

### 2.4 Sigma ROX (12.1 EVO, 4.0, 2.0)

**API/Connectivity:**
- **No public developer API**
- Data export via SIGMA RIDE app to third-party portals
- SIGMA DATA CENTER desktop software for data management
- Export formats: STF (proprietary), GPX, KMZ, KML, FIT (ROX 2.0+)
- Direct upload to Strava, TrainingPeaks, Komoot

**Route Push Capability: NO (via API)**
- Routes managed via SIGMA RIDE app
- No programmatic route push capability

**Live Data Access:** None via API

**MTB-Specific Features:**
- Basic cycling metrics
- Robust design for off-road

**Priority: VERY LOW** — No API, proprietary ecosystem.

---

### 2.5 Bryton (Rider S series, Aero)

**API/Connectivity:**
- **No public developer API**
- Data export via Bryton Active app/website
- Export formats: FIT, TCX
- Upload to Strava, TrainingPeaks
- Route import via GPX/FIT in Bryton Active app

**Route Push Capability: LIMITED**
- GPX import via Bryton Active app (not all devices)
- No programmatic API for route push

**Live Data Access:** None via API

**MTB-Specific Features:** Basic cycling metrics only

**Priority: VERY LOW** — No developer API, small market share.

---

## 3. Fitness Platforms & Apps

### 3.1 Garmin Connect

**API:** Garmin Connect Developer Program (Health, Activity, Training, Courses APIs)
**Auth:** OAuth 1.0a
**Access:** Business developers only, free after approval

**Data Export Formats:** JSON (via API), FIT/TCX/GPX (via manual export)

**Unique Data:**
- Body Battery, Stress scores
- Training Status/Load/Effect
- HRV Status (overnight)
- Recovery Time
- VO2 Max
- MTB Dynamics (Grit, Flow, Jumps)
- Sleep Score with detailed staging

**Integration Complexity:** Medium — Good docs, business approval required

**Priority: HIGH**

---

### 3.2 Huawei Health

**API:** Huawei Health Kit REST API
**Auth:** OAuth 2.0 via HMS Core
**Access:** Developer registration on HUAWEI Developers Console, scope approval

**Data Export Formats:** JSON (via API), no direct FIT/GPX export via API

**Unique Data:**
- Integrated Huawei ecosystem data
- TruSleep sleep staging
- TruRelax stress management
- Heart rate, SpO2, HRV
- Activity records with GPS

**Integration Complexity:** Medium — REST API available, requires HMS developer setup

**Priority: HIGH** — User's primary device ecosystem.

---

### 3.3 Apple Health

**API:** HealthKit (on-device iOS SDK only)
**Auth:** On-device permission prompts
**Access:** Requires iOS app

**Data Export Formats:** XML (full export from iPhone), no API-based export

**Unique Data:**
- Aggregated data from all connected devices and apps
- Walking steadiness, cardio fitness (VO2 Max)
- Medication tracking

**Integration Complexity:** Very High — No server-side path, requires iOS app or third-party bridge (Terra ~$0.10/user/month)

**Priority: VERY LOW** — No server-side access feasible for MCP.

---

### 3.4 Samsung Health

**API:** Samsung Health Data SDK (on-device Android SDK)
**Auth:** Partner approval
**Access:** Android app required, SDK recently migrated (old SDK deprecated July 2025)

**Data Export Formats:** No standard export via API

**Unique Data:**
- Body composition (Samsung BIA sensors)
- Blood pressure (Galaxy Watch 4+)

**Integration Complexity:** Very High — On-device only, SDK in transition

**Priority: VERY LOW**

---

### 3.5 Polar Flow

**API:** Polar AccessLink API (REST)
**Auth:** OAuth 2.0
**Access:** Free, open registration at `admin.polaraccesslink.com`

**Data Export Formats:** FIT, TCX, GPX, CSV (via web export); JSON (via API)

**Unique Data:**
- Training Load Pro
- Recovery Pro (Nightly Recharge)
- Running Index / Cycling performance test
- Orthostatic test
- Hill Splitter

**Integration Complexity:** Low — Open API, good docs, Python library available

**Limitations:** 28-day data window, only post-registration exercises

**Priority: MEDIUM**

---

### 3.6 Suunto App

**API:** Suunto Cloud API (Azure API Management)
**Auth:** Business contract required
**Access:** Organizations only, not for personal use

**Data Export Formats:** FIT (via API), GPX/TCX (via manual export)

**Unique Data:**
- SuuntoPlus sport apps
- Training insight and recovery metrics
- FusedTrack GPS data

**Integration Complexity:** High — Formal business application and contract

**Priority: LOW**

---

### 3.7 TrainingPeaks

**API:** TrainingPeaks Partner API
**Auth:** OAuth 2.0
**Access:** Commercial developers only (7-10 day approval), no personal use

**Data Export Formats:** FIT, TCX (via API)

**Unique Data:**
- TSS (Training Stress Score)
- IF (Intensity Factor)
- NP (Normalized Power)
- CTL/ATL/TSB (Fitness/Fatigue/Form)
- Structured workout plans
- Coach-prescribed training

**Integration Complexity:** Medium-High — Commercial approval, custom pricing

**Priority: MEDIUM** — Excellent training metrics, but restricted API access.

---

### 3.8 Intervals.icu

**API:** Public REST API with Swagger docs
**Auth:** API key (personal) or OAuth 2.0 (third-party apps)
**Access:** Free and open, generate API key in Settings > Developer Settings

**Data Export Formats:** FIT, TCX, GPX (activity export); JSON (via API)

**API Docs:** `intervals.icu/api-docs.html` and Swagger UI at `intervals.icu/api/v1/docs/swagger-ui/`

**Unique Data:**
- Fitness/Fatigue model (CTL/ATL/TSB) — free alternative to TrainingPeaks
- Power curve analysis
- HR zones, power zones
- Workout planning and calendar
- Wellness data (weight, HRV, sleep, mood)
- Activity streams (power, HR, cadence, GPS)
- 200+ third-party integrations (Garmin, Polar, Suunto, COROS, Wahoo, Strava, Zwift)

**Rate Limits:** Not strictly documented; API key based, reasonable for personal use

**Integration Complexity:** LOW
- Free, open API
- API key authentication (simple)
- Swagger documentation
- Active community and forum support
- Already aggregates data from multiple sources

**Priority: HIGH** — Best open API in the training analytics space, free, aggregates data from many devices.

---

### 3.9 Runalyze

**API:** Personal API (REST)
**Auth:** API key
**Access:** Available to all users; rate limits vary by tier

**Data Export Formats:** FIT (original), GPX, KML, TCX, FitLog (via API since May 2025)

**Unique Data:**
- TRIMP (Training Impulse)
- Effective VO2 Max
- Marathon shape prediction
- Race result analysis
- Detailed physiological metrics
- Monthly health data CSV export (Supporter+)

**Rate Limits:**
- Free: ~20 requests/hour
- Supporter: 40 requests/hour
- Premium: 150 requests/hour

**Integration Complexity:** Low-Medium
- API key authentication
- New API refactored May 2025
- Activity export endpoints available
- Rate limits may be restrictive for heavy use on free tier

**Priority: LOW-MEDIUM** — Good analysis platform, but rate limits and running-focused.

---

## 4. Priority Ranking for MTB MCP Server

| Priority | Platform/Device | API Quality (1-5) | MTB Value (1-5) | Integration Effort | Key Data | Notes |
|----------|----------------|-------------------|-----------------|-------------------|----------|-------|
| **1** | **Strava** | 4 | 5 | Low | Activities, segments, GPS, HR, power, routes | Already planned. Existing MCP servers available. |
| **2** | **Huawei Health Kit** | 3 | 3 | Medium | HR, GPS, sleep, HRV, stress, cycling activities | **User's device.** REST API available. Priority for personal value. |
| **3** | **Intervals.icu** | 5 | 4 | Low | Fitness/fatigue, power curves, wellness, streams | Best free open API. Aggregates all device data. Huge cycling community. |
| **4** | **Garmin Connect** | 4 | 5 | Medium-High | Body Battery, Grit/Flow, training load, HRV, sleep, MTB dynamics | Best MTB data, but business approval required. Dominant among cyclists. |
| **5** | **Garmin Edge** (computer) | 4 | 5 | Medium-High | Route push, workouts, MTB dynamics, Trailforks | Same API as Garmin Connect. Courses API enables route push to device. |
| **6** | **Polar AccessLink** | 4 | 3 | Low | HR, GPS, Training Load Pro, sleep, recovery | Free open API, easy to integrate. Good for multi-device support. |
| **7** | **Wahoo Cloud API** | 3 | 3 | Medium | Workouts, HR, power, cadence | Useful for ELEMNT/KICKR users. Limited MTB specifics. |
| **8** | **TrainingPeaks** | 3 | 4 | High | TSS, NP, IF, CTL/ATL/TSB, structured workouts | Excellent training data, but commercial-only API. |
| **9** | **Runalyze** | 3 | 2 | Low-Medium | TRIMP, VO2 Max, race analysis | Good analytics, but running-focused. Rate-limited free tier. |
| **10** | **COROS** | 2 | 3 | Medium-High | Activities, training load, GPS | Private API, growing brand. Consider via Intervals.icu aggregation. |
| **11** | **Suunto Cloud** | 2 | 3 | High | Workouts, FIT files, GPS, HR | Business contract required. High barrier. |
| **12** | **Hammerhead Karoo** | 2 | 3 | High | On-device SDK only, no cloud API | Interesting SDK but not server-side accessible. |
| **13** | **Apple Health** | 1 | 2 | Very High | Aggregated health data | No server API. Requires iOS bridge app. |
| **14** | **Samsung Health** | 1 | 1 | Very High | On-device health data | No server API. SDK deprecated/migrating. |
| **15** | **Sigma ROX** | 1 | 2 | Very High | Basic cycling metrics | No API. Proprietary ecosystem. |
| **16** | **Bryton** | 1 | 1 | Very High | Basic cycling metrics | No API. Small market share. |

### Scoring Rationale

**API Quality (1-5):**
- 5 = Public, documented, free, REST, Swagger/OpenAPI docs (Intervals.icu)
- 4 = Official REST API, good docs, approval needed (Garmin, Polar, Strava)
- 3 = REST API exists but limited access or documentation (Huawei, Wahoo, TrainingPeaks, Runalyze)
- 2 = Private/undocumented or SDK-only (COROS, Suunto, Hammerhead)
- 1 = No API or on-device only (Apple, Samsung, Sigma, Bryton)

**MTB Value (1-5):**
- 5 = MTB-specific metrics, GPS, HR, power, segments, route push (Garmin, Strava)
- 4 = Good cycling data with training analytics (Intervals.icu, TrainingPeaks)
- 3 = Standard cycling/fitness data (Huawei, Polar, Wahoo, COROS, Suunto, Hammerhead)
- 2 = Basic fitness tracking, no cycling focus (Apple, Runalyze, Sigma)
- 1 = Minimal cycling relevance (Samsung, Bryton)

---

## 5. Recommended Integration Strategy

### Phase 1: Core Integrations (Immediate)

| Integration | Rationale |
|-------------|-----------|
| **Strava** | Already planned. Use existing `@r-huijts/strava-mcp-server`. Activities, segments, GPS, HR, power. |
| **Huawei Health Kit** | User's device. REST API for pulling HR, GPS tracks, sleep, stress data. Build custom MCP client. |
| **Intervals.icu** | Free open API. Pulls aggregated data from any device. Fitness/fatigue model, power analysis. One integration covers many devices. |

### Phase 2: Power User Features

| Integration | Rationale |
|-------------|-----------|
| **Garmin Connect** | If user adds Garmin device. Best MTB data (Grit, Flow, training load). Route push via Courses API. |
| **Polar AccessLink** | Easy add for multi-device support. Free open API. Training Load Pro. |

### Phase 3: Advanced / On-Demand

| Integration | Rationale |
|-------------|-----------|
| **TrainingPeaks** | If user has TP account. Training metrics (TSS, CTL). Requires commercial approval. |
| **Wahoo Cloud** | If user has Wahoo devices. Workout sync. |
| **Runalyze** | Niche analytics. Personal API. |

### Key Insight: The Intervals.icu Shortcut

**Intervals.icu is the single most valuable integration after Strava** because:
1. It has a free, open, well-documented REST API
2. It already aggregates data from Garmin, Polar, Suunto, COROS, Wahoo, Strava, and Zwift
3. It provides computed training metrics (CTL/ATL/TSB) that would otherwise require TrainingPeaks ($20/month + commercial API)
4. A single integration gives us access to most users' training data regardless of their device
5. Active developer community with cookbook and forum support

For the user's specific setup (Huawei watch + Strava), the recommended data flow would be:

```
Huawei Watch → Huawei Health App → Strava (auto-sync) → Intervals.icu (auto-sync)
                    ↓                      ↓                       ↓
              Huawei Health Kit      Strava MCP              Intervals.icu MCP
              (HR, sleep, stress)   (activities, GPS)       (training analytics)
```

This gives us three complementary data sources:
- **Huawei Health Kit:** Raw biometrics (HR, sleep quality, stress, HRV)
- **Strava:** Activity data, segments, social features, GPS tracks
- **Intervals.icu:** Computed training load, fitness/fatigue balance, power analysis

---

## Sources

### Huawei Health Kit
- [Huawei Health Kit Developer Portal](https://developer.huawei.com/consumer/en/hms/huaweihealth/)
- [Health Kit REST API Overview](https://developer.huawei.com/consumer/en/doc/HMSCore-References/rest-overview-0000001254420693)
- [Health Kit REST API Service Introduction](https://developer.huawei.com/consumer/en/doc/development/HMSCore-Guides/overview-restful-api-0000001050071695)
- [Health Kit Data Model](https://developer.huawei.com/consumer/en/doc/development/HMSCore-References/data-model-0000001054556973)
- [Health Kit REST vs SDK Comparison](https://medium.com/huawei-developers/rest-vs-on-device-sdk-what-is-the-difference-huawei-health-kit-comparison-a18e5e80322c)
- [Huawei Health Kit Activity Record: Cycling](https://medium.com/huawei-developers/huawei-health-kit-activity-record-cycling-7672ad6b0f41)

### Garmin
- [Garmin Connect Developer Program Overview](https://developer.garmin.com/gc-developer-program/overview/)
- [Garmin Health API](https://developer.garmin.com/gc-developer-program/health-api/)
- [Garmin Activity API](https://developer.garmin.com/gc-developer-program/activity-api/)
- [Garmin Training API](https://developer.garmin.com/gc-developer-program/training-api/)
- [Garmin Courses API](https://developer.garmin.com/gc-developer-program/courses-api/)
- [Garmin Program FAQ](https://developer.garmin.com/gc-developer-program/program-faq/)
- [Connect IQ SDK](https://developer.garmin.com/connect-iq/overview/)

### Polar
- [Polar AccessLink API](https://www.polar.com/accesslink-api/)
- [Polar AccessLink Developer Portal](https://www.polar.com/en/accesslink)
- [Polar AccessLink Python Example](https://github.com/polarofficial/accesslink-example-python)

### Suunto
- [Suunto API Zone](https://apizone.suunto.com/)
- [Suunto API FAQ](https://apizone.suunto.com/faq)

### COROS
- [COROS API Application](https://support.coros.com/hc/en-us/articles/17085887816340-Submitting-an-API-Application)
- [COROS Bulk Export](https://support.coros.com/hc/en-us/articles/25002333092500-Requesting-a-Bulk-Export-of-COROS-Data)

### Wahoo
- [Wahoo Cloud API Developer Portal](https://developers.wahooligan.com/cloud)
- [Wahoo Cloud API Reference](https://cloud-api.wahooligan.com/)

### Samsung
- [Samsung Health Developer Portal](https://developer.samsung.com/health)
- [Samsung Health Data SDK](https://developer.samsung.com/health/data)
- [Samsung Health SDK Deprecation Notice](https://developer.samsung.com/sdp/news/en/2025/10/30/dev-insight-oct-2025-move-to-samsung-health-data-sdk-as-samsung-health-sdk-for-android-deprecates-and-other-latest-news)

### Apple
- [Apple HealthKit Documentation](https://developer.apple.com/documentation/healthkit)

### TrainingPeaks
- [TrainingPeaks API Help Center](https://help.trainingpeaks.com/hc/en-us/articles/234441128-TrainingPeaks-API)
- [TrainingPeaks API Update Blog](https://www.trainingpeaks.com/blog/an-update-on-trainingpeaks-partner-api/)

### Intervals.icu
- [Intervals.icu API Documentation](https://intervals.icu/api-docs.html)
- [Intervals.icu Swagger UI](https://intervals.icu/api/v1/docs/swagger-ui/index.html)
- [Intervals.icu API Integration Cookbook](https://forum.intervals.icu/t/intervals-icu-api-integration-cookbook/80090)
- [Intervals.icu API Access Forum](https://forum.intervals.icu/t/api-access-to-intervals-icu/609)

### Runalyze
- [Runalyze Personal API Help](https://runalyze.com/help/article/personal-api?_locale=en)
- [Runalyze Changelog](https://runalyze.com/changelog?_locale=en)

### Strava MCP Servers
- [strava-mcp (r-huijts)](https://github.com/r-huijts/strava-mcp)
- [strava-mcp (kw510)](https://github.com/kw510/strava-mcp)
- [mcp-strava (MariyaFilippova)](https://github.com/MariyaFilippova/mcp-strava)

### Hammerhead
- [Hammerhead Developer Platform](https://www.hammerhead.io/pages/developer-platform)
- [Karoo SDK (GitHub)](https://github.com/hammerheadnav/karoo-sdk)

### Market Data
- [Strava 2025 Year in Sport Report](https://the5krunner.com/2025/12/04/strava-2025-year-in-sport-report-apple-watch-coros-gen-z/)
- [Global Smartwatch Shipments Market Share](https://counterpointresearch.com/en/insights/global-smartwatch-shipments-market-share)
