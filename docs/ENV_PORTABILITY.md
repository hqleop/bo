# Environment Portability and Realtime Tuning

Use environment files as deployment profiles, not as local-only config.
The same code can run on a laptop, staging, or production by changing only env values.

## Backend

1. Copy `backend/.env.example` to `backend/.env`.
2. Set secure and environment-specific values:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG` (`0` in production)
   - `DJANGO_ALLOWED_HOSTS`
   - `CORS_ALLOWED_ORIGINS`
   - DB settings (`DB_*`)
3. Realtime/cache controls:
   - `STATUS_SYNC_CACHE_TTL_SECONDS`
   - `STATUS_SYNC_THROTTLE_PER_MINUTE`
   - `STATUS_SYNC_LOG_METRICS`
   - `USE_REDIS_CHANNEL_LAYER`
   - `REDIS_URL`
   - `REALTIME_PROPOSAL_EVENT_COALESCE_MS`
   - `REALTIME_PROPOSAL_EVENT_COALESCE_MAX_IDS`

## Frontend

1. Copy `frontend/.env.example` to `frontend/.env`.
2. Set API endpoint:
   - `NUXT_PUBLIC_API_BASE`
3. Realtime load controls (organizer pages):
   - `NUXT_PUBLIC_TENDER_REALTIME_SYNC_MS_*`
   - `NUXT_PUBLIC_TENDER_REALTIME_IDLE_*`
   - `NUXT_PUBLIC_TENDER_REALTIME_BURST_*`
   - `NUXT_PUBLIC_TENDER_REALTIME_HIDDEN_*`
   - `NUXT_PUBLIC_TENDER_REALTIME_OFFLINE_FALLBACK_MS`
   - `NUXT_PUBLIC_TENDER_REALTIME_PAUSE_WHEN_HIDDEN`
   - `NUXT_PUBLIC_TENDER_REALTIME_SYNC_JITTER_RATIO`

## Why this helps on another server

- No source edits for different infrastructure.
- You can keep conservative defaults for production and more aggressive values for staging/dev.
- You can tune load behavior (poll frequency, backoff, hidden-tab behavior) without redeploying code.
