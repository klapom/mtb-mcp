# MTB Community Research — Smart Devices, APIs & Automation Ideas

Research compiled from mtb-news.de, emtb-news.de, Pinkbike, Vital MTB, Reddit r/MTB, and
general tech sources. Focus: ideas relevant to an MCP server for MTB ride planning & tracking.

---

## 1. GPS Computers & Bike Computers

### Existing Products

| Product | Key Features | Data / API Access |
|---------|-------------|-------------------|
| **Garmin Edge 540/840/1050** | MTB metrics (Grit, Flow, Jump detection), 5Hz GPS, Trailforks maps, incident detection | Garmin Connect IQ SDK (custom apps/data fields); Garmin Activity API ($5k one-time fee for approved business devs) |
| **Wahoo ELEMNT ACE / BOLT 3 / ROAM 3** | Android-based OS, customizable data fields, wind sensor (ACE), 3rd-party integrations | Wahoo Cloud API (OAuth2, `cloud-api.wahooligan.com`); integrates with Strava, Komoot, RideWithGPS, TrainingPeaks |
| **Hammerhead Karoo 3** | Full Android, web dashboard, AXS Web integration | Third-party data push to AXS Web, Strava auto-upload |

### MTB-Specific Garmin Metrics (Edge 540+)

- **Grit:** Terrain roughness score
- **Flow:** Smoothness of descent
- **Jump Count / Air Time / Hang Time:** Automatic jump detection
- **MTB Dynamics:** All logged in FIT files, accessible via Connect IQ

### Forum Sentiment (mtb-news.de)

- Strong demand for Wahoo↔Garmin data sync (FIT file incompatibilities discussed at length)
- Wahoo's Android-based OS seen as more hackable/open vs. Garmin's proprietary stack
- Community frustration with Garmin's $5,000 Activity API fee; Strava API praised as "the right way to do it"

### MCP Integration Opportunities

- Pull Garmin Connect data via unofficial `garmin-connect` npm package (no fee)
- Wahoo Cloud API is open and documented — potential MCP server candidate
- Connect IQ custom data fields could display MCP-served trail info on-device

---

## 2. Suspension Sensors & Telemetry

### Commercial Products

| Product | Sensors | Connectivity | Price |
|---------|---------|-------------|-------|
| **Quarq ShockWiz** | Air pressure in fork/shock → inferred travel | Bluetooth → iOS/Android app | ~€300 |
| **BYB Telemetry 2.0** | Fork + shock linear sensors, brake sensors, 3-axis accel/gyro, GPS, wheel speed | WiFi/USB → Windows/Mac software + mobile app | €1,749 |
| **Motion Instruments System 2** | Induction sensor (fork), magnetic rotary sensor (rear pivot) — non-wearing | Bluetooth → MotionIQ app (on-trail, offline) | ~€500–800 |
| **RockShox Flight Attendant** | Crank rotation sensor + fork/shock position → automatic damping | SRAM AXS Bluetooth → AXS app; integrates with power meters | Premium (~€2,500+ system) |
| **Fox Live Valve 1.5** | Terrain analysis 1,000×/sec, 3ms response | Fox app; proprietary | Premium |

### Open-Source / DIY Projects

