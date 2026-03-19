# MTB MCP -- Competitive Landscape Analysis

**Date:** 2026-03-18
**Scope:** All-in-one MTB app that combines multi-source tour search, live BLE sensor integration, weather-aware planning, intelligent maintenance tracking, eBike range planning, crash detection, post-ride analytics, and proactive recommendations.

---

## Executive Summary

**No single app or platform combines all eight target features.** The market is highly fragmented: trail discovery, ride tracking, sensor telemetry, bike maintenance, eBike motor management, and crash detection are each served by separate apps and hardware ecosystems. Riders currently need 4-7 apps to cover the functionality our vision unifies.

The closest "all-in-one" attempts come from hardware ecosystems (Garmin, Wahoo, SRAM/Hammerhead) that bundle sensors + computers + companion apps, but these are locked to their own hardware and lack multi-source tour search, intelligent maintenance, and eBike motor integration.

---

## Feature Matrix: Our Vision vs. Market

| Feature | Strava | Komoot | Trailforks | Bosch Flow | ProBikeGarage | Velo Buddy | Trailmetry | Motion Instruments | SAGLY | Garmin Ecosystem |
|---------|--------|--------|------------|------------|---------------|------------|------------|-------------------|-------|-----------------|
| **1. Multi-source tour search** | -- | Own only | Own only | -- | -- | -- | -- | -- | -- | Partial (sync) |
| **2. Live BLE sensors (tire, suspension, power)** | HR/Power/Cadence | -- | -- | Motor only | -- | -- | Suspension only | Suspension only | -- | HR/Power/Cadence/Radar |
| **3. Weather-aware planning** | -- | Premium (basic) | Weather map | -- | -- | -- | Weather correlated | -- | -- | Via Epic Ride Weather |
| **4. Intelligent wear tracking** | -- | -- | -- | -- | km/time-based | AI-based | -- | -- | -- | -- |
| **5. eBike range planning** | -- | -- | -- | AI Range Control | -- | -- | -- | -- | -- | Partial (Shimano) |
| **6. Crash detection** | Beacon only | -- | -- | -- | -- | -- | -- | -- | -- | Incident Detection |
| **7. Post-ride analytics + auto trail-tagging** | Segments | Basic | Ride logging | Basic | -- | -- | Suspension analytics | Suspension analytics | -- | Segments |
| **8. Proactive ride recommendations** | Suggested Routes | -- | -- | -- | -- | -- | Setup suggestions | -- | -- | Suggested Routes |

**Key insight:** No competitor covers more than 3 of our 8 features. The Garmin ecosystem comes closest at ~4, but requires $500+ in hardware and offers no multi-source search, no intelligent maintenance, no eBike motor integration, and no tire pressure/suspension telemetry.

---

## Detailed Competitor Analysis

### Tier 1: Major Cycling Platforms

#### 1. Strava

- **Platform:** iOS, Android, Web
- **Key features:** GPS activity tracking, social network, segment leaderboards, route planning, training analysis, Beacon safety, suggested routes, club features
- **BLE sensors:** Heart rate, power meters, cadence, speed via paired devices (Garmin, Wahoo, etc.) -- not native app BLE
- **What's missing:** No tour aggregation from external sources, no tire pressure or suspension telemetry, no bike maintenance tracking, no eBike integration, no weather-based planning, no crash detection (relies on watch/computer), no trail condition estimation
- **Pricing:** Free (basic tracking + social); Premium $11.99/month or $79.99/year
- **Ratings:** 4.6 App Store, 4.3 Google Play
- **Adoption:** 120M+ registered users, dominant platform for ride tracking
- **Strength as competitor:** Massive user base and social lock-in; hard to displace for ride recording
- **Weakness:** Not MTB-focused; no sensor depth; increasingly paywalling features

#### 2. Komoot

