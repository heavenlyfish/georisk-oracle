# GeoRisk Oracle — Product Roadmap & Vision
**Last updated**: 2026-05-28
**Current state**: MVP / POC submitted to NVIDIA Build-a-Claw Hackathon

---

## Current State (What We Have)

- ✅ 3-model NIM pipeline: Llama screens → Nemotron reasons → NeMo Guardrails validates
- ✅ Auto-scan every 30 min via NewsAPI (single source)
- ✅ Risk score 0–100 with urgency levels
- ✅ Supply chain breakdown by category (rare earth, advanced semi, energy, etc.)
- ✅ Telegram alert when score ≥ 60
- ✅ Live dashboard on Railway (24/7, no laptop needed)
- ✅ Firebase Firestore persistence
- ❌ Single news source (NewsAPI only)
- ❌ No cross-source signal amplification
- ❌ No hierarchical supply chain propagation model
- ❌ No consumer product impact tracing
- ❌ OpenClaw not integrated (was the hackathon's core concept)

---

## Ultimate Vision

> **GeoRisk Oracle should be a 24/7 autonomous intelligence layer that surfaces only what matters — before it hits mainstream financial media.**

The key insight: **importance is a function of two signals**:

### Signal 1 — Cross-Source Confirmation
The same piece of news covered by **multiple distinct, independent sources** is more significant than a single outlet's report.
- Reuters + FT + Bloomberg all report the same Strait of Hormuz incident → HIGH confidence
- One blog post → ignore
- Implementation: deduplicate by semantic similarity, count distinct source domains, weight by source credibility tier

### Signal 2 — Supply Chain Hierarchy Propagation
Events at the **top of a supply chain** have outsized downstream effects that take weeks/months to reach consumer products.
The system must model the propagation path, not just the event itself.

---

## Real-World Examples (Design Reference Cases)

### Case 1 — Ukraine/Russia War → Global Energy Crisis
```
War in Ukraine
    → Russia sanctions / pipeline disruption
    → European natural gas shortage
    → Energy prices surge across EU
    → Industry shutdowns (fertilizer plants, aluminum smelters)
    → Food production costs rise (fertilizer shortage)
    → Consumer food prices inflate globally
    → EU accelerates renewable energy transition
    → Demand drop for Russian coal/oil → Russia revenue squeeze

Supply chain layers:
  Layer 1 (immediate):  Energy — oil, LNG, pipeline gas
  Layer 2 (weeks):      Fertilizers — urea, ammonia (energy-intensive to produce)
  Layer 3 (months):     Agriculture — wheat, corn (input cost rise)
  Layer 4 (quarters):   Food prices — consumer basket inflation
  Layer 5 (years):      EU energy policy shift — solar, wind, nuclear buildout
```

### Case 2 — US-Iran Conflict → Qatar → Urea/Nitrogen Fertilizer
```
US-Iran military escalation
    → Strait of Hormuz threat
    → Qatar (卡達) operations disrupted
    → LNG exports from Qatar impacted
    → Qatar also major urea (尿素) / nitrogen fertilizer (氮肥) exporter
    → Global fertilizer supply shock
    → Agricultural input costs rise
    → Food production squeeze in import-dependent nations (SE Asia, Africa)
    → Consumer food price inflation in emerging markets

Key propagation nodes:
  Energy conflict → LNG → fertilizer production → agriculture → food prices
```

**This is the pattern GeoRisk Oracle must learn to model automatically.**

---

## Next Development Priorities

### Priority 1 — Multi-Source Intelligence (Weekend Sprint)
**Problem**: Currently only uses NewsAPI (single aggregator, limited sources)

**Solution**: Integrate multiple distinct source tiers

| Tier | Sources | Method |
|---|---|---|
| Tier 1 (wire services) | Reuters, AP, AFP | RSS feeds |
| Tier 2 (financial) | FT, Bloomberg, WSJ | RSS / scrape |
| Tier 3 (geopolitical) | Foreign Policy, The Diplomat, CSIS | RSS |
| Tier 4 (commodities) | Platts, Argus, Fastmarkets | RSS / API |
| Tier 5 (social signal) | Twitter/X key accounts | API |

**Cross-source scoring**:
```python
importance_score = base_risk_score * source_count_multiplier * credibility_weight
# 3+ independent sources on same event → multiply risk score by 1.5x
```

### Priority 2 — Supply Chain Propagation Graph
**Problem**: Currently identifies affected sectors but doesn't model downstream propagation

**Solution**: Build a supply chain graph where Nemotron traces the full cascade

```
Event node
    → Tier 1 impact (direct commodity/region)
    → Tier 2 impact (industries dependent on Tier 1)
    → Tier 3 impact (consumer products from Tier 2)
    → Estimated time lag per tier
    → Confidence decay per tier (further = less certain)
```

Example propagation chains to hardcode as reference:
- Energy → Fertilizer → Agriculture → Food prices
- Semiconductor materials → Advanced chips → Consumer electronics/EVs
- Shipping disruption → Import costs → Retail inflation
- Rare earth → EV batteries → Automotive → Consumer vehicle prices

### Priority 3 — OpenClaw Integration (The Real Build-a-Claw Goal)
**Problem**: Watch daemon is a hardcoded loop, not a true autonomous agent

**Solution**: Replace hardcoded loop with OpenClaw agent powered by Nemotron

```
NemoClaw (security sandbox on Oracle Cloud VM)
    └── OpenClaw (autonomous agent)
            ├── tool: search_news(query, sources)
            ├── tool: analyze_event(text) → RiskAssessment
            ├── tool: check_cross_source(event) → confirmation_count
            ├── tool: trace_supply_chain(event) → PropagationGraph
            ├── tool: send_alert(assessment)
            └── tool: update_dashboard(data)

OpenClaw decides:
  - WHEN to search (triggered by news volume spikes)
  - WHAT to search (based on watchlist + emerging signals)
  - WHETHER an event warrants deep analysis
  - HOW to prioritize multiple concurrent events
```

**Oracle Cloud VM** (already set up, pending capacity):
- Stack: `georisk-openclaw-stack` in Oracle Resource Manager
- Shape: VM.Standard.A1.Flex, 4 OCPU, 24GB, Oracle Linux 9
- Region: Tokyo (ap-tokyo-1), VCN: georisk-vcn, Subnet: georisk-subnet
- Keep retrying — capacity opens up randomly

### Priority 4 — Importance Ranking Algorithm
**Problem**: All events treated equally regardless of how many sources report it

**Solution**: Event importance = f(source_count, source_tier, supply_chain_level, time_decay)

```python
def importance_score(event):
    base = nemotron_risk_score(event)
    source_boost = log(1 + distinct_source_count) * avg_source_credibility
    hierarchy_boost = supply_chain_tier_weight  # Tier 1 events amplify more
    recency = time_decay_factor(event.published_at)
    return min(100, base * source_boost * hierarchy_boost * recency)
```

Only events above `IMPORTANCE_THRESHOLD` (default: 70) trigger deep Nemotron analysis + alert.

### Priority 5 — Semantic Deduplication
**Problem**: Same event reported by 10 sources = 10 separate analyses

**Solution**: 
1. Cluster incoming headlines by semantic similarity (embeddings)
2. Merge into single "event cluster" with source_count metadata
3. Run ONE Nemotron analysis on the merged event
4. Surface source_count as a signal of importance

Use: `nvidia/llama-nemotron-embed-1b-v2` (available on NIM, free) for embeddings.

### Priority 6 — User-Configurable Watchlist
**Problem**: Watchlist is hardcoded in `data/watchlist.json`

**Solution**: Dashboard UI to add/remove:
- Watchlist keywords
- Countries/regions of interest
- Specific companies to track
- Alert threshold per category

---

## Architecture Target (6-Month Vision)

```
Multiple News Sources (RSS + APIs)
        ↓
[Source Aggregator] — deduplicate, tier-weight, cluster by topic
        ↓
[Importance Filter] — cross-source confirmation score
        ↓ (high importance only)
[OpenClaw Agent] — powered by Nemotron via NIM, sandboxed by NemoClaw
        ├── [Supply Chain Propagation Tracer]
        ├── [Cross-Source Verifier]
        └── [Risk Scorer]
        ↓
[NeMo Guardrails] — policy validation
        ↓
[Alert Engine] — Telegram + dashboard
        ↓
[Firebase Firestore] — persistence
        ↓
[Dashboard] — event feed, propagation graph, pattern analysis, 2-week outlook
```

---

## Notes on Key Supply Chain Nodes to Model

| Event Type | Key Propagation Path |
|---|---|
| Middle East conflict | Energy → Fertilizer → Agriculture → Food |
| Taiwan Strait crisis | Advanced Semi → Consumer electronics, EVs, defense |
| Ukraine/Russia war | Energy + Wheat → EU inflation + food security |
| China rare earth ban | Rare earth → EV batteries + semiconductors + defense |
| Red Sea/Hormuz blockade | Shipping → all import-dependent supply chains |
| Iran sanctions | Oil + LNG + Urea → Energy + fertilizer + food |

---

## Reminder: Before Next Session
- [ ] Rotate all API keys (NIM, Firebase, Telegram) — see PRE_SUBMISSION.md
- [ ] Retry Oracle Cloud stack: Resource Manager → georisk-openclaw-stack → Apply
- [ ] Install NemoClaw on Oracle VM once it's up
- [ ] NewsAPI free tier = 100 req/day — upgrade or find alternative for multi-source