| Project | Hardware | Software | Link |
|---------|---------|---------|------|
| **Sufni Suspension Telemetry (sst)** | Raspberry Pi Pico W + rotary encoders | Web UI, CSV import/export, spring rate / damping plots | [github.com/sghctoma/sst](https://github.com/sghctoma/sst) |
| **MTB-telemetry (Nathancrz)** | Arduino/ESP32 | Python data acquisition + analysis | [github.com/Nathancrz/MTB-telemetry](https://github.com/nathancrz/MTB-telemetry) |
| **Suspension-telemetry (porast1)** | ESP32 | MTB/dirtbike suspension logger | [github.com/porast1/suspension-telemetry](https://github.com/porast1/suspension-telemetry) |
| **Aalto DIY Suspension Wizard** | Arduino | University project, SD card logging | [Aalto University Wiki](https://wiki.aalto.fi/display/MEX/DIY+suspension+wizard) |

### Forum Discussions (Vital MTB, mtb-news.de)

- Active DIY telemetry threads on Vital MTB and mtb-news.de (`DIY Telemetrie / Data Acquisition System` thread)
- Riders want suspension data overlaid on GoPro footage (BYB supports this)
- ShockWiz described as "80% of BYB Telemetry at 20% of the cost" — sweet spot for most riders
- Motion Instruments praised for non-wearing sensor design and on-trail offline analysis

### MCP Integration Opportunities

- BYB and ShockWiz export CSV/ride files → potential ingest tool for suspension history
- Sufni's web UI accepts CSV — an MCP tool could format + upload suspension sessions
- Post-ride suspension report: "Your fork used 85% travel twice, rear only 60% — consider reducing front compression"

---

## 3. Tire Pressure Sensors (TPMS)

### Commercial Products

| Product | Protocol | Compatibility | Price |
|---------|---------|--------------|-------|
| **Quarq TyreWiz 2.0** | ANT+ + Bluetooth LE | Garmin Edge, SRAM AXS app, most head units | ~$120/pair |
| **Schrader AIRsistant** | Bluetooth LE | Garmin devices, iOS/Android app | ~€99.99/pair |

### Key Features

- Both mount on Presta valve, replace valve core
- Real-time pressure displayed on head unit or phone
- TyreWiz: integrates into SRAM AXS Web dashboard (pressure logged per ride alongside shifting data)
- AIRsistant: also monitors temperature; slow puncture detection
- TyreWiz LED indicator shows out-of-range pressure without needing phone/computer

### Forum Activity (mtb-news.de)

- Quarq TyreWiz covered in dedicated mtb-news.de article ("Echtzeit Reifendruck-Kontrollsystem")
- AIRsistant covered on emtb-news.de (Eurobike 2021 launch, follow-up articles)
- Community interest in optimal tubeless pressure by terrain type (gravel vs. roots vs. rocks)

### MCP Integration Opportunities

- SRAM AXS Web stores pressure data per ride — if AXS API ever opens, ingest pressure history
- MCP tool: recommend target pressure based on rider weight + trail surface type (OSM surface tags)
- "Your rear tire was at 1.8 bar on the rocky traverse — for your weight on that terrain, 1.6 bar is recommended"

---

## 4. Electronic Drivetrains & Dropper Posts

### SRAM AXS Ecosystem

SRAM AXS is the most data-rich MTB drivetrain platform currently available:

| Component | Data Tracked | Access |
|-----------|-------------|--------|
| Eagle AXS Derailleur | Shift count, gear distribution, time in each gear | SRAM AXS Web dashboard |
| Reverb AXS Dropper | Drop count, usage frequency | SRAM AXS Web |
| Quarq TyreWiz | Tire pressure per ride | SRAM AXS Web |
| Flight Attendant | Suspension mode switches, terrain adaptation | SRAM AXS app (no web export) |

AXS Web integrates data uploaded via Garmin, Wahoo, or Hammerhead head units.
No official public API documented — data visible in web dashboard only.

### Shimano Di2 / EP8

- E-Tube Project app: adjust assist levels, firmware update, monitor battery
- E-Tube Ride app: live ride data, ride history, Strava sync
- No public API; some reverse-engineering by the community

### MCP Integration Opportunities

- If SRAM opens AXS API: automatic drivetrain wear tracking (shift counts → chain wear alert)
- Di2 battery prediction: "At your typical ride intensity, you have ~2 rides of battery remaining"
- Dropper post usage pattern: "You dropped your post 47 times last ride — high-frequency trail"

---

## 5. eMTB Motor Systems

### App Ecosystem

| Motor Brand | App | Data Available | API Status |
|-------------|-----|---------------|------------|
| **Bosch Smart System** | eBike Flow | Assist modes, custom tuning (torque, acceleration, cutoff speed), range prediction | **Cloud API available** for manufacturer/dealer integration (`community.developer.bosch.com`) |
| **Shimano EP8 / Steps** | E-Tube Ride | Motor data, ride history, Strava sync | No public API; E-Tube API internal only |
| **Fazua Ride 60** | Fazua app | Activity tracking (added 2023), ANT+ + BT interfaces | ANT+ data stream accessible to head units |
| **Brose** | Brose app | Motor settings, firmware | No public API |
| **Specialized SL1.2 / Turbo** | Mission Control | Fine-grained motor tuning, range | No public API |

### Bosch Developer Portal

Bosch explicitly offers a Cloud API for manufacturers and dealers to build custom apps.
Community: `community.developer.bosch.com/t5/Bosch-eBike-Systems/ct-p/bosch_developers-ebike`

Key Bosch 2025 additions: Automatic gear shifting (Smart System integration with Di2/AXS), updated range prediction algorithm, enhanced theft protection.

### eMTB-News.de Forum Discussions

- Active threads comparing Bosch vs. Shimano vs. Fazua vs. Brose APIs/apps
- Rider demand for motor data in Strava activities (not just time/distance)
- Discussion of subscription models (Bosch's approach) — controversial
- Wish for "power budget" tool: predict remaining range based on route elevation profile

### MCP Integration Opportunities

- Bosch Cloud API: battery state + range prediction → "Can I complete this 1,200hm loop on one charge?"
- Route-range calculator: Komoot elevation profile + motor efficiency curves → range estimate
- Motor mode recommendation by trail type: "Technical descent ahead — switch to Eco for better modulation"

---

## 6. Smart Helmets

### Commercial Products

| Product | Smart Features | Crash Detection |
|---------|---------------|----------------|
| **ABUS MoDrop QUIN** | GPS location tracking, ride data | QUIN sensor: sends GPS coordinates + crash alert to emergency contacts |
| **Lumos Nyxel MIPS** | 360° integrated lights, auto brake light, turn signals | Quin crash detection (optional) |
| **UNIT 1 FARO / AURA MIPS** | Integrated LED lights, MIPS | Accelerometer-based crash detection → SOS timer → auto-alert |
| **POC Omne Eternal** | Solar-assisted battery for lights | No smart features |

### QUIN Technology (used by ABUS, Lumos, others)

- Sensors: accelerometer + GPS
- On crash: monitors impact location, peak G-force, rotational acceleration
- If rider doesn't respond to 60-second check-in → automatically alerts chosen contacts with GPS position
- SDK/API: not public, but QUIN is a platform play (licensing model for helmet brands)

### MCP Integration Opportunities

- Crash event webhook: if QUIN API ever opens → automatic emergency notification via WhatsApp/Signal
- Ride start/end detection from helmet → trigger automatic ride logging
- Helmet light status as proxy for "rider is on trail" → trail condition timestamp

---

## 7. Trail Condition Platforms

### Trailforks

- **API:** JSON API available upon application approval (not guaranteed)
  - URL: `trailforks.com/about/api/`
  - RSS feeds and embeddable widgets also available
- **Trail Reporting:** Riders report conditions after rides (mud, snow, downed trees, damage)
  - Reports filterable by trail, date, reporter
  - Builders/associations can mark issues as resolved
- **Service Tracker:** Component tracking with service interval reminders (time/distance/rides/date)
- **Community project:** [trail-conditions-map](https://github.com/tessapower/trail-conditions-map) — Austin MTB, combines Trailforks API + NWS weather API + scraping for real-time condition warnings

### MTB Project (REI)

- **API:** Public REST API at `mtbproject.com/data` (was free, status uncertain post-REI acquisition)
  - Returns trail list, details, photos, difficulty ratings, GPS coordinates
- **Data:** 39,000+ trails, 128,000+ miles worldwide, crowd-sourced
- **Widget:** Embeddable trail widgets (`mtbproject.com/widget`)

### Trailbot

- Service that automatically crossposts trail condition updates to Facebook and website embeds
- No API documented; scraping-based

### TrailAPI (RapidAPI)

- Third-party API aggregating trail data: `rapidapi.com/trailapi/api/trailapi`
- Returns trails by location with difficulty, length, summary

### MCP Integration Opportunities (already partially in project)

- Trailforks API (with approval): live condition reports → "Last report 3 hours ago: trail open, slightly damp"
- Weather + trail condition inference: DWD rain data (last 48h) + trail surface (OSM) → estimated dryness
- Automatic condition update after ride: MCP tool to submit Trailforks trail report post-activity

---

## 8. Bike Maintenance Tracking

### Apps With Integration Potential

| App | Strava Sync | API | Component Tracking |
|-----|------------|-----|-------------------|
| **mainTrack** | Yes | No public API | Distance, time, ride count per component |
| **ProBikeGarage** | Yes (auto daily) | No public API | Per-component distance across multiple bikes |
| **The Bike Mechanic** | Yes | No public API | Custom wear intervals; chain, cassette, tire, etc. |
| **Trailforks Service Tracker** | Indirect | Via Trailforks API | Service history log, interval reminders |

All major apps rely on Strava as the data backbone for ride distance — no direct sensor input.

### Community-Requested Features (mtbr.com, nsmb.com forums)

- Automatic chain wear alert based on ride hours (not just distance — relevant for wet/muddy conditions)
- Integration with component serial numbers for recall tracking
- Suspension service interval tracker (hours-based, not just distance)
- Brake bleed reminder based on modulation feel reports (subjective, but discussed)

### MCP Integration Opportunities

- Strava activity data → component wear calculator (Strava already in project)
- "Your chain has 850km since last replacement. Recommended interval: 1,000-1,500km for your terrain type."
- Fork service reminder: "Your Fox 36 has 90 hours of use. Lower leg service recommended at 100h."

---

## 9. Open-Source Projects & DIY Community

### Bike Computers / Data Loggers

| Project | Platform | Features | Link |
|---------|---------|---------|------|
| **pizero_bikecomputer** | Raspberry Pi Zero W | GPS, ANT+ sensors, offline maps, navigation | [github.com/hishizuka/pizero_bikecomputer](https://github.com/hishizuka/pizero_bikecomputer) |
| **bike-computer-32** | ESP32-C3 | OSM offline maps, GPX track rendering, GNSS | [github.com/lspr98/bike-computer-32](https://github.com/lspr98/bike-computer-32) |
| **stravaV10** | Custom hardware | Strava segments on-device, ANT+ sensors | [github.com/vincent290587/stravaV10](https://github.com/vincent290587/stravaV10) |
| **mountain-bike data logger** | Arduino | Hackster.io project — GPS + sensors | [hackster.io](https://www.hackster.io/NightRider2000/mountain-bike-data-logger-140447) |
| **OpenSourceEBike** | ESP32 | Full eMTB open-source electronics + software | [opensourceebike.github.io](https://opensourceebike.github.io/) |

### Trail & Routing Tools

| Project | Purpose | Link |
|---------|---------|------|
| **mtb-trail-finder** | ML-based trail recommendation by preference | [github.com/sgreylewis/mtb-trail-finder](https://github.com/sgreylewis/mtb-trail-finder) |
| **trail-conditions-map** | Trailforks + weather → real-time condition warnings | [github.com/tessapower/trail-conditions-map](https://github.com/tessapower/trail-conditions-map) |
| **OpenMTBMap** | OSM-based MTB maps for Garmin/Wahoo | [openmtbmap.org](https://openmtbmap.org/) |

### MCP Servers Already Existing for Cycling

| Server | Function | Link |
|--------|---------|------|
| **RideWithGPS MCP** | Natural language queries over RideWithGPS route library | Community project |
| **FirstCycling MCP** | Pro cycling data via MCP | Community project |
| **Strava MCP** | `@r-huijts/strava-mcp-server` — 25 tools | Already integrated in project |
| **VanMoof MCP** | E-bike status via MCP | [stefanstranger.github.io](https://stefanstranger.github.io/2025/04/25/VanMoofMCPServer/) |

---

## 10. Data Integration Landscape

### What Already Flows Together

```
Garmin/Wahoo/Hammerhead
    │
    ├─→ Strava (auto-upload via OAuth) ──→ Strava API (project: active)
    │       │
    │       └─→ mainTrack / ProBikeGarage (maintenance tracking via Strava)
    │
    ├─→ SRAM AXS Web (shifting + pressure data, no public API)
    │
    └─→ Garmin Connect (proprietary, $5k API)

Komoot ──────────────────────────────────→ Komoot API v007 (project: planned)

Trailforks ──────────────────────────────→ Trailforks API (by request)

Bosch eMTB ──────────────────────────────→ Bosch Cloud API (developer program)

OSM/Overpass ────────────────────────────→ Free, no auth (project: planned)
```

### Key Pain Points from Community

1. **No single data hub:** Suspension data (BYB/Motion Instruments), tire pressure (TyreWiz/AIRsistant), drivetrain (AXS), and ride data (Strava/Garmin) all live in separate silos.
2. **Garmin API is prohibitively expensive** for individual/hobby developers — unofficial `garmin-connect` npm package fills the gap.
3. **Komoot has no public API** — reverse-engineered v007 is widely used but technically unsupported.
4. **Trailforks API approval is not guaranteed** — community workaround: weather inference + crowdsourced reports.
5. **SRAM AXS data is trapped** in the web dashboard — no export, no API.

---

## 11. Automation Ideas from Community

These ideas appeared repeatedly in forum discussions and GitHub projects:

### Ride Planning Automation

- **Weekend ride suggester:** Friday evening: check weather forecast → search matching Komoot tours → send GPX to phone/Garmin
- **Rain window detector:** DWD radar + ride duration → "You have a 90-minute dry window starting at 14:00"
- **Trail condition scorer:** Last 72h rainfall (DWD) + trail surface (OSM) → dryness estimate per trail
- **Route optimizer:** Combine Strava heatmap (popular = well-maintained) + OSM difficulty tags + elevation profile

### Ride Logging Automation

- **Automatic activity tagging:** Strava upload → detect trail names from GPS trace against OSM/Trailforks → auto-tag ride with trail names
- **Jump detection summary:** Garmin Jump metrics from FIT file → "Today: 12 jumps, max 1.8s hang time, new PR on drop at Hetzlas"
- **Segment comparison:** "You were 8 seconds slower than your best on the S2 descent — headwind or technique?"

### Maintenance Automation

- **Proactive service alerts:** Strava distance + component service intervals → WhatsApp alert "Fork service due in ~2 rides"
- **Weather-based wear acceleration:** Muddy rides count double toward chain wear
- **Tubeless sealant reminder:** Date-based (sealant dries in ~6 months) + distance

### Safety Automation

- **Ride buddy notification:** Garmin LiveTrack / Strava Beacon → MCP bridge → WhatsApp "Rider has started a 3h tour, last position: [map link]"
- **Crash detection alert:** QUIN-equipped helmet → if API available → emergency contact via WhatsApp
- **No-return alert:** Scheduled check: if no Strava activity upload by expected return time → alert

### eMTB Specific

- **Range planner:** Bosch Cloud API battery state + Komoot elevation profile → "This 1,400hm route will use ~85% battery. Charge first."
- **Motor mode advisor:** Upcoming trail segment steepness (from GPX) → recommended assist mode
- **Battery history:** Track degradation over charge cycles (Bosch API includes cycle count)

---

## 12. Products Worth Deeper Investigation for MCP Integration

| Product/API | Priority | Reason | Status |
|-------------|---------|--------|--------|
| **Bosch eBike Cloud API** | High | Official developer program, eMTB-specific data | Available, needs application |
| **Trailforks API** | High | Trail condition reports — core use case | Available on request |
| **Wahoo Fitness API** | Medium | Open OAuth2 API, large user base | Documented, open |
| **MTB Project API** | Medium | 39k trails, public REST API | Free (verify status) |
| **SRAM AXS Web** | Low | No public API, dashboard only | Watch for changes |
| **Garmin Connect IQ** | Medium | Custom data fields on device, ANT+ sensor access | SDK free, Activity API expensive |
| **Motion Instruments MotionIQ** | Low | Suspension data, offline app only | No API |
| **Quarq TyreWiz** | Low | ANT+ data accessible on head unit, no cloud API | Head unit data only |

---

## Sources

- [MTB-News.de — Elektronik rund ums Bike Forum](https://www.mtb-news.de/forum/f/elektronik-rund-ums-bike.92/)
- [MTB-News.de — Wahoo ELEMNT Ace Test](https://www.mtb-news.de/forum/t/wahoo-elemnt-ace-im-ersten-test-der-neue-koenig-der-gps-radcomputer.993136/page-3)
- [MTB-News.de — Quarq TyreWiz](https://www.mtb-news.de/news/quarq-tyrewiz-echtzeit-reifendruck-kontrollsystem-mountainbike/)
- [MTB-News.de — BYB Telemetry v2.0](https://www.mtb-news.de/news/byb-telemetry-v2-0-infos-preise/)
- [MTB-News.de — DIY Telemetrie Forum](https://www.mtb-news.de/forum/t/diy-telemetrie-data-acquisition-system.971652/page-2)
- [eMTB-News.de — E-Bike Apps Bosch Shimano Specialized](https://www.emtb-news.de/news/e-bike-app-bosch-shimano-specialized/)
- [eMTB-News.de — AIRsistant TPMS](https://www.emtb-news.de/news/schrader-airsistant/)
- [Pinkbike — BYB Telemetry 2.0 Review](https://www.pinkbike.com/news/review-byb-telemetry-2-mtb-data-acquisition.html)
- [Pinkbike — SRAM AXS Web Tool](https://www.pinkbike.com/news/sram-axs-web-tool-tracks-your-shifting-and-dropper-post-usage.html)
- [Vital MTB — DIY Suspension Telemetry Forum](https://www.vitalmtb.com/forums/The-Hub,2/DIY-mtb-telemetry-data,11126)
- [GitHub — Sufni Suspension Telemetry](https://github.com/sghctoma/sst)
- [GitHub — Trail Conditions Map](https://github.com/tessapower/trail-conditions-map)
- [Trailforks API](https://www.trailforks.com/about/api/)
- [MTB Project API](https://www.mtbproject.com/data)
- [Bosch eBike Developer Portal](https://community.developer.bosch.com/t5/Bosch-eBike-Systems/ct-p/bosch_developers-ebike)
- [Wahoo Fitness API](https://cloud-api.wahooligan.com/)
- [Garmin Connect IQ SDK](https://developer.garmin.com/connect-iq/)
- [SRAM AXS Integrations](https://www.sram.com/en/learn/axs-integrations)
- [Motion Instruments System 2](https://motioninstruments.com/products/system-2)
- [Quarq TyreWiz](https://www.sram.com/en/quarq/series/tyrewiz)
- [ABUS MoDrop QUIN Review](https://bikerumor.com/review-abus-modrop-quin-smart-mtb-helmet-crash-notifications/)
- [DC Rainmaker — Wahoo ELEMNT Ace Review](https://www.dcrainmaker.com/2024/12/wahoo-elemnt-ace-in-depth-review-bike-computer.html)
- [Movcan — Next-Gen MTB Tech 2025](https://movcan-bike.com/blogs/blog/next-generation-mtb-tech-revolutionizing-trails-in-2025)
- [E-MOUNTAINBIKE Magazine — Bosch Smart System 2025](https://ebike-mtb.com/en/bosch-smart-system-news-2025/)
- [RideWithGPS MCP Server](https://skywork.ai/skypage/en/cycling-data-ai-engineer/1981296737417207808)