- **Platform:** iOS, Android, Web, Apple Watch, Garmin/Wahoo sync
- **Key features:** Route planning with surface types, turn-by-turn voice navigation, offline maps, sport-specific map layers, community highlights, multi-day planning, 3D maps
- **BLE sensors:** None (relies on phone GPS)
- **What's missing:** No BLE sensor integration, no maintenance tracking, no eBike range planning, no crash detection, no suspension/tire telemetry, no real-time trail conditions, basic weather (premium only)
- **Pricing:** Free (limited); Premium $59.99/year (was one-time region unlocks, now subscription-only for new users since Feb 2025 -- controversial)
- **Ratings:** 4.7 App Store, 4.5 Google Play
- **Adoption:** 40M+ users, very strong in DACH/Europe
- **Strength as competitor:** Best-in-class route planning UX; strong European trail data
- **Weakness:** No API for third-party integration (reverse-engineered only); paywall backlash; purely planning/navigation -- no ride analytics depth

#### 3. Trailforks

- **Platform:** iOS, Android, Web
- **Key features:** World's largest MTB trail database (225k+ trails), trail condition reports, weather map overlay, difficulty ratings, offline maps, heatmaps, route planner, community condition reporting
- **BLE sensors:** None
- **What's missing:** No sensor integration, no maintenance tracking, no eBike support, no crash detection, no post-ride analytics beyond basic logging, no proactive recommendations, no weather-based trail condition estimation
- **Pricing:** Free (limited to ~35x35 mile home area); Pro $35.99/year ($2.99/month)
- **Ratings:** 4.7 App Store, 4.5 Google Play (but reviews note bugs and UI issues)
- **Adoption:** Dominant MTB trail platform, owned by Outside Inc. (Pinkbike parent)
- **Strength as competitor:** Unmatched trail database depth for MTB; community condition reports
- **Weakness:** No public API (integration not feasible); free tier very limited; app quality complaints increasing; purely trail discovery, no ride intelligence

#### 4. AllTrails

- **Platform:** iOS, Android, Web
- **Key features:** 450k+ trails (hiking-focused), reviews, photos, GPS tracking, offline maps, trail discovery
- **BLE sensors:** None
- **What's missing:** Weak MTB focus (hiking-first); no sensor integration; no maintenance; no eBike; no weather planning; no crash detection; no analytics depth
- **Pricing:** Free (basic); AllTrails+ $35.99/year
- **Ratings:** 4.9 App Store (highest rated), 4.6 Google Play
- **Adoption:** 60M+ users, primarily hikers
- **Strength as competitor:** Massive user base, excellent trail reviews
- **Weakness:** Not MTB-optimized; no technical riding data; no public API

#### 5. onX Backcountry (powered by MTB Project)

- **Platform:** iOS, Android
- **Key features:** MTB Project trail data integrated, 3D maps, live tracking, detailed topography, elevation profiles, trail difficulty ratings, weather tools, offline maps, land ownership data
- **BLE sensors:** None
- **What's missing:** No sensor integration, no maintenance, no eBike, no crash detection, no post-ride analytics, no proactive recommendations
- **Pricing:** Free (basic); Premium $29.99/year; Elite $99.99/year
- **Ratings:** 4.7 App Store
- **Adoption:** Growing, strong in US backcountry
- **Strength as competitor:** Excellent map quality with MTB Project data; good weather integration
- **Weakness:** US-focused; no European trail data depth; no sensor/hardware ecosystem

---

### Tier 2: Sensor & Telemetry Systems

#### 6. Trailmetry

- **Platform:** iOS, Android
- **Key features:** Suspension telemetry via BLE sensors (Witmotion WT9011DCL), fork and rear shock analysis, GPS tracking, heart rate integration, weather-correlated setup suggestions, tire pressure recommendations, ride recording
- **BLE sensors:** Suspension (via external Witmotion sensors, ~EUR25 each)
- **What's missing:** No multi-source tour search, no route planning, no maintenance tracking, no eBike support, no crash detection, no post-ride trail-tagging, no proactive ride recommendations
- **Pricing:** Free (single fork sensor); Premium subscription for rear shock analysis
- **Ratings:** New/niche -- limited reviews
- **Adoption:** Small but growing MTB enthusiast niche
- **Strength as competitor:** Closest to our BLE sensor vision; affordable entry; weather-correlated setup advice
- **Weakness:** Suspension-only focus; no broader ride ecosystem; depends on specific sensor hardware

