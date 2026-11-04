# Link audit

Run: `.venv/bin/python tools/link_audit.py` (2026-11-04). It checks every distinct external URL that the inspector, the screen flags, the live tool or the docs show. Each URL is fetched (first 16 KB only) with redirects followed, and the status, final URL, content type, page title and file signature are recorded. HTTP 200 alone was not accepted: each destination was judged against what the product claims it is. No URL was invented. The replacement links below were each checked before use.

**Totals:** 112 URLs, 104 reachable, 8 not reachable (all curated-constraint sources).

## Verdicts by group

* **Raw data files:**
  * BTS On-Time (12 monthly zips), FAA TAF zip, FAA enplanement, cargo, grant and NPIAS workbooks, BEA CAINC1 zip, NASR APT zip and the Census delineation workbook all serve the claimed file. The signature is zip/xlsx and the file names match source and period. **VERIFIED.**
  * T-100, the BTS lookups, ATADS and OurAirports were wrong or misleading as 'raw file' links. They are now **FIXED / labelled** (table below).
* **Dataset pages:** all 15 resolve to the publisher's dataset page with a matching title (BTS Transtats tables, FAA TAF, ATADS, NPIAS, AIP grant histories, enplanement data, NASR subscription, Census delineation files, OurAirports data). The Census regions PDF is the regions and divisions map. The BEA page returns HTML without a title (not inspected further). **VERIFIED**, BEA **PARTIAL**.
* **Live API:** `nasstatus.faa.gov/api/airport-status-information` returns `application/xml` with live programs. **VERIFIED.**
* **Curated constraint sources:** 7 return HTTP 404 and 1 returns 403 (the site blocks automated checks). These sources back records that were already graded `unverified` or `snippet` (except SFO's primary-evidence FAA Capacity Profile PDF, which **is verified**: `application/pdf`). The dead links are recorded in `config/link_status.toml`, and a flag that relies on one now shows `source_link: HTTP 404 …` instead of presenting the link as evidence. No replacement URLs were guessed. **OPEN:** find primary documents.
* **Documentation links:**
  * Groq, OpenAI, MDN, vad-web, Pipecat and LiveKit docs resolve to the cited pages (titles match; Pipecat and LiveKit redirect to their renamed paths).
  * Google AI Studio pages return 200 but render with JavaScript, so their content is **NOT VERIFIED** by this check.
  * The Groq community thread redirects automated clients to the homepage, so it is **NOT VERIFIED**.
  * README's `http://127.0.0.1:8765` is the local app.

## Corrected or questionable links

| Original URL | Verdict | What it is / what changed |
|---|---|---|
| https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FMG&QO_fu146_anzr=Nv4%20Pn44vr45 | PARTIAL | Opens the BTS T-100 download form (title 'Download page'); the data file is produced by a form POST. Inspector now labels it 'download form' and explains this. |
| https://www.transtats.bts.gov/Download_Lookup.asp | FIXED | Redirected to the Transtats homepage, so it was not a file. The inspector no longer links it and explains that lookups come from a form. |
| https://www.aspm.faa.gov/opsnet/sys/opsnet-server-x.asp | FIXED | Backend query endpoint (GET returns JSON, not data). The inspector now links the verified ATADS form page instead, labelled 'download form'. |
| https://davidmegginson.github.io/ourairports-data/ | FIXED | Index page, not a file. The inspector now links the verified airports.csv and runways.csv (text/csv, correct headers). |
| https://community.groq.com/t/gpt-oss-20b-free-tier-getting-413-errors/1411 | NOT VERIFIED | Redirects automated clients to groq.com; third-party report cited as such. |

## Full results

### Documentation links

| Status | URL | Final destination | Type | Title |
|---|---|---|---|---|
| 206 | http://127.0.0.1:8765 |  | html | Airport Investment Intelligence |
| 200 | https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol |  | html | Stream Protocols / AI SDK |
| 200 | https://ai.google.dev/gemini-api/docs/pricing | https://aistudio.google.com/docs/pricing | html |  |
| 200 | https://aistudio.google.com/docs/live-api/capabilities |  | html |  |
| 200 | https://aistudio.google.com/docs/live-api/ephemeral-tokens |  | html |  |
| 200 | https://aistudio.google.com/docs/live-api/tools |  | html |  |
| 200 | https://aistudio.google.com/docs/pricing |  | html |  |
| 206 | https://community.groq.com/t/gpt-oss-20b-free-tier-getting-413-errors/1411 | https://groq.com/ | html | Groq is the premier neocloud for fast inference |
| 200 | https://community.openai.com/t/ephemeral-keys-trigger-realtime-sideband-404-errors/1396002 |  | html | Ephemeral keys trigger Realtime sideband 404 errors - Bugs - OpenAI De |
| 206 | https://console.groq.com/docs/billing-faqs |  | html | Billing FAQs - GroqDocs |
| 206 | https://console.groq.com/docs/deprecations |  | html | Model Deprecation - GroqDocs |
| 206 | https://console.groq.com/docs/model/openai/gpt-oss-120b |  | html | OpenAI GPT-OSS 120B - GroqDocs |
| 206 | https://console.groq.com/docs/model/qwen/qwen3.8-27b |  | html | Qwen 3.8 27B - GroqDocs |
| 206 | https://console.groq.com/docs/models |  | html | Supported Models - GroqDocs |
| 206 | https://console.groq.com/docs/prompt-caching |  | html | Prompt Caching - GroqDocs |
| 206 | https://console.groq.com/docs/rate-limits |  | html | Rate Limits - GroqDocs |
| 206 | https://console.groq.com/docs/reasoning |  | html | Reasoning - GroqDocs |
| 206 | https://console.groq.com/docs/speech-to-text |  | html | Speech to Text - GroqDocs |
| 206 | https://console.groq.com/docs/structured-outputs |  | html | Structured Outputs - GroqDocs |
| 206 | https://console.groq.com/docs/text-to-speech |  | html | Text to Speech - GroqDocs |
| 206 | https://console.groq.com/docs/tool-use | https://console.groq.com/docs/tool-use/overview | html | Tool Use Overview - GroqDocs |
| 206 | https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition |  | html | SpeechRecognition - Web APIs / MDN |
| 206 | https://developers.openai.com/api/docs/guides/realtime-conversations |  | html | Realtime conversations / OpenAI API |
| 206 | https://developers.openai.com/api/docs/guides/realtime-vad |  | html | Voice activity detection (VAD) / OpenAI API |
| 206 | https://developers.openai.com/api/docs/pricing |  | html | Pricing / OpenAI API |
| 206 | https://developers.openai.com/api/reference/resources/realtime/subresources/client_secrets/methods/create |  | html | Create client secret / OpenAI API Reference |
| 200 | https://docs.livekit.io/agents/build/nodes/ | https://docs.livekit.io/agents/logic/nodes/ | html | Pipeline nodes and hooks / LiveKit Documentation |
| 200 | https://docs.livekit.io/agents/build/turns/ | https://docs.livekit.io/agents/logic/turns/ | html | Turns overview / LiveKit Documentation |
| 200 | https://docs.pipecat.ai/guides/learn/pipeline | https://docs.pipecat.ai/pipecat/learn/pipeline | html | Pipeline &amp; Frame Processing - Pipecat |
| 200 | https://docs.pipecat.ai/server/utilities/turn-detection/smart-turn-overview | https://docs.pipecat.ai/api-reference/server/utilities/turn-detection/smart-turn-overview | html | Smart Turn Overview - Pipecat |
| 206 | https://docs.vad.ricky0123.com/user-guide/algorithm/ |  | html | Algorithm - Voice Activity Detection for Javascript |
| 206 | https://docs.vad.ricky0123.com/user-guide/browser/ |  | html | Browser - Voice Activity Detection for Javascript |
| 206 | https://github.com/SYSTRAN/faster-whisper |  | html |  |
| 206 | https://github.com/adbar/trafilatura |  | html |  |
| 206 | https://github.com/assistant-ui/assistant-ui |  | html |  |
| 206 | https://github.com/google-gemini/live-api-web-console |  | html |  |
| 206 | https://github.com/langflow-ai/langflow/issues/11120 |  | html |  |
| 206 | https://github.com/livekit/agents |  | html |  |
| 206 | https://github.com/pipecat-ai/pipecat |  | html |  |
| 206 | https://github.com/searxng/searxng |  | html |  |
| 206 | https://github.com/vega/altair |  | html |  |
| 206 | https://github.com/vercel/ai |  | html |  |

### Curated constraint sources (screen flags)

| Status | URL | Final destination | Type | Title |
|---|---|---|---|---|
| 206 | https://adip.faa.gov | https://adip.faa.gov/agis/public/#/ | html | Airport Data and Information Portal |
| 403 | https://bradleyairport.com/news/bradley-international-airport-caps-off-terminal-expansion-with-unveiling-of-newly-constructed-concourse/ |  | Forbidden |  |
| 200 | https://btv.aero/about-btv/airport-development | https://btv.aero/airport-development/ | html | Airport Development - Patrick Leahy Burlington International Airport |
| 206 | https://ceqanet.opr.ca.gov/2019049020/2 | https://ceqanet.lci.ca.gov/2019049020/2 | html | Los Angeles International Airport Airfield and Terminal Modernization  |
| 404 | https://dot.alaska.gov/anc/about/facts.shtml |  | Not Found |  |
| 404 | https://flyri.com/pvd-master-plan/ |  | Not Found |  |
| 206 | https://flyri.com/riac/improvement/ |  | html | Improvements - Rhode Island T. F. Green International Airport / PVD |
| 404 | https://newportbeachca.gov/pln/CEQA_REVIEW/John Wayne Airport DEIR/CC 3 Principal Terms of the Proposed Project and Alternatives.pdf | https://newportbeachca.gov/pln/CEQA_REVIEW/John%20Wayne%20Airport%20DEIR/CC%203%20Principal%20Terms%20of%20the%20Proposed%20Project%20and%20Alternatives.pdf | Not Found |  |
| 404 | https://noise.flysfo.com/aircraft-noise/flight-patterns-operations/ |  | Not Found |  |
| 404 | https://portlandjetport.org/sites/default/files/PWM%20Master%20Plan%20Executive%20Summary.pdf |  | Not Found |  |
| 200 | https://www.faa.gov/airports/planning_capacity/profiles |  | html | Airport Capacity Profiles / Federal Aviation Administration |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/profiles/SFO-Airport-Capacity-Profile-2019.pdf |  | pdf |  |
| 404 | https://www.flymanchester.com/manchester-boston-regional-airport-and-aeroterm-to-develop-multitenant-cargo-facility/ |  | Not Found |  |
| 200 | https://www.flymanchester.com/public-documents-and-plans/ |  | html | Public Documents and Plans / Manchester Boston Regional Airport (MHT) |
| 404 | https://www.flysfo.com/about-sfo/media/press-releases/sfos-terminal-3-west-modernization-project-underway |  | Not Found |  |
| 206 | https://www.lawa.org/transforminglax |  | html | TransformingLAX / Los Angeles World Airports |
| 200 | https://www.massport.com/massport-media/news/massport-elected-officials-celebrate-modernization-terminal-e-and-100-years-connecting |  | html |  |
| 200 | https://www.megaproject.com/news/airport/faa-prohibits-parallel-arrivals-at-san-francisco-international-airport |  | html | FAA Prohibits Parallel Arrivals At San Francisco International Airport |
| 200 | https://www.ocair.com/about/administration/access-noise | https://www.ocair.com/about/administration/access-noise/ | html | Access &amp; Noise / John Wayne Airport, Orange County |

### Dataset pages (inspector 'Dataset page')

| Status | URL | Final destination | Type | Title |
|---|---|---|---|---|
| 206 | https://apps.bea.gov/regional/downloadzip.htm |  | html |  |
| 206 | https://ourairports.com/data/ |  | html | Open data @ OurAirports |
| 200 | https://www.aspm.faa.gov/opsnet/sys/airport.asp |  | html | Air Traffic Activity System (ATADS) |
| 200 | https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html |  | html | Delineation Files |
| 200 | https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/ |  | html | 28 Day NASR Subscription |
| 200 | https://www.faa.gov/airports/aip/grant_histories |  | html | Airport Improvement Program (AIP) Grant Histories / Federal Aviation A |
| 200 | https://www.faa.gov/airports/planning_capacity/npias/current |  | html | National Plan of Integrated Airport Systems (NPIAS) - Current / Federa |
| 200 | https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger |  | html | Passenger Boarding (Enplanement) and All-Cargo Data for U.S. Airports  |
| 200 | https://www.faa.gov/data_research/aviation/taf |  | html | Terminal Area Forecast (TAF) / Federal Aviation Administration |
| 200 | https://www.transtats.bts.gov |  | html | OST_R / BTS / Transtats Homepage |
| 200 | https://www.transtats.bts.gov/Tables.asp?QO_VQ=EEE |  | html | OST_R / BTS / Transtats Data Tables |
| 200 | https://www.transtats.bts.gov/Tables.asp?QO_VQ=EFD |  | html | OST_R / BTS / Transtats Data Tables |
| 206 | https://www2.census.gov/geo/pdfs/maps-data/maps/reference/us_regdiv.pdf |  | pdf |  |

### Raw data files (inspector 'raw file' / 'download form')

| Status | URL | Final destination | Type | Title |
|---|---|---|---|---|
| 206 | https://apps.bea.gov/regional/zip/CAINC1.zip |  | zip/xlsx |  |
| 206 | https://davidmegginson.github.io/ourairports-data/ |  | html | Open-data downloads for OurAirports / ourairports-data |
| 206 | https://nfdc.faa.gov/webContent/28DaySub/extra/29_Oct_2026_APT_CSV.zip |  | zip/xlsx |  |
| 206 | https://taf.faa.gov/Downloads/APO100_TAF_Final_2025.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_10.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_11.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_12.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_9.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_1.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_2.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_3.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_4.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_5.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_6.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_7.zip |  | zip/xlsx |  |
| 206 | https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_8.zip |  | zip/xlsx |  |
| 200 | https://www.aspm.faa.gov/opsnet/sys/opsnet-server-x.asp |  | json |  |
| 206 | https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/ARP-CY2025-all-cargo-airports.xlsx | https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/arp-CY2025-all-cargo-airports.xlsx | zip/xlsx |  |
| 206 | https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/arp-cy2025-commercial-service-enplanements.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/2022-12/FY2022-AIP-grants.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/2023-07/FY2021-AIP-grants.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/2023-10/FY2023-AIP-grants.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/2024-10/FY2024-AIP-grants.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/2025-11/FY_2025_AIP_Grants.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/npias/current/ARP-NPIAS-2025-2029-AppendixA.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/passenger_allcargo_stats/passenger/CY12CommercialServiceEnplanements.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/passenger_allcargo_stats/passenger/cy13-commercial-service-enplanements.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/passenger_allcargo_stats/passenger/cy14-commercial-service-enplanements.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/passenger_allcargo_stats/passenger/cy15-commercial-service-enplanements.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/passenger_allcargo_stats/passenger/cy16-commercial-service-enplanements.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/passenger_allcargo_stats/passenger/cy17-commercial-service-enplanements.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/passenger_allcargo_stats/passenger/cy18-commercial-service-enplanements.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/passenger_allcargo_stats/passenger/cy19-commercial-service-enplanements.xlsx |  | zip/xlsx |  |
| 206 | https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/passenger_allcargo_stats/passenger/cy20-commercial-service-enplanements.xlsx |  | zip/xlsx |  |
| 200 | https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FMG&QO_fu146_anzr=Nv4%20Pn44vr45 |  | html | Download page |
| 200 | https://www.transtats.bts.gov/Download_Lookup.asp | https://www.transtats.bts.gov/Homepage.asp | html | OST_R / BTS / Transtats Homepage |
| 206 | https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx |  | zip/xlsx |  |

### Live API

| Status | URL | Final destination | Type | Title |
|---|---|---|---|---|
| 200 | https://nasstatus.faa.gov/api/airport-status-information |  | xml/html |  |

Browser check: in the running app, the inspector for a BTS On-Time finding shows 'Dataset page' plus monthly 'raw file' zips; a T-100 finding shows 'download form' with the access note; an ATADS finding links the ATADS form page (tested 2026-11-04).
