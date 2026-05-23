# OK (Odnoklassniki) Integration Feasibility Gate

**Status:** Research-only. Do not implement until all checklist items are validated on a real test group.

**Current assumption:** OK may support group messaging via a Bot API similar to VK Callback API. Production-readiness is unconfirmed until the items below are validated with an active OK community group.

---

## Feasibility Checklist

### 1. Official Inbound Updates Model

- [ ] Confirm OK provides a documented Callback API (webhook push) for community bots.
- [ ] Identify the exact event schema for inbound direct messages to a community.
- [ ] Verify that confirmation handshake and secret validation work the same as VK.
- [ ] Determine whether polling is available as an alternative if webhooks are unreliable.

### 2. Webhook vs Polling

- [ ] Test webhook delivery reliability (retry behavior, timeout, deduplication semantics).
- [ ] Confirm whether OK retries unacknowledged events and how many times.
- [ ] Determine the required response format (`ok` plain text vs JSON).
- [ ] Test ngrok/public URL registration in the OK developer console.

### 3. Group Token Lifecycle

- [ ] Identify token type required for community messaging (group access token).
- [ ] Confirm token expiry policy (does it expire? refresh mechanism?).
- [ ] Test token revocation and re-issue in a real community.
- [ ] Document required token scopes (message read, message send, etc.).

### 4. Send-Message Method

- [ ] Find the equivalent of VK `messages.send` for OK communities.
- [ ] Confirm required parameters: peer ID, message text, random ID for idempotency.
- [ ] Verify `peer_id` semantics for direct messages vs group posts.
- [ ] Test actual message delivery to a user who messaged the community first.

### 5. Rate Limits

- [ ] Find documented rate limits per community token (messages per second, per day).
- [ ] Test actual throttling behavior (error codes, retry-after headers).
- [ ] Determine whether rate limits are enforced per-user or globally per token.

### 6. UI Primitives

- [ ] Check if OK supports in-message buttons (keyboard API equivalent).
- [ ] Determine button label length limits.
- [ ] Test button rendering in the OK mobile client and desktop client.
- [ ] Confirm whether plain-text numbered options are the correct fallback for unsupported clients.

### 7. Moderation / Policy Constraints for Sensitive Support Conversations

- [ ] Review OK community terms of service for mental health / crisis content.
- [ ] Confirm whether OK moderation systems auto-flag or block crisis-adjacent messages.
- [ ] Test that crisis responses (Tier 3/4) are delivered without filtering.
- [ ] Check whether the bot account requires any special approval for psychological support content.

### 8. Test Group Requirements

- [ ] Create a real OK community group for testing.
- [ ] Register a developer application and link it to the community.
- [ ] Complete the confirmation handshake from a public URL.
- [ ] Send at least 20 test messages and confirm full round-trip (inbound + outbound reply).
- [ ] Reproduce a crisis-tier message and confirm delivery of the crisis response without blocking.

---

## Decision Gate

**OK adapter implementation is blocked until:**

1. All items in sections 1–4 are confirmed with live tests on a real group.
2. Rate limits (section 5) are characterized and a backoff strategy is designed.
3. At least one crisis-tier message (Tier 3 or Tier 4) is delivered and replied to without platform filtering.

Once the gate is passed, open a separate task: **"OK Phase 1 Adapter Implementation"** following the same architecture as the VK adapter (`app/channels/ok_adapter.py`, `app/integrations/webhooks/ok.py`).