#### 7. Motion Instruments (System 2 + MotionIQ app)

- **Platform:** iOS, Android (MotionIQ app)
- **Key features:** Professional-grade suspension data acquisition, rebound/compression analysis, axle position, vibration, bike balance, GPS integration, works with XC through DH air spring forks
- **BLE sensors:** Custom suspension sensors (accelerometer, gyroscope, GPS)
- **What's missing:** No tour search, no route planning, no weather planning, no maintenance tracking, no eBike, no crash detection, no social features, no tire pressure
- **Pricing:** $499 for System 2 hardware kit
- **Ratings:** Highly regarded in enthusiast/pro community
- **Adoption:** Niche pro/enthusiast market
- **Strength as competitor:** Gold standard for suspension setup data; professional credibility
- **Weakness:** Expensive; single-purpose (suspension only); no broader app ecosystem

#### 8. BYB Telemetry

- **Platform:** Proprietary hardware + software
- **Key features:** Professional telemetry system for MTB, 1000Hz sampling rate, works with any fork/shock (air or coil), accelerometer/gyroscope/GPS, used by World Cup teams
- **BLE sensors:** Custom sensors
- **What's missing:** Everything outside suspension telemetry
- **Pricing:** Professional-tier pricing (not publicly listed, estimated EUR500+)
- **Ratings:** Pro/team market validation
- **Adoption:** Teams and high-end bike shops
- **Strength as competitor:** Highest fidelity data; pro team validation
- **Weakness:** Not consumer-friendly; no app ecosystem; pure telemetry tool

#### 9. Quarq TyreWiz (SRAM)

- **Platform:** SRAM AXS app (iOS, Android) + compatible bike computers
- **Key features:** Real-time tire pressure monitoring via BLE valve sensors, per-second pressure data, low pressure alerts
- **BLE sensors:** Tire pressure (BLE to SRAM AXS app or compatible computer)
- **What's missing:** Only tire pressure -- no suspension, no power, no route planning, no maintenance, no eBike, no crash detection
- **Pricing:** ~$50/pair (hardware sensors)
- **Ratings:** Well-reviewed for what it does
- **Adoption:** Moderate -- SRAM ecosystem riders
- **Strength as competitor:** Best-in-class tire pressure monitoring; SRAM ecosystem integration
- **Weakness:** SRAM-locked ecosystem; single measurement only; sensor discontinued/hard to find

#### 10. AIRsistant (Schrader)

- **Platform:** iOS, Android app
- **Key features:** BLE tire pressure and temperature monitoring, valve-mounted sensors, real-time alerts, optimal pressure recommendations for riding conditions
- **BLE sensors:** Tire pressure + temperature
- **What's missing:** Everything beyond tire pressure
- **Pricing:** ~EUR40-60 per pair
- **Adoption:** Niche, growing in eBike segment
- **Strength as competitor:** Consumer-friendly tire pressure monitoring
- **Weakness:** Single-purpose; limited ecosystem

---

### Tier 3: Bike Maintenance Trackers

#### 11. ProBikeGarage

- **Platform:** iOS, Android, Web
- **Key features:** Component tracking, maintenance alerts (distance, time, rides), Strava auto-sync, customizable setups per ride type, service documentation, photo/video storage (10GB), parts price comparison
- **BLE sensors:** None (Strava sync for ride data)
- **What's missing:** No intelligent/AI wear prediction (strictly interval-based), no tour search, no weather, no eBike, no crash detection, no ride analytics, no sensor integration
- **Pricing:** Free (basic); Premium subscription for advanced features
- **Ratings:** 4.6 App Store, well-regarded in cycling community
- **Adoption:** Established, active development (v2.0 launched 2024)
- **Strength as competitor:** Most mature maintenance tracker; good Strava integration
- **Weakness:** km/time-based intervals only -- not "intelligent"; no broader riding features

#### 12. Velo Buddy

