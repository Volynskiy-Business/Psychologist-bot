# Speech-to-Text Provider Evaluation & Strategy

**Document Type**: Technical Architecture Decision
**Last Updated**: 2026-05-23
**Status**: Active

## Overview

This document captures strategic decisions and evaluations regarding Speech-to-Text (STT) provider selection for PsySupport AI, including self-hosted vs. cloud solutions, language support, and cost-benefit analysis.

---

## Key Findings

### Problem Statement

PsySupport AI requires:
1. Reliable voice transcription for Russian conversations
2. Potential future support for Hebrew and multiple languages
3. Cost-effective operation on limited VPS infrastructure
4. High-quality transcription for emotional/psychological support context

### Critical Discovery: Language Support Matrix

Different STT solutions have vastly different language coverage and specialization:

| Provider | Languages | Hebrew | Russian | Cost | Speed | GPU Required |
|----------|-----------|--------|---------|------|-------|--------------|
| **Whisper tiny** | 99+ | ✅ | ✅ Good | $5–10/mo | Slow | No |
| **Whisper base** | 99+ | ✅ | ✅ Good | $15–25/mo | Very Slow | No |
| **Silero STT** | 3–4 | ❌ | ✅ Excellent | $10–15/mo | Fast | No |
| **Vosk** | 10+ | ❌ | ✅ Good | $3–5/mo | Slow | No |
| **Deepgram Cloud** | 60+ | ✅ | ✅ Good | API-based | Real-time | N/A |

---

## Strategic Recommendations

### Recommendation 1: Silero STT for Russian-Only Deployments

**Best For**: Pure Russian language support with no international expansion planned

**Advantages**:
- Specifically optimized for Russian language
- Excellent transcription quality for Russian
- Fast processing on minimal resources
- Runs on $10–15/mo VPS without GPU
- Open-source, no API costs

**Infrastructure**:
```
VPS Specs: 2–4 GB RAM, 2 CPU, no GPU
Monthly Cost: $10–15
Initial Setup: Easy (Python SDK available)
```

**Implementation Path**:
1. Deploy on self-hosted VPS
2. Replace Deepgram fallback with local Silero instance
3. Monitor performance and cost savings

---

### Recommendation 2: Whisper tiny for Multilingual Support

**Best For**: Russian + Hebrew + other languages; future-proof architecture

**Advantages**:
- 99+ languages in single model (Russian, Hebrew, English, French, Chinese, etc.)
- Universal approach — no model switching needed
- Better long-term scalability
- Good quality across all supported languages
- Comparable cost to Silero

**Trade-offs**:
- Slower inference (5–15 min per min of audio on CPU)
- Larger model (~39 MB)
- More CPU/RAM overhead

**Infrastructure**:
```
VPS Specs: 2–4 GB RAM, 2 CPU, no GPU needed
Monthly Cost: $5–10 (CPU-friendly)
Initial Setup: Simple (Python package)
```

**When Speed Becomes Critical**:
- If real-time or near-real-time transcription required
- Consider upgrade to Whisper base (~2–3x slower, better quality)
- GPU deployment would be needed for faster inference ($50–100+/mo)

---

### Recommendation 3: Deepgram (Current Solution) — Hybrid Fallback

**When to Keep**:
- Peak demand periods requiring guaranteed low-latency
- As paid fallback for self-hosted STT reliability
- Trial phase before full self-hosted commitment

**Cost Management**:
- Deepgram has free tier (~$0 startup)
- Pay-as-you-go for production ($5–50/mo depending on usage)

---

## Cost-Benefit Analysis: Self-Hosted vs. Cloud

### Scenario 1: Russian-Only + Silero STT

```
Setup Cost: $0 (open-source)
Monthly VPS: $10–15
Annual Cost: $120–180
Break-even: Immediate (vs. Deepgram pay-per-use)
Quality: Excellent for Russian
Latency: Acceptable (non-real-time is OK for bot)
```

### Scenario 2: Multilingual + Whisper tiny

```
Setup Cost: $0 (open-source)
Monthly VPS: $5–10
Annual Cost: $60–120
Break-even: Immediate
Quality: Good across 99+ languages
Latency: Slower (~5–15 sec per min of audio)
Scalability: Excellent for future expansion
```

### Scenario 3: Current + Deepgram Cloud

```
Setup Cost: $0 (free tier)
Monthly Cost: $10–50+ (usage-based)
Annual Cost: $120–600+
Quality: Excellent (commercial grade)
Latency: Real-time
Scalability: Unlimited (pay-as-you-grow)
Risk: API dependency, cost variability
```

---

## Language Support Deep Dive

### Russian
- ✅ **Whisper tiny**: Good quality, universal model
- ✅ **Whisper base**: Better quality
- ✅✅ **Silero**: Best quality, purpose-built
- ✅ **Deepgram**: Good quality

### Hebrew
- ✅ **Whisper tiny**: Supported (99+ languages)
- ✅ **Whisper base**: Supported
- ❌ **Silero**: Not supported
- ✅ **Deepgram**: Supported

### Future Multilingual (20+ languages)
- ✅✅ **Whisper**: Best choice — single model for all
- ❌ **Silero**: Requires separate models per language
- ⚠️ **Vosk**: Limited language coverage
- ✅ **Deepgram**: Supported but cost scales with usage

---

## Decision Framework

**Choose Silero if**:
- Deploying exclusively for Russian speakers
- Cost optimization is top priority
- Self-hosted infrastructure is acceptable
- Real-time transcription not required

**Choose Whisper tiny if**:
- Planning Hebrew + Russian support
- Future multilingual expansion anticipated
- Self-hosted resilience preferred over cloud dependency
- Cost per inference acceptable

**Choose Deepgram if**:
- Real-time, low-latency transcription is critical
- Acceptable to pay per-usage
- Prefer managed cloud solution over self-hosting
- Quality consistency is top priority

---

## Implementation Roadmap

### Phase 1 (Current)
- ✅ Fix missing STT config fields in `app/config.py`
- ✅ Validate Deepgram integration is working
- Test voice transcription end-to-end

### Phase 2 (Optional)
- Implement local Silero STT as fallback
- Measure inference time and resource usage
- A/B test quality against Deepgram

### Phase 3 (Future)
- Evaluate Whisper tiny for multilingual support
- Plan Hebrew language rollout
- Decision point: continue Deepgram or migrate to self-hosted

---

## References

- Whisper: https://github.com/openai/whisper
- Silero STT: https://github.com/snakers4/silero-models
- Deepgram: https://deepgram.com
- Vosk: https://alphacephei.com/vosk/

---

## Document Maintenance

- Review quarterly as language requirements evolve
- Update cost estimates based on actual infrastructure bills
- Track Whisper/Silero model improvements
- Monitor Deepgram pricing changes