- **Platform:** iOS, Android
- **Key features:** AI-powered wear prediction based on riding patterns + weather + terrain + intensity, Strava sync, tire pressure calculator, cost tracking/budgeting, smart maintenance reminders, learns from component replacement history
- **BLE sensors:** None (uses Strava ride data for AI analysis)
- **What's missing:** No tour search, no route planning, no live sensor integration, no eBike, no crash detection, no ride analytics beyond maintenance, no weather-based ride planning
- **Pricing:** Free (1 bike); Premium for unlimited bikes
- **Ratings:** New app, limited reviews
- **Adoption:** Early stage
- **Strength as competitor:** Closest to our "intelligent maintenance" vision -- uses AI, considers weather and riding style
- **Weakness:** New/unproven; maintenance-only focus; no hardware sensor integration

#### 13. The Bike Mechanic

- **Platform:** iOS, Android
- **Key features:** Smart maintenance tracking, Strava + Intervals.icu auto-sync, component lifecycle management, power meter battery monitoring, shifter battery monitoring, zero manual entry
- **BLE sensors:** None (Strava-derived data)
- **What's missing:** No AI prediction, no tour search, no weather, no eBike, no crash detection
- **Pricing:** Not publicly listed
- **Ratings:** Limited data
- **Adoption:** Niche
- **Strength as competitor:** Good multi-platform activity sync; battery monitoring unique
- **Weakness:** Limited feature set; unclear business viability

#### 14. mainTrack

- **Platform:** iOS
- **Key features:** Component usage tracking, maintenance reminders (time, usage, rides, elapsed time), service records, multi-bike management
- **BLE sensors:** None
- **What's missing:** No AI, no tour search, no weather, no eBike, no crash detection
- **Pricing:** Free with IAP
- **Ratings:** 4.6 App Store
- **Adoption:** Small but loyal user base
- **Strength as competitor:** Clean, focused maintenance tracker
- **Weakness:** iOS only; basic interval tracking; no intelligence layer

#### 15. CRANKLOGIX

- **Platform:** Web/Mobile (early stage)
- **Key features:** AI-powered diagnostics, component tracking, ride optimization, maintenance prediction
- **BLE sensors:** None
- **What's missing:** Appears early-stage; no tour search, no weather, no eBike, no crash detection, no live sensors
- **Pricing:** Not yet publicly available
- **Ratings:** Too new for ratings
- **Adoption:** Pre-launch/early
- **Strength as competitor:** AI-first approach to maintenance; MTB-focused positioning
- **Weakness:** Unproven; early stage; limited feature scope

---

### Tier 4: eBike Motor Ecosystems

#### 16. Bosch eBike Flow App

- **Platform:** iOS, Android
- **Key features:** AI-powered Range Control (uses 20+ riding variables), route planning with battery estimation, automatic motor adjustment to reach destination, ride recording, OTA firmware updates, customizable riding modes, anti-theft features
- **BLE sensors:** Motor/battery system via eBike SDK (BLE), speed, distance, riding time
- **What's missing:** No multi-source tour search, no tire pressure/suspension telemetry, no maintenance tracking, no crash detection, no trail condition estimation, no post-ride analytics beyond basic stats, no proactive ride recommendations
- **Pricing:** Free basic; Flow+ EUR4.99/month or EUR39.99/year (first 12 months free)
- **Ratings:** 3.5-4.0 (mixed reviews, connectivity complaints)
- **Adoption:** Dominant -- Bosch is #1 eBike motor manufacturer
- **Strength as competitor:** Best-in-class eBike range planning; AI learning improves over time; official SDK/API available for third-party integration
- **Weakness:** Bosch-only; no trail/tour features; limited analytics; connectivity issues reported

#### 17. Specialized Mission Control / Specialized App

- **Platform:** iOS, Android
- **Key features:** Smart Control (auto-adjusts motor output for target ride time/distance), motor customization sliders, ride recording, diagnostics, range management
- **BLE sensors:** Specialized eBike motor system only
- **What's missing:** Everything outside Specialized eBike motor management
- **Pricing:** Free (with Specialized eBike)
- **Adoption:** Specialized eBike owners only
- **Strength as competitor:** Excellent motor tuning UX; Smart Control is well-implemented
- **Weakness:** Completely locked to Specialized hardware; no broader ecosystem

#### 18. Shimano E-Tube Ride

- **Platform:** iOS, Android
- **Key features:** Ride data display, motor assist customization, D-FLY wireless integration with third-party computers, Interface X for ANT+ compatibility
- **BLE sensors:** Shimano STEPS motor system
- **What's missing:** No range planning sophistication (vs Bosch), no tour search, no maintenance, no analytics
- **Pricing:** Free
- **Adoption:** Shimano STEPS eBike owners
- **Strength as competitor:** Third-party device compatibility via ANT+ / D-FLY
- **Weakness:** Limited app features; basic compared to Bosch Flow

---

### Tier 5: Crash Detection & Safety

#### 19. Tocsen Crash Sensor

- **Platform:** iOS, Android + dedicated sensor (helmet-mounted)
- **Key features:** Helmet-mounted crash sensor, automatic emergency contact alerts, GPS location sharing, "rescue community" (alerts nearby Tocsen users), 3-month rechargeable battery
- **BLE sensors:** Proprietary crash sensor (accelerometer + gyroscope)
- **What's missing:** Everything outside crash detection
- **Pricing:** ~EUR80 for sensor
- **Adoption:** Growing in European MTB community
- **Strength as competitor:** MTB-specific crash detection; community rescue feature is unique
- **Weakness:** Single-purpose; requires separate hardware

#### 20. Specialized ANGi

- **Platform:** iOS, Android (via Specialized app)
- **Key features:** Helmet-mounted sensor with accelerometer + gyroscope, BLE connection, automatic emergency alerts, countdown timer
- **BLE sensors:** Crash detection sensor
- **What's missing:** Everything outside crash detection
- **Pricing:** Included with compatible Specialized helmets
- **Adoption:** Specialized helmet owners
- **Strength as competitor:** Integrated into helmet; no separate purchase needed
- **Weakness:** Specialized-only ecosystem; helmet-dependent

#### 21. Garmin Incident Detection

- **Platform:** Garmin Edge bike computers + Connect app
- **Key features:** Built into bike computers, detects sudden deceleration/impact, sends GPS location to emergency contacts, integrates with LiveTrack
- **BLE sensors:** Built into Garmin Edge (accelerometer)
- **What's missing:** Requires Garmin hardware ($200-$600)
- **Pricing:** Included with Garmin Edge computers
- **Adoption:** Large -- Garmin Edge is market leader in bike computers
- **Strength as competitor:** No extra hardware; works automatically; trusted brand
- **Weakness:** Garmin-locked; hardware cost; part of larger computer, not standalone

---

### Tier 6: Setup & Tuning

#### 22. SAGLY

- **Platform:** iOS, Android
- **Key features:** MTB suspension setup guidance (sag-based), AI/ML-powered baseline settings using rider data + bike type + terrain + skill level, "bracketing" method (World Cup technique), setup history, community setup sharing, training plans, bike component database
- **BLE sensors:** None (manual input for suspension settings)
- **What's missing:** No live telemetry, no tour search, no weather planning, no maintenance tracking, no eBike, no crash detection, no ride recording
- **Pricing:** Free (basic); PRO EUR7.90/month or ~EUR50/year
- **Ratings:** Well-reviewed; praised for ease of use
- **Adoption:** Growing MTB enthusiast niche
- **Strength as competitor:** Best static suspension setup guide; AI recommendations; community sharing
- **Weakness:** No live data -- all manual input; setup guidance only, not a riding companion

---

### Tier 7: Hardware Ecosystems (Integrated but Closed)

#### 23. Garmin Cycling Ecosystem

- **Platform:** Edge computers + Connect app + sensor lineup
- **Key features:** GPS bike computers, ANT+/BLE sensor hub (HR, power, cadence, speed, Varia radar/camera, lights), incident detection, LiveTrack, training plans, Strava/Komoot/Trailforks sync, weather (via Connect IQ apps)
- **BLE sensors:** Full ANT+/BLE: HR, power, cadence, speed, radar, lights, eBike (Shimano)
- **What's missing:** No multi-source tour search in one view, no tire pressure monitoring, no suspension telemetry, no intelligent maintenance, no eBike range planning (except basic Shimano), limited weather-trail correlation
- **Pricing:** Edge computers $249-$599; sensors $30-$400 each; no app subscription
- **Adoption:** Market leader in cycling computers
- **Strength as competitor:** Broadest sensor ecosystem; most reliable hardware; deep analytics
- **Weakness:** Expensive; hardware-locked; no software-only option; fragmented app experience

#### 24. Wahoo Ecosystem

- **Platform:** ELEMNT computers + Companion app + 110+ app partners
- **Key features:** BLE/ANT+ sensor support, Strava/Komoot/Trailforks/TrainingPeaks sync, structured training (SYSTM), KICKR trainer integration
- **BLE sensors:** HR, power, cadence, speed, radar
- **What's missing:** Similar to Garmin -- no tire pressure, no suspension, no intelligent maintenance, no eBike range, limited weather
- **Pricing:** ELEMNT computers $299-$599
- **Adoption:** Strong #2 behind Garmin
- **Strength as competitor:** Best third-party app compatibility (110+ partners); clean UX
- **Weakness:** Hardware-dependent; narrower sensor range than Garmin

#### 25. Hammerhead Karoo (SRAM)

- **Platform:** Karoo 3 computer + Companion app + Dashboard
- **Key features:** Android-based bike computer, third-party app support (Epic Ride Weather, etc.), SRAM AXS auto-sync (gearing, battery status), BLE/ANT+ sensors, Strava/Komoot sync
- **BLE sensors:** HR, power, cadence, speed, SRAM AXS components
- **What's missing:** Same gaps as Garmin/Wahoo
- **Pricing:** Karoo 3 $399
- **Adoption:** Growing, enthusiast-focused
- **Strength as competitor:** Most open platform (Android-based, third-party apps on device); SRAM component integration
- **Weakness:** SRAM-biased; smaller ecosystem than Garmin

---

### Tier 8: Bike Computer Apps (Smartphone-Based)

#### 26. SuperCycle Bike Computer

- **Platform:** iOS, Android
- **Key features:** GPS tracking, BLE sensor support (speed, cadence, HR, power), real-time data display, ride mapping
- **BLE sensors:** Standard cycling BLE sensors (HR, speed, cadence, power)
- **What's missing:** No tour search, no trail conditions, no maintenance, no eBike, no crash detection, no weather planning, no suspension/tire sensors
- **Pricing:** Free with IAP
- **Adoption:** Moderate
- **Strength as competitor:** Good BLE sensor support in a phone app
- **Weakness:** Basic feature set; no MTB-specific intelligence

#### 27. Cadence App

- **Platform:** iOS, Android
- **Key features:** GPS tracking, BLE sensor support (HR, speed, cadence, power, Garmin Varia radar), Apple Watch support, clean interface
- **BLE sensors:** Standard cycling BLE + Garmin Varia radar (rare for phone apps)
- **What's missing:** No tour aggregation, no trail conditions, no maintenance, no eBike, no crash detection, limited analytics
- **Pricing:** Free with premium
- **Adoption:** Niche but growing
- **Strength as competitor:** One of few phone apps supporting Garmin Varia radar; good BLE breadth
- **Weakness:** Road-cycling oriented; no MTB-specific features

---

## Gap Analysis: What Nobody Does

| Capability | Status in Market |
|-----------|-----------------|
| **Unified multi-source tour search** (Komoot + Trailforks + GPS-Tour.info + OSM in one interface) | **Does not exist.** Each platform is siloed. |
| **Live BLE tire pressure + suspension + power in one app** | **Does not exist.** Tire pressure (Quarq/AIRsistant), suspension (Trailmetry/Motion), and power (Strava/Garmin) are separate ecosystems. |
| **Weather-aware trail condition estimation** (rain history -> mud probability) | **Does not exist.** Trailforks has community reports + weather map but no automated estimation. Epic Ride Weather covers route weather but not trail surface conditions. |
| **Intelligent component wear tracking** (ride-intensity + weather + terrain aware) | **Emerging.** Velo Buddy is attempting this with AI but is early-stage and maintenance-only. |
| **Cross-brand eBike range planning** (Bosch + Shimano + Brose + Fazua) | **Does not exist.** Each brand has its own app. Bosch SDK is available for third-party integration. |
| **Crash detection integrated with ride context** | **Partial.** Garmin, Apple Watch, Tocsen have crash detection, but none correlate with trail difficulty, riding history, or emergency trail access routes. |
| **Auto trail-tagging from GPS traces** (match ride to known trail segments) | **Partial.** Strava does this for road segments. Trailforks does basic ride logging. No app auto-matches GPS traces to trail databases across platforms. |
| **Proactive "you should ride today" recommendations** (weather + fitness + trail conditions + schedule) | **Does not exist.** Strava suggests routes. Komoot suggests tours. Neither proactively says "conditions are perfect, here's your ideal ride." |

---

## Pricing Landscape Summary

| App/Service | Free Tier | Premium Price | Model |
|------------|-----------|--------------|-------|
| Strava | Basic tracking + social | $79.99/year | Subscription |
| Komoot | Very limited (new users) | $59.99/year | Subscription (controversial change) |
| Trailforks | Small home area | $35.99/year | Subscription |
| AllTrails | Basic | $35.99/year | Subscription |
| onX Backcountry | Basic | $29.99-$99.99/year | Subscription (tiered) |
| ProBikeGarage | 1 bike basic | Premium subscription | Subscription |
| Velo Buddy | 1 bike full | Premium for more bikes | Freemium |
| SAGLY | Basic setup | EUR50/year | Subscription |
| Bosch Flow+ | Basic motor | EUR39.99/year | Subscription (12mo free) |
| Trailmetry | 1 fork sensor | Premium for rear shock | Freemium + hardware |
| Motion Instruments | -- | $499 hardware | One-time hardware |
| Tocsen | -- | ~EUR80 hardware | One-time hardware |
| Garmin Edge | -- | $249-$599 hardware | One-time hardware |

**Market pricing sweet spot for an all-in-one MTB app:** $5-10/month ($50-100/year), based on what cyclists already pay across multiple apps.

---

## Competitive Moats & Risks

### Why fragmentation persists (and why there's an opportunity):

1. **Hardware lock-in:** Garmin, Wahoo, SRAM each want you in their ecosystem. A software-only solution that bridges hardware is valuable.
2. **Data silo incentives:** Strava, Komoot, Trailforks each monetize their data separately. No incentive to federate.
3. **BLE complexity:** Integrating diverse BLE sensor types (tire pressure, suspension, power, motor) requires deep protocol knowledge. Most app developers stick to standard cycling BLE profiles.
4. **eBike motor APIs:** Bosch is the only motor manufacturer with a public SDK/API. Shimano, Brose, and Fazua have limited third-party support.

### Key risks:

1. **Strava as platform:** If Strava ever adds maintenance tracking or sensor depth, their user base gives them instant adoption.
2. **Garmin software improvement:** Garmin Connect is getting better; if they add intelligent maintenance and weather-trail correlation, their hardware base is unbeatable.
3. **Komoot paywall backlash:** Komoot's pricing changes are pushing users to seek alternatives -- opportunity for us.
4. **API access:** Komoot (reverse-engineered) and Trailforks (no API) integrations carry legal/stability risk.
5. **Sensor fragmentation:** New BLE sensor standards could change the landscape; we need to stay protocol-agnostic.

---

## Strategic Positioning Recommendation

**Our unique value proposition:** "The first MTB app that connects everything -- your trails, your sensors, your bike, your weather, your motor -- into one intelligent riding companion."

**Differentiation pillars:**
1. **Multi-source aggregation** -- search Komoot + OSM + GPS-Tour.info trails in one query (Trailforks API not feasible)
2. **Universal BLE sensor hub** -- tire pressure + suspension + power + motor in one app, hardware-agnostic
3. **Weather-to-trail intelligence** -- "It rained 15mm yesterday, Waldboden trails are likely muddy" (nobody does this)
4. **Intelligent maintenance** -- ride-context-aware component tracking (beyond simple km counters)
5. **Cross-brand eBike integration** -- starting with Bosch SDK, the only open motor API
6. **Proactive riding assistant** -- "Saturday morning looks perfect for the Hetzlas trail, your tire pressure is optimal, chain has 200km left before service"

**Phase 1 focus (highest differentiation, lowest competition):**
- Multi-source tour search (MCP architecture enables this naturally)
- Weather + trail condition estimation (DWD + OSM data, unique combination)
- Proactive ride recommendations (scheduled tasks + weather + fitness)

**Phase 2 focus (medium difficulty, growing market):**
- BLE sensor integration (start with standard cycling sensors, add tire pressure)
- Intelligent maintenance tracking (Strava ride data + weather context)
- Post-ride analytics with auto trail-tagging

**Phase 3 focus (hardest, highest moat):**
- eBike range planning via Bosch SDK
- Suspension telemetry integration
- Crash detection with trail-context intelligence

---

## Sources

- [BikeRadar: Best cycling apps 2026](https://www.bikeradar.com/advice/buyers-guides/best-cycling-apps)
- [BikeMag: 10 Best Cycling Apps for MTB](https://www.bikemag.com/mountain-bike-gear/best-cycling-apps-for-mtb)
- [Trailmetry](https://trailmetry.com/)
- [Motion Instruments](https://motioninstruments.com/)
- [BYB Telemetry](https://www.bybtech.it/telemetry)
- [Quarq TyreWiz](https://www.sram.com/en/quarq/series/tyrewiz)
- [AIRsistant](https://www.airsistant.com/)
- [ProBikeGarage](https://www.probikegarage.com/)
- [Velo Buddy](https://velobuddy.bike/)
- [The Bike Mechanic](https://themechanic.bike/)
- [CRANKLOGIX](https://www.cranklogix.com/)
- [mainTrack](https://maintrack.app/)
- [SAGLY MTB App](https://sagly.at/)
- [Bosch eBike Flow App](https://www.bosch-ebike.com/us/products/ebike-flow-app)
- [Bosch eBike SDK / Cloud API](https://www.bosch-ebike.com/us/company/industry-solutions/cloud-api-ebike-sdk)
- [Specialized Mission Control](https://www.specialized.com/us/en/app)
- [Shimano E-Tube Ride](https://bike.shimano.com/products/apps/e-tube-ride.html)
- [Tocsen Crash Sensor](https://powunity.com/en/bike-crash-detection-bike-apps-can-also-provide-first-aid)
- [Strava Pricing](https://www.strava.com/pricing)
- [Strava Safety Features](https://www.techradar.com/health-fitness/four-strava-safety-features-every-user-needs-to-know-about-including-you)
- [Komoot Pricing Changes](https://www.dcrainmaker.com/2025/03/komoots-expanded-paywalls-trying-to-make-sense-of-it.html)
- [Trailforks App](https://www.trailforks.com/apps/map)
- [onX Backcountry MTB](https://www.onxmaps.com/backcountry/app/features/mountain-biking)
- [Epic Ride Weather](https://www.epicrideweather.com/)
- [Garmin Cycling Ecosystem](https://www.garmin.com/en-US/c/sports-fitness/cycling-bike-computers-bike-radar-power-meter-headlights/)
- [Wahoo ELEMNT Integrations](https://www.wahoofitness.com/devices/bike-computers/elemnt-integrations)
- [Hammerhead Karoo Third-Party Apps](https://www.cyclingweekly.com/products/the-major-update-ive-been-waiting-for-hammerhead-karoo-computers-now-support-third-party-apps)
- [SuperCycle Bike Computer](https://play.google.com/store/apps/details?id=com.osborntech.supercycle)
- [Cadence App](https://getcadence.app/)
- [Sufni Open Source Suspension Telemetry](https://www.mtbr.com/threads/sufni-suspensiont-telemetry-an-open-source-suspension-telemetry-system.1220806/)
- [BIKE Magazin: MTB-Touren-Portale Vergleich](https://www.bike-magazin.de/touren/touren-tipps/mtb-touren-portale-und-deren-apps-im-vergleich/)
- [Tubolito PSENS Reifendruck](https://wattmoves.de/fahrradschlauch-mit-sensor-tubo-mtb-psens-reifenluftdruck-per-app-messen/198221/)
- [Trailbot Trail Conditions](https://trailbot.com/)
