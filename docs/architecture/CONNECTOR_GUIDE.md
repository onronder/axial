2026-01-13T13:09:16.000000000Z [inf]  Starting Container
2026-01-13T13:09:17.879288383Z [inf]  Tue Jan 13 13:09:16 2026 -> ClamAV update process started at Tue Jan 13 13:09:16 2026
2026-01-13T13:09:17.879299867Z [inf]  Tue Jan 13 13:09:16 2026 -> daily.cvd database is up-to-date (version: 27879, sigs: 354800, f-level: 90, builder: svc.clamav-publisher)
2026-01-13T13:09:17.879307372Z [inf]  Tue Jan 13 13:09:16 2026 -> main.cvd database is up-to-date (version: 63, sigs: 3287027, f-level: 90, builder: tomjudge)
2026-01-13T13:09:17.879314453Z [inf]  Tue Jan 13 13:09:16 2026 -> bytecode.cvd database is up-to-date (version: 339, sigs: 80, f-level: 90, builder: nrandolp)
2026-01-13T13:09:17.879321106Z [inf]  🛡️ Starting ClamAV daemon...
2026-01-13T13:09:24.985008803Z [err]  2026-01-13 13:09:24,977 - main - INFO - 🔭 Sentry initialized with logging and error tracking
2026-01-13T13:09:25.700849011Z [err]  2026-01-13 13:09:25,226 - core.resilience - INFO - ✅ Retry configurations loaded: OpenAI, Supabase, LlamaParse
2026-01-13T13:09:25.700858485Z [err]  2026-01-13 13:09:25,252 - core.metrics - INFO - 📊 Prometheus metrics initialized
2026-01-13T13:09:25.700978826Z [err]  2026-01-13 13:09:25,112 - main - INFO - 🔒 CORS: Loaded 2 origin(s) from ALLOWED_ORIGINS
2026-01-13T13:09:25.700985730Z [err]  2026-01-13 13:09:25,113 - main - INFO - 🔒 CORS: Production mode - 2 strict origin(s)
2026-01-13T13:09:25.700993809Z [err]  2026-01-13 13:09:25,226 - core.resilience - INFO - 🔌 Circuit breakers initialized for: OpenAI, LlamaParse, Supabase
2026-01-13T13:09:25.855251456Z [err]  2026-01-13 13:09:25,851 - services.email - INFO - 📧 EmailService initialized with Resend API
2026-01-13T13:09:26.692703349Z [err]  /usr/local/lib/python3.11/site-packages/clamd/__init__.py:6: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
2026-01-13T13:09:26.692707132Z [err]    __version__ = __import__('pkg_resources').get_distribution('clamd').version
2026-01-13T13:09:26.692710970Z [err]  2026-01-13 13:09:26,406 - worker.tasks - INFO - ✅ Worker tasks module loaded - Cache buster 001
2026-01-13T13:09:26.842524861Z [err]  2026-01-13 13:09:26,836 - core.db - INFO - ✅ Supabase client initialized successfully
2026-01-13T13:09:26.843116321Z [err]  INFO:     Started server process [1]
2026-01-13T13:09:26.843123193Z [err]  INFO:     Waiting for application startup.
2026-01-13T13:09:26.843129396Z [err]  2026-01-13 13:09:26,824 - main - INFO - 🚀 Starting Axio Hub API...
2026-01-13T13:09:26.843135514Z [err]  2026-01-13 13:09:26,824 - core.db - INFO - 🔌 Initializing Supabase client with connection pool
2026-01-13T13:09:27.004991794Z [err]  2026-01-13 13:09:27,000 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id&limit=1 "HTTP/2 200 OK"
2026-01-13T13:09:27.004997887Z [err]  2026-01-13 13:09:27,003 - main - INFO - ✅ Database connection verified
2026-01-13T13:09:27.005003262Z [err]  INFO:     Application startup complete.
2026-01-13T13:09:27.016732121Z [err]  INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
2026-01-13T13:09:31.803606904Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: MaxRecHWP3 limit set to 16.
2026-01-13T13:09:31.803619155Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: PCREMatchLimit limit set to 100000.
2026-01-13T13:09:31.803628183Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: PCRERecMatchLimit limit set to 2000.
2026-01-13T13:09:31.803636351Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: PCREMaxFileSize limit set to 104857600.
2026-01-13T13:09:31.803643676Z [inf]  Tue Jan 13 13:09:31 2026 -> Archive support enabled.
2026-01-13T13:09:31.803794323Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: Global time limit set to 120000 milliseconds.
2026-01-13T13:09:31.803800734Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: Global size limit set to 524288000 bytes.
2026-01-13T13:09:31.803807314Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: File size limit set to 209715200 bytes.
2026-01-13T13:09:31.803813301Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: Recursion level limit set to 17.
2026-01-13T13:09:31.803818746Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: Files limit set to 10000.
2026-01-13T13:09:31.803824021Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: Core-dump limit is 0.
2026-01-13T13:09:31.803828866Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: MaxEmbeddedPE limit set to 41943040 bytes.
2026-01-13T13:09:31.803833378Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: MaxHTMLNormalize limit set to 41943040 bytes.
2026-01-13T13:09:31.803838319Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: MaxHTMLNoTags limit set to 8388608 bytes.
2026-01-13T13:09:31.803844143Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: MaxScriptNormalize limit set to 20971520 bytes.
2026-01-13T13:09:31.803848849Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: MaxZipTypeRcg limit set to 1048576 bytes.
2026-01-13T13:09:31.803854164Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: MaxPartitions limit set to 50.
2026-01-13T13:09:31.803860277Z [inf]  Tue Jan 13 13:09:31 2026 -> Limits: MaxIconsPE limit set to 100.
2026-01-13T13:09:31.806102282Z [inf]  Tue Jan 13 13:09:31 2026 -> Image (graphics) scanning support enabled.
2026-01-13T13:09:31.806107917Z [inf]  Tue Jan 13 13:09:31 2026 -> Detection using image fuzzy hash enabled.
2026-01-13T13:09:31.806112971Z [inf]  Tue Jan 13 13:09:31 2026 -> AlertExceedsMax heuristic detection disabled.
2026-01-13T13:09:31.806118398Z [inf]  Tue Jan 13 13:09:31 2026 -> Heuristic alerts enabled.
2026-01-13T13:09:31.806123400Z [inf]  Tue Jan 13 13:09:31 2026 -> Portable Executable support enabled.
2026-01-13T13:09:31.806128366Z [inf]  Tue Jan 13 13:09:31 2026 -> ELF support enabled.
2026-01-13T13:09:31.806133359Z [inf]  Tue Jan 13 13:09:31 2026 -> Mail files support enabled.
2026-01-13T13:09:31.806138977Z [inf]  Tue Jan 13 13:09:31 2026 -> OLE2 support enabled.
2026-01-13T13:09:31.806144466Z [inf]  Tue Jan 13 13:09:31 2026 -> PDF support enabled.
2026-01-13T13:09:31.806149963Z [inf]  Tue Jan 13 13:09:31 2026 -> SWF support enabled.
2026-01-13T13:09:31.806155318Z [inf]  Tue Jan 13 13:09:31 2026 -> HTML support enabled.
2026-01-13T13:09:31.806160622Z [inf]  Tue Jan 13 13:09:31 2026 -> XMLDOCS support enabled.
2026-01-13T13:09:31.806166032Z [inf]  Tue Jan 13 13:09:31 2026 -> HWP3 support enabled.
2026-01-13T13:09:31.806179720Z [inf]  Tue Jan 13 13:09:31 2026 -> OneNote support enabled.
2026-01-13T13:09:31.806222358Z [inf]  Tue Jan 13 13:09:31 2026 -> Self checking every 600 seconds.
2026-01-13T13:09:31.806242053Z [inf]  Tue Jan 13 13:09:31 2026 -> Listening daemon: PID: 12
2026-01-13T13:09:31.806247880Z [inf]  Tue Jan 13 13:09:31 2026 -> MaxQueue set to: 100
2026-01-13T13:19:37.382661952Z [inf]  Tue Jan 13 13:19:31 2026 -> SelfCheck: Database status OK.
2026-01-13T13:29:32.770476491Z [inf]  Tue Jan 13 13:29:31 2026 -> SelfCheck: Database status OK.
2026-01-13T13:39:39.697891280Z [inf]  Tue Jan 13 13:39:31 2026 -> SelfCheck: Database status OK.
2026-01-13T13:49:35.747328836Z [inf]  Tue Jan 13 13:49:31 2026 -> SelfCheck: Database status OK.
2026-01-13T13:59:32.588919040Z [inf]  Tue Jan 13 13:59:32 2026 -> SelfCheck: Database status OK.
2026-01-13T14:09:40.867446434Z [inf]  Tue Jan 13 14:09:32 2026 -> SelfCheck: Database status OK.
2026-01-13T14:19:36.066708912Z [inf]  Tue Jan 13 14:19:32 2026 -> SelfCheck: Database status OK.
2026-01-13T14:20:05.827749885Z [err]  2026-01-13 14:20:02,885 - core.tracing - INFO - ➡️  [0b8a4042] GET /api/v1/team/effective-plan (user: eyJhbGci...)
2026-01-13T14:20:05.827761121Z [err]  2026-01-13 14:20:03,067 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.827767647Z [err]  2026-01-13 14:20:03,137 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.827772769Z [err]  2026-01-13 14:20:03,225 - httpx - INFO - HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/rpc/get_effective_plan "HTTP/2 200 OK"
2026-01-13T14:20:05.827777292Z [err]  2026-01-13 14:20:03,234 - core.tracing - INFO - ➡️  [6e88f5be] GET /api/v1/billing/plans (user: eyJhbGci...)
2026-01-13T14:20:05.827782338Z [err]  2026-01-13 14:20:03,301 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.827787102Z [err]  2026-01-13 14:20:03,354 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.827791377Z [err]  2026-01-13 14:20:03,373 - core.tracing - INFO - ➡️  [03e5e691] GET /api/v1/settings/profile (user: eyJhbGci...)
2026-01-13T14:20:05.827795927Z [err]  2026-01-13 14:20:03,413 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.827800746Z [err]  2026-01-13 14:20:03,452 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.830563152Z [inf]  INFO:     100.64.0.2:18930 - "GET /api/v1/team/effective-plan HTTP/1.1" 200 OK
2026-01-13T14:20:05.830569952Z [inf]  INFO:     100.64.0.3:28756 - "GET /api/v1/settings/profile HTTP/1.1" 200 OK
2026-01-13T14:20:05.830574732Z [err]  2026-01-13 14:20:03,635 - core.tracing - INFO - ➡️  [4e2e256a] GET /api/v1/usage (user: eyJhbGci...)
2026-01-13T14:20:05.830579494Z [err]  2026-01-13 14:20:03,635 - core.tracing - INFO - ➡️  [a957e447] GET /api/v1/conversations (user: eyJhbGci...)
2026-01-13T14:20:05.830584018Z [err]  2026-01-13 14:20:03,672 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.830593831Z [err]  2026-01-13 14:20:03,504 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.830598335Z [err]  2026-01-13 14:20:03,550 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.830602503Z [err]  2026-01-13 14:20:03,585 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-13T14:20:05.830607082Z [err]  2026-01-13 14:20:03,627 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.830611147Z [err]  2026-01-13 14:20:03,629 - core.tracing - INFO - ✅ [0b8a4042] GET /api/v1/team/effective-plan → 200 (744.7ms)
2026-01-13T14:20:05.830616054Z [err]  2026-01-13 14:20:03,630 - core.tracing - INFO - ✅ [03e5e691] GET /api/v1/settings/profile → 200 (256.4ms)
2026-01-13T14:20:05.833563153Z [err]  2026-01-13 14:20:03,713 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.833575156Z [err]  2026-01-13 14:20:03,757 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=plan&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-13T14:20:05.833584801Z [err]  2026-01-13 14:20:03,794 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.833591919Z [err]  2026-01-13 14:20:03,846 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/subscriptions?select=status&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.833598381Z [err]  2026-01-13 14:20:03,886 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id%2Cfile_size_bytes&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-13T14:20:05.833605882Z [err]  2026-01-13 14:20:03,932 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.833612769Z [err]  2026-01-13 14:20:03,974 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.833619571Z [err]  2026-01-13 14:20:04,020 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/conversations?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&order=updated_at.desc "HTTP/2 200 OK"
2026-01-13T14:20:05.833626133Z [err]  2026-01-13 14:20:04,021 - core.tracing - INFO - ✅ [4e2e256a] GET /api/v1/usage → 200 (386.5ms)
2026-01-13T14:20:05.836893538Z [err]  2026-01-13 14:20:04,729 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/notifications?select=id&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&is_read=eq.False "HTTP/2 200 OK"
2026-01-13T14:20:05.836894222Z [err]  2026-01-13 14:20:04,022 - core.tracing - INFO - ✅ [a957e447] GET /api/v1/conversations → 200 (386.2ms)
2026-01-13T14:20:05.836904495Z [inf]  INFO:     100.64.0.4:61902 - "GET /api/v1/usage HTTP/1.1" 200 OK
2026-01-13T14:20:05.836906613Z [err]  2026-01-13 14:20:04,731 - core.tracing - INFO - ✅ [525d419d] GET /api/v1/notifications/unread-count → 200 (128.2ms)
2026-01-13T14:20:05.836912314Z [inf]  INFO:     100.64.0.5:41708 - "GET /api/v1/conversations HTTP/1.1" 200 OK
2026-01-13T14:20:05.836918303Z [err]  2026-01-13 14:20:04,111 - httpx - INFO - HTTP Request: GET https://api.polar.sh/v1/products?is_archived=false "HTTP/1.1 307 Temporary Redirect"
2026-01-13T14:20:05.836924280Z [err]  2026-01-13 14:20:04,205 - httpx - INFO - HTTP Request: GET https://api.polar.sh/v1/products/?is_archived=false "HTTP/1.1 200 OK"
2026-01-13T14:20:05.836930732Z [err]  2026-01-13 14:20:04,210 - core.tracing - INFO - ✅ [6e88f5be] GET /api/v1/billing/plans → 200 (975.9ms)
2026-01-13T14:20:05.836936351Z [inf]  INFO:     100.64.0.3:28746 - "GET /api/v1/billing/plans HTTP/1.1" 200 OK
2026-01-13T14:20:05.836946143Z [err]  2026-01-13 14:20:04,603 - core.tracing - INFO - ➡️  [525d419d] GET /api/v1/notifications/unread-count (user: eyJhbGci...)
2026-01-13T14:20:05.836953020Z [err]  2026-01-13 14:20:04,649 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.836959242Z [err]  2026-01-13 14:20:04,690 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.839067810Z [err]  2026-01-13 14:20:04,733 - core.tracing - INFO - ➡️  [f323cde0] GET /api/v1/settings/profile (user: eyJhbGci...)
2026-01-13T14:20:05.839075499Z [err]  2026-01-13 14:20:04,781 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.839081486Z [err]  2026-01-13 14:20:04,819 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.839085945Z [err]  2026-01-13 14:20:04,865 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-13T14:20:05.839093398Z [err]  2026-01-13 14:20:04,905 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.839099877Z [inf]  INFO:     100.64.0.3:28746 - "GET /api/v1/notifications/unread-count HTTP/1.1" 200 OK
2026-01-13T14:20:05.839105658Z [err]  2026-01-13 14:20:04,907 - core.tracing - INFO - ✅ [f323cde0] GET /api/v1/settings/profile → 200 (174.6ms)
2026-01-13T14:20:05.839111037Z [inf]  INFO:     100.64.0.5:41708 - "GET /api/v1/settings/profile HTTP/1.1" 200 OK
2026-01-13T14:20:05.839116596Z [err]  2026-01-13 14:20:05,268 - core.tracing - INFO - ➡️  [987565b7] GET /api/v1/notifications/unread-count (user: eyJhbGci...)
2026-01-13T14:20:05.839122584Z [err]  2026-01-13 14:20:05,323 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.839128244Z [err]  2026-01-13 14:20:05,382 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.841079300Z [err]  2026-01-13 14:20:05,493 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/notifications?select=id&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&is_read=eq.False "HTTP/2 200 OK"
2026-01-13T14:20:05.841093524Z [err]  2026-01-13 14:20:05,496 - core.tracing - INFO - ✅ [987565b7] GET /api/v1/notifications/unread-count → 200 (228.6ms)
2026-01-13T14:20:05.841103852Z [err]  2026-01-13 14:20:05,499 - core.tracing - INFO - ➡️  [dca6db33] GET /api/v1/integrations/available (user: eyJhbGci...)
2026-01-13T14:20:05.841109296Z [err]  2026-01-13 14:20:05,500 - core.tracing - INFO - ➡️  [9b14d3d8] GET /api/v1/integrations/status (user: eyJhbGci...)
2026-01-13T14:20:05.841113891Z [err]  2026-01-13 14:20:05,579 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.841118900Z [err]  2026-01-13 14:20:05,642 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.841134881Z [err]  2026-01-13 14:20:05,717 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/connector_definitions?select=%2A&is_active=eq.True "HTTP/2 200 OK"
2026-01-13T14:20:05.880832641Z [err]  2026-01-13 14:20:05,879 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:05.930661963Z [err]  2026-01-13 14:20:05,925 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:05.979490404Z [err]  2026-01-13 14:20:05,968 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations?select=id%2Cconnector_definition_id%2Clast_sync_at%2Cconnector_definitions%28type%2Cname%2Cicon_path%2Ccategory%29&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-13T14:20:05.979499941Z [inf]  INFO:     100.64.0.5:41708 - "GET /api/v1/notifications/unread-count HTTP/1.1" 200 OK
2026-01-13T14:20:05.979506307Z [err]  2026-01-13 14:20:05,970 - core.tracing - INFO - ✅ [dca6db33] GET /api/v1/integrations/available → 200 (471.6ms)
2026-01-13T14:20:05.979513185Z [err]  2026-01-13 14:20:05,971 - core.tracing - INFO - ✅ [9b14d3d8] GET /api/v1/integrations/status → 200 (470.3ms)
2026-01-13T14:20:05.979571817Z [inf]  INFO:     100.64.0.3:28746 - "GET /api/v1/integrations/available HTTP/1.1" 200 OK
2026-01-13T14:20:05.979579333Z [inf]  INFO:     100.64.0.3:28756 - "GET /api/v1/integrations/status HTTP/1.1" 200 OK
2026-01-13T14:20:05.979585023Z [err]  2026-01-13 14:20:05,974 - core.tracing - INFO - ➡️  [f732c059] GET /api/v1/documents/stats (user: eyJhbGci...)
2026-01-13T14:20:06.034590516Z [err]  2026-01-13 14:20:06,027 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:06.695316230Z [err]  2026-01-13 14:20:06,103 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:06.695323853Z [err]  2026-01-13 14:20:06,148 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-13T14:20:06.695329785Z [err]  2026-01-13 14:20:06,618 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:06.695333564Z [err]  2026-01-13 14:20:06,149 - core.tracing - INFO - ✅ [f732c059] GET /api/v1/documents/stats → 200 (175.3ms)
2026-01-13T14:20:06.695336498Z [err]  2026-01-13 14:20:06,666 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-13T14:20:06.695341953Z [inf]  INFO:     100.64.0.5:41718 - "GET /api/v1/documents/stats HTTP/1.1" 200 OK
2026-01-13T14:20:06.695342465Z [err]  2026-01-13 14:20:06,667 - core.tracing - INFO - ✅ [99608813] GET /api/v1/documents/stats → 200 (174.6ms)
2026-01-13T14:20:06.695348047Z [inf]  INFO:     100.64.0.5:41718 - "GET /api/v1/documents/stats HTTP/1.1" 200 OK
2026-01-13T14:20:06.695350297Z [err]  2026-01-13 14:20:06,493 - core.tracing - INFO - ➡️  [99608813] GET /api/v1/documents/stats (user: eyJhbGci...)
2026-01-13T14:20:06.695357428Z [err]  2026-01-13 14:20:06,539 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:10.679791660Z [err]  2026-01-13 14:20:10,678 - core.tracing - INFO - ➡️  [ccb690c4] GET /api/v1/integrations/status (user: eyJhbGci...)
2026-01-13T14:20:10.728837198Z [err]  2026-01-13 14:20:10,724 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:10.771254953Z [err]  2026-01-13 14:20:10,769 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:10.847615936Z [err]  2026-01-13 14:20:10,830 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations?select=id%2Cconnector_definition_id%2Clast_sync_at%2Cconnector_definitions%28type%2Cname%2Cicon_path%2Ccategory%29&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-13T14:20:10.847622719Z [err]  2026-01-13 14:20:10,832 - core.tracing - INFO - ✅ [ccb690c4] GET /api/v1/integrations/status → 200 (154.2ms)
2026-01-13T14:20:10.847627682Z [inf]  INFO:     100.64.0.5:41718 - "GET /api/v1/integrations/status HTTP/1.1" 200 OK
2026-01-13T14:20:10.847632508Z [err]  2026-01-13 14:20:10,835 - core.tracing - INFO - ➡️  [dbab6ce2] GET /api/v1/integrations/available (user: eyJhbGci...)
2026-01-13T14:20:10.925879384Z [err]  2026-01-13 14:20:10,919 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-13T14:20:10.969734477Z [err]  2026-01-13 14:20:10,962 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-13T14:20:11.005298201Z [err]  2026-01-13 14:20:11,002 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/connector_definitions?select=%2A&is_active=eq.True "HTTP/2 200 OK"
2026-01-13T14:20:11.005303105Z [err]  2026-01-13 14:20:11,004 - core.tracing - INFO - ✅ [dbab6ce2] GET /api/v1/integrations/available → 200 (168.8ms)
2026-01-13T14:20:11.009661469Z [inf]  INFO:     100.64.0.3:43364 - "GET /api/v1/integrations/available HTTP/1.1" 200 OK

2026-01-13T13:09:09.000000000Z [inf]  Starting Container
2026-01-13T13:09:10.274180769Z [inf]  Tue Jan 13 13:09:09 2026 -> ClamAV update process started at Tue Jan 13 13:09:09 2026
2026-01-13T13:09:10.274184034Z [inf]  Tue Jan 13 13:09:09 2026 -> daily.cvd database is up-to-date (version: 27879, sigs: 354800, f-level: 90, builder: svc.clamav-publisher)
2026-01-13T13:09:10.274187179Z [inf]  Tue Jan 13 13:09:09 2026 -> main.cvd database is up-to-date (version: 63, sigs: 3287027, f-level: 90, builder: tomjudge)
2026-01-13T13:09:10.274190193Z [inf]  Tue Jan 13 13:09:09 2026 -> bytecode.cvd database is up-to-date (version: 339, sigs: 80, f-level: 90, builder: nrandolp)
2026-01-13T13:09:10.274192837Z [inf]  🛡️ Starting ClamAV daemon...
2026-01-13T13:09:14.698884142Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: Global time limit set to 120000 milliseconds.
2026-01-13T13:09:14.698891824Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: Global size limit set to 524288000 bytes.
2026-01-13T13:09:14.698893717Z [inf]  Tue Jan 13 13:09:14 2026 -> Self checking every 600 seconds.
2026-01-13T13:09:14.698897703Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: File size limit set to 209715200 bytes.
2026-01-13T13:09:14.698901158Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: Recursion level limit set to 17.
2026-01-13T13:09:14.698906676Z [inf]  Tue Jan 13 13:09:14 2026 -> Listening daemon: PID: 12
2026-01-13T13:09:14.698906776Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: Files limit set to 10000.
2026-01-13T13:09:14.698913737Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: Core-dump limit is 0.
2026-01-13T13:09:14.698914538Z [inf]  Tue Jan 13 13:09:14 2026 -> MaxQueue set to: 100
2026-01-13T13:09:14.698918263Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: MaxEmbeddedPE limit set to 41943040 bytes.
2026-01-13T13:09:14.698921318Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: MaxHTMLNormalize limit set to 41943040 bytes.
2026-01-13T13:09:14.698924202Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: MaxHTMLNoTags limit set to 8388608 bytes.
2026-01-13T13:09:14.698927237Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: MaxScriptNormalize limit set to 20971520 bytes.
2026-01-13T13:09:14.698930362Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: MaxZipTypeRcg limit set to 1048576 bytes.
2026-01-13T13:09:14.698933216Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: MaxPartitions limit set to 50.
2026-01-13T13:09:14.698936200Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: MaxIconsPE limit set to 100.
2026-01-13T13:09:14.698938974Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: MaxRecHWP3 limit set to 16.
2026-01-13T13:09:14.698942590Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: PCREMatchLimit limit set to 100000.
2026-01-13T13:09:14.698945614Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: PCRERecMatchLimit limit set to 2000.
2026-01-13T13:09:14.698950331Z [inf]  Tue Jan 13 13:09:14 2026 -> Limits: PCREMaxFileSize limit set to 104857600.
2026-01-13T13:09:14.698953146Z [inf]  Tue Jan 13 13:09:14 2026 -> Archive support enabled.
2026-01-13T13:09:14.698955790Z [inf]  Tue Jan 13 13:09:14 2026 -> Image (graphics) scanning support enabled.
2026-01-13T13:09:14.698958564Z [inf]  Tue Jan 13 13:09:14 2026 -> Detection using image fuzzy hash enabled.
2026-01-13T13:09:14.698961228Z [inf]  Tue Jan 13 13:09:14 2026 -> AlertExceedsMax heuristic detection disabled.
2026-01-13T13:09:14.698963922Z [inf]  Tue Jan 13 13:09:14 2026 -> Heuristic alerts enabled.
2026-01-13T13:09:14.698966816Z [inf]  Tue Jan 13 13:09:14 2026 -> Portable Executable support enabled.
2026-01-13T13:09:14.698970231Z [inf]  Tue Jan 13 13:09:14 2026 -> ELF support enabled.
2026-01-13T13:09:14.698973106Z [inf]  Tue Jan 13 13:09:14 2026 -> Mail files support enabled.
2026-01-13T13:09:14.698975990Z [inf]  Tue Jan 13 13:09:14 2026 -> OLE2 support enabled.
2026-01-13T13:09:14.698978744Z [inf]  Tue Jan 13 13:09:14 2026 -> PDF support enabled.
2026-01-13T13:09:14.698981608Z [inf]  Tue Jan 13 13:09:14 2026 -> SWF support enabled.
2026-01-13T13:09:14.698984393Z [inf]  Tue Jan 13 13:09:14 2026 -> HTML support enabled.
2026-01-13T13:09:14.698987167Z [inf]  Tue Jan 13 13:09:14 2026 -> XMLDOCS support enabled.
2026-01-13T13:09:14.698990742Z [inf]  Tue Jan 13 13:09:14 2026 -> HWP3 support enabled.
2026-01-13T13:09:14.698994257Z [inf]  Tue Jan 13 13:09:14 2026 -> OneNote support enabled.
2026-01-13T13:09:17.034144669Z [inf]   
2026-01-13T13:09:17.034150318Z [inf]   -------------- celery@b4759615d988 v5.3.6 (emerald-rush)
2026-01-13T13:09:17.034153953Z [inf]  --- ***** ----- 
2026-01-13T13:09:17.034156768Z [inf]  -- ******* ---- Linux-6.1.0-41-cloud-amd64-x86_64-with-glibc2.41 2026-01-13 13:09:16
2026-01-13T13:09:17.034159812Z [inf]  - *** --- * --- 
2026-01-13T13:09:17.034162947Z [inf]  - ** ---------- [config]
2026-01-13T13:09:17.034166232Z [inf]  - ** ---------- .> app:         axial_worker:0x7f0c3c65f7d0
2026-01-13T13:09:17.034169066Z [inf]  - ** ---------- .> transport:   redis://default:**@redis.railway.internal:6379//
2026-01-13T13:09:17.034175195Z [inf]                  .> queues.parsing   exchange=celery(direct) key=celery
2026-01-13T13:09:17.034195916Z [inf]   -------------- [queues]
2026-01-13T13:09:17.034199362Z [inf]                  .> celery           exchange=celery(direct) key=celery
2026-01-13T13:09:17.034202006Z [inf]    . worker.tasks.crawl_discovery_task
2026-01-13T13:09:17.034203007Z [inf]                  .> queues.embedding exchange=celery(direct) key=celery
2026-01-13T13:09:17.034205611Z [inf]    . worker.tasks.finalize_crawl_task
2026-01-13T13:09:17.034206773Z [inf]                  .> queues.indexing  exchange=celery(direct) key=celery
2026-01-13T13:09:17.034208736Z [inf]    . worker.tasks.generate_embeddings_task
2026-01-13T13:09:17.034212061Z [inf]    . worker.tasks.health_check_task
2026-01-13T13:09:17.034212421Z [inf]  - ** ---------- .> results:     redis://default:**@redis.railway.internal:6379/
2026-01-13T13:09:17.034216958Z [inf]    . worker.tasks.index_chunks_task
2026-01-13T13:09:17.034219171Z [inf]  - *** --- * --- .> concurrency: 10 (gevent)
2026-01-13T13:09:17.034220493Z [inf]    . worker.tasks.process_page_task
2026-01-13T13:09:17.034222997Z [inf]  -- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
2026-01-13T13:09:17.034223728Z [inf]  
2026-01-13T13:09:17.034226282Z [inf]  --- ***** ----- 
2026-01-13T13:09:17.034227213Z [err]  [2026-01-13 13:09:16,967: INFO/MainProcess] Connected to redis://default:**@redis.railway.internal:6379//
2026-01-13T13:09:17.034230739Z [err]  [2026-01-13 13:09:16,990: INFO/MainProcess] mingle: searching for neighbors
2026-01-13T13:09:17.034232151Z [err]  /usr/local/lib/python3.11/site-packages/clamd/__init__.py:6: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
2026-01-13T13:09:17.034234855Z [inf]  
2026-01-13T13:09:17.034236097Z [err]    __version__ = __import__('pkg_resources').get_distribution('clamd').version
2026-01-13T13:09:17.034237539Z [inf]  [tasks]
2026-01-13T13:09:17.034240203Z [inf]    . finalize_job_task
2026-01-13T13:09:17.034243127Z [inf]    . process_file_task
2026-01-13T13:09:17.034245781Z [inf]    . unified_ingest_task
2026-01-13T13:09:17.034248706Z [inf]    . worker.tasks.check_scheduled_crawls
2026-01-13T13:09:17.034251580Z [inf]    . worker.tasks.cleanup_old_jobs
2026-01-13T13:09:18.077717720Z [err]  [2026-01-13 13:09:18,034: INFO/MainProcess] mingle: all alone
2026-01-13T13:09:18.077722177Z [err]  [2026-01-13 13:09:18,071: INFO/MainProcess] celery@b4759615d988 ready.
2026-01-13T13:09:18.086373775Z [err]  [2026-01-13 13:09:18,081: INFO/MainProcess] pidbox: Connected to redis://default:**@redis.railway.internal:6379//.
2026-01-13T13:19:19.551568163Z [inf]  Tue Jan 13 13:19:14 2026 -> SelfCheck: Database status OK.
2026-01-13T13:29:16.670358667Z [inf]  Tue Jan 13 13:29:14 2026 -> SelfCheck: Database status OK.
2026-01-13T13:39:18.002914334Z [inf]  Tue Jan 13 13:39:14 2026 -> SelfCheck: Database status OK.
2026-01-13T13:49:20.504869937Z [inf]  Tue Jan 13 13:49:15 2026 -> SelfCheck: Database status OK.
2026-01-13T13:59:23.370077763Z [inf]  Tue Jan 13 13:59:15 2026 -> SelfCheck: Database status OK.
2026-01-13T14:09:17.678857284Z [inf]  Tue Jan 13 14:09:15 2026 -> SelfCheck: Database status OK.
2026-01-13T14:19:20.596767556Z [inf]  Tue Jan 13 14:19:15 2026 -> SelfCheck: Database status OK.

16:08:37.542 Running build in Washington, D.C., USA (East) – iad1
16:08:37.543 Build machine configuration: 4 cores, 8 GB
16:08:37.731 Cloning github.com/onronder/axial (Branch: main, Commit: 1dd911b)
16:08:38.502 Cloning completed: 770.000ms
16:08:39.413 Restored build cache from previous deployment (5R63mRpQZ2qtWDye9PyevQzNDqSC)
16:08:39.726 Running "vercel build"
16:08:40.162 Vercel CLI 50.1.6
16:08:40.493 Installing dependencies...
16:08:42.296 
16:08:42.297 up to date in 2s
16:08:42.297 
16:08:42.297 289 packages are looking for funding
16:08:42.297   run `npm fund` for details
16:08:42.328 Detected Next.js version: 16.0.10
16:08:42.335 Running "npm run build"
16:08:42.434 
16:08:42.434 > frontend-new@0.1.0 build
16:08:42.434 > next build
16:08:42.434 
16:08:43.754    ▲ Next.js 16.0.10 (Turbopack)
16:08:43.754    - Experiments (use with caution):
16:08:43.754      · clientTraceMetadata
16:08:43.754      · optimizePackageImports
16:08:43.754 
16:08:43.789    Creating an optimized production build ...
16:09:02.887  ✓ Compiled successfully in 18.3s
16:09:02.887    Running next.config.js provided runAfterProductionCompile ...
16:09:03.163 [@sentry/nextjs - After Production Compile] Info: Sending telemetry data on issues and performance to Sentry. To disable telemetry, set `options.telemetry` to `false`.
16:09:05.480 > Found 430 files
16:09:05.484 > Found 100 files
16:09:05.490 > Analyzing 100 sources
16:09:05.506 > Analyzing 430 sources
16:09:05.513 > Analyzing completed in 0.023s
16:09:05.514 > Rewriting sources
16:09:05.553 > Analyzing completed in 0.047s
16:09:05.554 > Rewriting sources
16:09:05.802 > Rewriting completed in 0.288s
16:09:05.804 > Adding source map references
16:09:06.458 > Rewriting completed in 0.904s
16:09:06.483 > Adding source map references
16:09:06.580 > Bundling completed in 0.775s
16:09:06.580 > Bundled 100 files for upload
16:09:06.580 > Bundle ID: f7ff0ea8-f625-5cff-83da-101b1d4c3bcb
16:09:06.608 > Optimizing completed in 0.028s
16:09:08.338 > Uploading completed in 1.374s
16:09:08.338 > Uploaded files to Sentry
16:09:08.693 > Processing completed in 0.355s
16:09:08.693 > File upload complete (processing pending on server)
16:09:08.694 > Organization: fittechs
16:09:08.694 > Projects: axiohub-frontend
16:09:08.694 > Release: 1dd911b2ab79f07fb13becfadbfa65abbf89edad
16:09:08.694 > Dist: None
16:09:08.694 > Upload type: artifact bundle
16:09:08.694 
16:09:08.694 Source Map Upload Report
16:09:08.694   Scripts
16:09:08.694     ~/01c2c7b0774098ac.js (sourcemap at d8f5b521e2c9e9c9.js.map, debug id 2aadde59-4158-2286-1c74-09dfee21ce9a)
16:09:08.694     ~/0267809f41e667a9.js (sourcemap at 37577569f11e55ef.js.map, debug id 1161c45b-2866-ce4e-99b6-56f146312422)
16:09:08.695     ~/0a1efa1d8621152b.js (sourcemap at 92c11afe64a0dc60.js.map, debug id 5d30fa8b-6ba0-f1b1-1371-854d15308f2e)
16:09:08.695     ~/0eeb2eb75c9817a9.js (sourcemap at d58fb72b8734f61c.js.map, debug id a871dead-25fb-7f19-bbd2-18e3dc150daf)
16:09:08.695     ~/10de09ffec5f86b2.js (sourcemap at c2689ee959a21033.js.map, debug id a535dedf-4774-a3ad-e4d0-902a14df764d)
16:09:08.695     ~/14892d9c158809e2.js (sourcemap at 2f23a2a34f9ea7cf.js.map, debug id e0adc1da-5783-a313-6df9-34f293f861af)
16:09:08.695     ~/183763f228b5bcf1.js (sourcemap at b771ef2d58d400e2.js.map, debug id 2ea6c79e-a799-24cd-873b-b67c7aa76f52)
16:09:08.695     ~/18753bea754f8e79.js (sourcemap at 6f4430f1e4cffe3f.js.map, debug id 7df5e1f7-5aa9-20d8-bb7a-395193f8a697)
16:09:08.695     ~/194b3b487311dccf.js (sourcemap at 0d11bdb1a4200f03.js.map, debug id 6cb5f628-8d1f-d18d-d2d4-30d28d042fa0)
16:09:08.695     ~/1a5d2cb58f827305.js (sourcemap at a09f918ff247f735.js.map, debug id ee50e671-c0e7-0728-346c-c97dcdb5de5e)
16:09:08.695     ~/29d049d518e4d93a.js (sourcemap at cc163944161d7df2.js.map, debug id 489e6cce-5782-849a-a392-6805499a39aa)
16:09:08.695     ~/2cd4d73c09075fa4.js (sourcemap at ee148d8b219c927a.js.map, debug id c96e7fdc-6775-3e9c-ab7c-a96aa19ec54b)
16:09:08.695     ~/2f3114f242a50809.js (sourcemap at c98e6720b52c307a.js.map, debug id 6600690c-c509-c4de-e211-be01b778f681)
16:09:08.696     ~/3100c40f9ddc28da.js (sourcemap at f3712fa2caa675d6.js.map, debug id c972c207-4054-da88-4399-ba75cd2e92d3)
16:09:08.696     ~/39f561c6f4726867.js (sourcemap at 7820c02cd5c58874.js.map, debug id 39995e43-d677-9cdb-9c20-02bb591d8b41)
16:09:08.696     ~/4994b446a8515ccc.js (sourcemap at ff2289e6ca6b1786.js.map, debug id eb6b1e70-aba2-de5c-e3a0-2e7417f6df3e)
16:09:08.702     ~/4e6c8c9cddd926e6.js (sourcemap at 5ab05ef1ca23dcb3.js.map, debug id 3523e392-aaaa-8919-c86f-2889c8497c0b)
16:09:08.702     ~/5f119dc4394ee2fa.js (sourcemap at 735e63492633a6f5.js.map, debug id 90874f72-c07b-f49e-bb37-fa47d686bc49)
16:09:08.702     ~/631b9d43f65f13e4.js (sourcemap at 5327ec6de83ef3ff.js.map, debug id 8bd6131c-110c-e6bd-9023-e2339f5a3830)
16:09:08.702     ~/64c981496995a4b6.js (sourcemap at 9151782e8638b1ac.js.map, debug id 62cd6d38-9e2a-7a4d-e380-cf29325e730b)
16:09:08.702     ~/6aac47217564e63d.js (sourcemap at aa6d98dbf2485283.js.map, debug id 251ad38f-1a47-360b-f0a8-8c7b858f639a)
16:09:08.703     ~/6e6ca1d801b146ba.js (sourcemap at cd8e721ba72bfed4.js.map, debug id 8c344ed8-634b-600f-f4af-9d8c11543185)
16:09:08.703     ~/71f6cb242555a467.js (sourcemap at 1c1b9175e798d4dd.js.map, debug id df5dcc42-a552-7c47-b241-812be16d0566)
16:09:08.703     ~/72acf68f34bff552.js (sourcemap at 2ca5a85fd8a2e6ce.js.map, debug id 56305881-d423-2f76-46e2-e4bc2e19f8c8)
16:09:08.704     ~/79811b18e06a89ef.js (sourcemap at fbf21dc5aab181ee.js.map, debug id f5f1832c-49e7-9147-139c-d5b79439cdfd)
16:09:08.704     ~/7cac19251570adc7.js (sourcemap at 35e136cce5c54b58.js.map, debug id ca195ca8-0cc1-cec3-2050-49e87aba214d)
16:09:08.704     ~/804e4cb100207fb8.js (sourcemap at d59388c26f9ae249.js.map, debug id 525891db-6320-0aab-83d2-a4be750038da)
16:09:08.704     ~/902cbe21fe2f64d6.js (sourcemap at 3313a3efd5888ecf.js.map, debug id cda6b576-012e-8cfd-3d7a-d188dd6f17ec)
16:09:08.704     ~/92bba849835903a0.js (sourcemap at 8b055edd7eaad111.js.map, debug id 96722136-1237-eff8-fe4b-45a0a1366d54)
16:09:08.704     ~/949854601b8b74cd.js (sourcemap at 9c6d4874507cac84.js.map, debug id 8aff9036-6db1-5ada-4e69-a0c7c807624f)
16:09:08.704     ~/9bf0adee6c2ce7fb.js (sourcemap at 52fe024d847c3a9f.js.map, debug id 71db69ba-0822-4481-507d-2b0f7438208e)
16:09:08.704     ~/a460539eb8e1675c.js (sourcemap at db546cfc014f91ee.js.map, debug id 10a81414-569b-7b16-00ef-b012a1a035bc)
16:09:08.704     ~/a66052790847c9d2.js (sourcemap at 02a02229a85375a8.js.map, debug id cd2a273a-1c52-aed3-ae4d-90bbd3709a74)
16:09:08.704     ~/a6dad97d9634a72d.js (no sourcemap found)
16:09:08.705       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/a6dad97d9634a72d.js)
16:09:08.705     ~/a9883b417e8d40e7.js (sourcemap at 596e3d5bc34ea011.js.map, debug id 2fac8a1c-bde2-cae5-63f2-20b635c26812)
16:09:08.705     ~/aa74dda79f774529.js (sourcemap at 92faaf143e9d1639.js.map, debug id 52efd5eb-6853-23e4-0f50-1e1455e8ea8f)
16:09:08.705     ~/b17fb76c0d5554c3.js (sourcemap at 32278c5bd74c4034.js.map, debug id 14d01a2e-422a-552c-5e5f-a66dc5d6e38b)
16:09:08.705     ~/b5ab7eae7196e084.js (sourcemap at 9420516863e32882.js.map, debug id 61837c14-13db-3d69-742f-18238ce08cfb)
16:09:08.705     ~/bd3369b2bca380f8.js (sourcemap at db2a2eebe72ea40d.js.map, debug id 9a6c01c4-91d3-97a3-d46d-ff52a47d5420)
16:09:08.705     ~/be5d4cc7ce08c747.js (sourcemap at 519b5c98984d296d.js.map, debug id eff95a8e-62cd-2b25-4a26-2212d4914f46)
16:09:08.705     ~/c0ca73ab6299f136.js (sourcemap at 8dc4632c71c0b168.js.map, debug id d8b24662-9b73-34fc-a543-b436daabeb32)
16:09:08.705     ~/c86eed53cd98d3fa.js (sourcemap at 459d596481c845ef.js.map, debug id 831cf680-61b8-6dfc-e949-5dc5fabb19bf)
16:09:08.705     ~/ccc4f38200ec14d6.js (sourcemap at efc9a28101d9deca.js.map, debug id 8e0814f9-8d09-b54d-5888-c2fc759ee723)
16:09:08.706     ~/cddfcbd707579a2a.js (sourcemap at 89d463d684624bc4.js.map, debug id 0dba63cd-0a2d-aa1d-9ba8-8fba5953a11d)
16:09:08.706     ~/d20b998992547b39.js (sourcemap at a4806ec1b423bbb3.js.map, debug id 9d509283-0266-2bfd-a9e3-b87c9968b64b)
16:09:08.706     ~/e5272cb92ad56b9a.js (sourcemap at 92ce7f4d1ff30eca.js.map, debug id bb3057a5-3f20-d828-6915-5b7cf1c953e7)
16:09:08.706     ~/eb945bcf29dfae8e.js (sourcemap at b56bcc9a922b890b.js.map, debug id a356bc01-794e-e172-dd1e-c06c75b36197)
16:09:08.706     ~/ed92a782a4e0b50c.js (sourcemap at 1f4f7c5b3619a497.js.map, debug id 502dbcff-5354-8a9a-fa59-c026f5643a9c)
16:09:08.707     ~/eed7aaff1f45b4f7.js (sourcemap at 03715c2db74e537c.js.map, debug id b55e03f4-5cff-e001-75bf-1ee03040df53)
16:09:08.707     ~/turbopack-ce44e449e30f1a5d.js (sourcemap at efdeb1b804e660d5.js.map, debug id 06431249-5d4f-89e7-fc8f-d2c2ede6a1dc)
16:09:08.707   Source Maps
16:09:08.707     ~/02a02229a85375a8.js.map (debug id cd2a273a-1c52-aed3-ae4d-90bbd3709a74)
16:09:08.707     ~/03715c2db74e537c.js.map (debug id b55e03f4-5cff-e001-75bf-1ee03040df53)
16:09:08.707     ~/0d11bdb1a4200f03.js.map (debug id 6cb5f628-8d1f-d18d-d2d4-30d28d042fa0)
16:09:08.707     ~/1c1b9175e798d4dd.js.map (debug id df5dcc42-a552-7c47-b241-812be16d0566)
16:09:08.707     ~/1f4f7c5b3619a497.js.map (debug id 502dbcff-5354-8a9a-fa59-c026f5643a9c)
16:09:08.707     ~/24f22e5c1a17402d.css.map
16:09:08.707     ~/2ca5a85fd8a2e6ce.js.map (debug id 56305881-d423-2f76-46e2-e4bc2e19f8c8)
16:09:08.707     ~/2f23a2a34f9ea7cf.js.map (debug id e0adc1da-5783-a313-6df9-34f293f861af)
16:09:08.707     ~/32278c5bd74c4034.js.map (debug id 14d01a2e-422a-552c-5e5f-a66dc5d6e38b)
16:09:08.707     ~/3313a3efd5888ecf.js.map (debug id cda6b576-012e-8cfd-3d7a-d188dd6f17ec)
16:09:08.707     ~/35e136cce5c54b58.js.map (debug id ca195ca8-0cc1-cec3-2050-49e87aba214d)
16:09:08.707     ~/37577569f11e55ef.js.map (debug id 1161c45b-2866-ce4e-99b6-56f146312422)
16:09:08.707     ~/459d596481c845ef.js.map (debug id 831cf680-61b8-6dfc-e949-5dc5fabb19bf)
16:09:08.707     ~/519b5c98984d296d.js.map (debug id eff95a8e-62cd-2b25-4a26-2212d4914f46)
16:09:08.707     ~/52fe024d847c3a9f.js.map (debug id 71db69ba-0822-4481-507d-2b0f7438208e)
16:09:08.707     ~/5327ec6de83ef3ff.js.map (debug id 8bd6131c-110c-e6bd-9023-e2339f5a3830)
16:09:08.707     ~/596e3d5bc34ea011.js.map (debug id 2fac8a1c-bde2-cae5-63f2-20b635c26812)
16:09:08.707     ~/5ab05ef1ca23dcb3.js.map (debug id 3523e392-aaaa-8919-c86f-2889c8497c0b)
16:09:08.707     ~/6f4430f1e4cffe3f.js.map (debug id 7df5e1f7-5aa9-20d8-bb7a-395193f8a697)
16:09:08.707     ~/735e63492633a6f5.js.map (debug id 90874f72-c07b-f49e-bb37-fa47d686bc49)
16:09:08.708     ~/7820c02cd5c58874.js.map (debug id 39995e43-d677-9cdb-9c20-02bb591d8b41)
16:09:08.708     ~/89d463d684624bc4.js.map (debug id 0dba63cd-0a2d-aa1d-9ba8-8fba5953a11d)
16:09:08.708     ~/8b055edd7eaad111.js.map (debug id 96722136-1237-eff8-fe4b-45a0a1366d54)
16:09:08.708     ~/8dc4632c71c0b168.js.map (debug id d8b24662-9b73-34fc-a543-b436daabeb32)
16:09:08.708     ~/9151782e8638b1ac.js.map (debug id 62cd6d38-9e2a-7a4d-e380-cf29325e730b)
16:09:08.708     ~/92c11afe64a0dc60.js.map (debug id 5d30fa8b-6ba0-f1b1-1371-854d15308f2e)
16:09:08.708     ~/92ce7f4d1ff30eca.js.map (debug id bb3057a5-3f20-d828-6915-5b7cf1c953e7)
16:09:08.708     ~/92faaf143e9d1639.js.map (debug id 52efd5eb-6853-23e4-0f50-1e1455e8ea8f)
16:09:08.708     ~/9420516863e32882.js.map (debug id 61837c14-13db-3d69-742f-18238ce08cfb)
16:09:08.708     ~/9c6d4874507cac84.js.map (debug id 8aff9036-6db1-5ada-4e69-a0c7c807624f)
16:09:08.708     ~/a09f918ff247f735.js.map (debug id ee50e671-c0e7-0728-346c-c97dcdb5de5e)
16:09:08.708     ~/a4806ec1b423bbb3.js.map (debug id 9d509283-0266-2bfd-a9e3-b87c9968b64b)
16:09:08.708     ~/aa6d98dbf2485283.js.map (debug id 251ad38f-1a47-360b-f0a8-8c7b858f639a)
16:09:08.708     ~/b56bcc9a922b890b.js.map (debug id a356bc01-794e-e172-dd1e-c06c75b36197)
16:09:08.708     ~/b771ef2d58d400e2.js.map (debug id 2ea6c79e-a799-24cd-873b-b67c7aa76f52)
16:09:08.708     ~/c2689ee959a21033.js.map (debug id a535dedf-4774-a3ad-e4d0-902a14df764d)
16:09:08.708     ~/c98e6720b52c307a.js.map (debug id 6600690c-c509-c4de-e211-be01b778f681)
16:09:08.708     ~/cc163944161d7df2.js.map (debug id 489e6cce-5782-849a-a392-6805499a39aa)
16:09:08.708     ~/cd8e721ba72bfed4.js.map (debug id 8c344ed8-634b-600f-f4af-9d8c11543185)
16:09:08.708     ~/d58fb72b8734f61c.js.map (debug id a871dead-25fb-7f19-bbd2-18e3dc150daf)
16:09:08.708     ~/d59388c26f9ae249.js.map (debug id 525891db-6320-0aab-83d2-a4be750038da)
16:09:08.708     ~/d8f5b521e2c9e9c9.js.map (debug id 2aadde59-4158-2286-1c74-09dfee21ce9a)
16:09:08.708     ~/db2a2eebe72ea40d.js.map (debug id 9a6c01c4-91d3-97a3-d46d-ff52a47d5420)
16:09:08.708     ~/db546cfc014f91ee.js.map (debug id 10a81414-569b-7b16-00ef-b012a1a035bc)
16:09:08.708     ~/ee148d8b219c927a.js.map (debug id c96e7fdc-6775-3e9c-ab7c-a96aa19ec54b)
16:09:08.709     ~/efc9a28101d9deca.js.map (debug id 8e0814f9-8d09-b54d-5888-c2fc759ee723)
16:09:08.709     ~/efdeb1b804e660d5.js.map (debug id 06431249-5d4f-89e7-fc8f-d2c2ede6a1dc)
16:09:08.709     ~/f3712fa2caa675d6.js.map (debug id c972c207-4054-da88-4399-ba75cd2e92d3)
16:09:08.709     ~/fbf21dc5aab181ee.js.map (debug id f5f1832c-49e7-9147-139c-d5b79439cdfd)
16:09:08.709     ~/ff2289e6ca6b1786.js.map (debug id eb6b1e70-aba2-de5c-e3a0-2e7417f6df3e)
16:09:08.762 > Bundling completed in 2.278s
16:09:08.763 > Bundled 430 files for upload
16:09:08.763 > Bundle ID: 6680efd8-6ba8-51ba-a3be-3f1393d6d022
16:09:08.818 > Optimizing completed in 0.055s
16:09:11.688 > Uploading completed in 2.527s
16:09:11.688 > Uploaded files to Sentry
16:09:12.046 > Processing completed in 0.357s
16:09:12.046 > File upload complete (processing pending on server)
16:09:12.046 > Organization: fittechs
16:09:12.046 > Projects: axiohub-frontend
16:09:12.046 > Release: 1dd911b2ab79f07fb13becfadbfa65abbf89edad
16:09:12.046 > Dist: None
16:09:12.046 > Upload type: artifact bundle
16:09:12.049 
16:09:12.049 Source Map Upload Report
16:09:12.049   Scripts
16:09:12.049     ~/app/(auth)/forgot-password/page.js (sourcemap at page.js.map)
16:09:12.049     ~/app/(auth)/forgot-password/page_client-reference-manifest.js (no sourcemap found)
16:09:12.049       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/(auth)/forgot-password/page_client-reference-manifest.js)
16:09:12.049     ~/app/(auth)/login/page.js (sourcemap at page.js.map)
16:09:12.049     ~/app/(auth)/login/page_client-reference-manifest.js (no sourcemap found)
16:09:12.049       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/(auth)/login/page_client-reference-manifest.js)
16:09:12.049     ~/app/(auth)/register/page.js (sourcemap at page.js.map)
16:09:12.049     ~/app/(auth)/register/page_client-reference-manifest.js (no sourcemap found)
16:09:12.049       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/(auth)/register/page_client-reference-manifest.js)
16:09:12.049     ~/app/(marketing)/legal/[slug]/page.js (sourcemap at page.js.map)
16:09:12.049     ~/app/(marketing)/legal/[slug]/page_client-reference-manifest.js (no sourcemap found)
16:09:12.049       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/(marketing)/legal/[slug]/page_client-reference-manifest.js)
16:09:12.049     ~/app/_global-error/page.js (sourcemap at page.js.map)
16:09:12.049     ~/app/_global-error/page_client-reference-manifest.js (no sourcemap found)
16:09:12.049       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/_global-error/page_client-reference-manifest.js)
16:09:12.050     ~/app/_not-found/page.js (sourcemap at page.js.map)
16:09:12.050     ~/app/_not-found/page_client-reference-manifest.js (no sourcemap found)
16:09:12.050       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/_not-found/page_client-reference-manifest.js)
16:09:12.050     ~/app/auth/callback/route.js (sourcemap at route.js.map)
16:09:12.050     ~/app/auth/callback/route_client-reference-manifest.js (no sourcemap found)
16:09:12.050       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/auth/callback/route_client-reference-manifest.js)
16:09:12.050     ~/app/auth/reset-password/page.js (sourcemap at page.js.map)
16:09:12.050     ~/app/auth/reset-password/page_client-reference-manifest.js (no sourcemap found)
16:09:12.050       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/auth/reset-password/page_client-reference-manifest.js)
16:09:12.050     ~/app/dashboard/chat/[chatId]/page.js (sourcemap at page.js.map)
16:09:12.050     ~/app/dashboard/chat/[chatId]/page_client-reference-manifest.js (no sourcemap found)
16:09:12.050       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/chat/[chatId]/page_client-reference-manifest.js)
16:09:12.050     ~/app/dashboard/documents/page.js (sourcemap at page.js.map)
16:09:12.050     ~/app/dashboard/documents/page_client-reference-manifest.js (no sourcemap found)
16:09:12.050       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/documents/page_client-reference-manifest.js)
16:09:12.050     ~/app/dashboard/help/[slug]/page.js (sourcemap at page.js.map)
16:09:12.050     ~/app/dashboard/help/[slug]/page_client-reference-manifest.js (no sourcemap found)
16:09:12.050       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/help/[slug]/page_client-reference-manifest.js)
16:09:12.050     ~/app/dashboard/help/page.js (sourcemap at page.js.map)
16:09:12.050     ~/app/dashboard/help/page_client-reference-manifest.js (no sourcemap found)
16:09:12.050       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/help/page_client-reference-manifest.js)
16:09:12.050     ~/app/dashboard/page.js (sourcemap at page.js.map)
16:09:12.050     ~/app/dashboard/page_client-reference-manifest.js (no sourcemap found)
16:09:12.050       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/page_client-reference-manifest.js)
16:09:12.050     ~/app/dashboard/settings/billing/page.js (sourcemap at page.js.map)
16:09:12.050     ~/app/dashboard/settings/billing/page_client-reference-manifest.js (no sourcemap found)
16:09:12.050       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/settings/billing/page_client-reference-manifest.js)
16:09:12.050     ~/app/dashboard/settings/data-sources/page.js (sourcemap at page.js.map)
16:09:12.050     ~/app/dashboard/settings/data-sources/page_client-reference-manifest.js (no sourcemap found)
16:09:12.051       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/settings/data-sources/page_client-reference-manifest.js)
16:09:12.051     ~/app/dashboard/settings/failed-tasks/page.js (sourcemap at page.js.map)
16:09:12.051     ~/app/dashboard/settings/failed-tasks/page_client-reference-manifest.js (no sourcemap found)
16:09:12.051       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/settings/failed-tasks/page_client-reference-manifest.js)
16:09:12.051     ~/app/dashboard/settings/general/page.js (sourcemap at page.js.map)
16:09:12.051     ~/app/dashboard/settings/general/page_client-reference-manifest.js (no sourcemap found)
16:09:12.051       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/settings/general/page_client-reference-manifest.js)
16:09:12.051     ~/app/dashboard/settings/knowledge-base/page.js (sourcemap at page.js.map)
16:09:12.051     ~/app/dashboard/settings/knowledge-base/page_client-reference-manifest.js (no sourcemap found)
16:09:12.051       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/settings/knowledge-base/page_client-reference-manifest.js)
16:09:12.051     ~/app/dashboard/settings/notifications/page.js (sourcemap at page.js.map)
16:09:12.051     ~/app/dashboard/settings/notifications/page_client-reference-manifest.js (no sourcemap found)
16:09:12.051       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/settings/notifications/page_client-reference-manifest.js)
16:09:12.051     ~/app/dashboard/settings/page.js (sourcemap at page.js.map)
16:09:12.052     ~/app/dashboard/settings/page_client-reference-manifest.js (no sourcemap found)
16:09:12.052       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/settings/page_client-reference-manifest.js)
16:09:12.052     ~/app/dashboard/settings/team/page.js (sourcemap at page.js.map)
16:09:12.052     ~/app/dashboard/settings/team/page_client-reference-manifest.js (no sourcemap found)
16:09:12.052       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/dashboard/settings/team/page_client-reference-manifest.js)
16:09:12.052     ~/app/favicon.ico/route.js (sourcemap at route.js.map)
16:09:12.052     ~/app/invite/[token]/page.js (sourcemap at page.js.map)
16:09:12.052     ~/app/invite/[token]/page_client-reference-manifest.js (no sourcemap found)
16:09:12.052       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/invite/[token]/page_client-reference-manifest.js)
16:09:12.052     ~/app/oauth/callback/page.js (sourcemap at page.js.map)
16:09:12.052     ~/app/oauth/callback/page_client-reference-manifest.js (no sourcemap found)
16:09:12.052       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/oauth/callback/page_client-reference-manifest.js)
16:09:12.052     ~/app/page.js (sourcemap at page.js.map)
16:09:12.052     ~/app/page_client-reference-manifest.js (no sourcemap found)
16:09:12.052       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/app/page_client-reference-manifest.js)
16:09:12.052     ~/chunks/13956_build_esm_detectors_platform_node_machine-id_getMachineId-linux_0c68c229.js (sourcemap at 13956_build_esm_detectors_platform_node_machine-id_getMachineId-linux_0c68c229.js.map, debug id f7b0e6ea-26dc-10ad-ad8c-115697123160)
16:09:12.052     ~/chunks/13956_build_esm_detectors_platform_node_machine-id_getMachineId-unsupported_236ca858.js (sourcemap at 13956_build_esm_detectors_platform_node_machine-id_getMachineId-unsupported_236ca858.js.map, debug id e56edd19-6895-87f3-b482-010601eed038)
16:09:12.052     ~/chunks/1da7c_7c615a46._.js (sourcemap at 1da7c_7c615a46._.js.map, debug id 6dc4e3e2-8442-a7f5-b181-c0df6db52521)
16:09:12.052     ~/chunks/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_a6e355df._.js (sourcemap at 1da7c_%40opentelemetry_resources_build_esm_detectors_platform_node_machine-id_a6e355df._.js.map, debug id 5544189a-ee47-c8ed-3bbc-1b44a228c142)
16:09:12.052     ~/chunks/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_b2241ed2._.js (sourcemap at 1da7c_%40opentelemetry_resources_build_esm_detectors_platform_node_machine-id_b2241ed2._.js.map, debug id fc89a005-6f20-a4f6-597c-35a271f82211)
16:09:12.052     ~/chunks/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_fbf9b753._.js (sourcemap at 1da7c_%40opentelemetry_resources_build_esm_detectors_platform_node_machine-id_fbf9b753._.js.map, debug id d7be5e49-86d3-96d5-026b-151dd91f92a3)
16:09:12.053     ~/chunks/1da7c_c5d00c00._.js (sourcemap at 1da7c_c5d00c00._.js.map, debug id 4fc69fbd-84c6-b7b8-4c16-f6251b668b19)
16:09:12.053     ~/chunks/1da7c_next_dist_esm_build_templates_app-route_cf5e7020.js (sourcemap at 1da7c_next_dist_esm_build_templates_app-route_cf5e7020.js.map, debug id 1e220094-b07c-f67f-c6e0-5ee454416b46)
16:09:12.053     ~/chunks/[externals]_node:inspector_7a4283c6._.js (sourcemap at %5Bexternals%5D_node%3Ainspector_7a4283c6._.js.map, debug id bbb7096f-41e0-233c-11dd-d03d0fc428b4)
16:09:12.053     ~/chunks/[root-of-the-server]__28821955._.js (sourcemap at %5Broot-of-the-server%5D__28821955._.js.map, debug id 2c5f937c-db64-4f5b-a0c5-6cef48d8c041)
16:09:12.053     ~/chunks/[root-of-the-server]__86eb7852._.js (sourcemap at %5Broot-of-the-server%5D__86eb7852._.js.map, debug id 0f42ff8e-f625-236f-a8ea-df6c00c689fd)
16:09:12.053     ~/chunks/[root-of-the-server]__ab52b825._.js (sourcemap at %5Broot-of-the-server%5D__ab52b825._.js.map, debug id 0a4e70a7-dd05-a9be-b594-7c7699031a06)
16:09:12.053     ~/chunks/[root-of-the-server]__b89b5a39._.js (sourcemap at %5Broot-of-the-server%5D__b89b5a39._.js.map, debug id 5ac8d800-056e-59bb-275e-a2f608c27d4d)
16:09:12.053     ~/chunks/[root-of-the-server]__b8d37178._.js (sourcemap at %5Broot-of-the-server%5D__b8d37178._.js.map, debug id 6461ebce-e6ed-7298-fb07-275ceff12363)
16:09:12.053     ~/chunks/[turbopack]_runtime.js (sourcemap at %5Bturbopack%5D_runtime.js.map)
16:09:12.053     ~/chunks/frontend-new__next-internal_server_app_auth_callback_route_actions_8ffb3c0e.js (sourcemap at frontend-new__next-internal_server_app_auth_callback_route_actions_8ffb3c0e.js.map, debug id c94eda45-421e-10e9-fb1e-d78bf7fa4ede)
16:09:12.053     ~/chunks/frontend-new__next-internal_server_app_favicon_ico_route_actions_fa397e36.js (sourcemap at frontend-new__next-internal_server_app_favicon_ico_route_actions_fa397e36.js.map, debug id d412fe64-89fc-adf4-7d0a-61c597ca21ed)
16:09:12.053     ~/chunks/frontend-new_sentry_server_config_ts_fb78c4fb._.js (sourcemap at frontend-new_sentry_server_config_ts_fb78c4fb._.js.map, debug id c5291ba3-0de6-1e2a-cdfe-180faa98bae9)
16:09:12.053     ~/chunks/ssr/13956_build_esm_detectors_platform_node_machine-id_getMachineId-linux_d7cb7675.js (sourcemap at 13956_build_esm_detectors_platform_node_machine-id_getMachineId-linux_d7cb7675.js.map, debug id 0478fb4e-6b4a-e2d1-d28f-cc566114ce72)
16:09:12.053     ~/chunks/ssr/13956_build_esm_detectors_platform_node_machine-id_getMachineId-unsupported_8b7aecf9.js (sourcemap at 13956_build_esm_detectors_platform_node_machine-id_getMachineId-unsupported_8b7aecf9.js.map, debug id e6b7b94e-af54-5ad3-79d3-c78671fc687e)
16:09:12.053     ~/chunks/ssr/1da7c_02c30ede._.js (sourcemap at 1da7c_02c30ede._.js.map, debug id 9a79e254-72c9-ad22-c6af-c4e3534b74d7)
16:09:12.053     ~/chunks/ssr/1da7c_4c86d122._.js (sourcemap at 1da7c_4c86d122._.js.map, debug id 12549ee1-ffb5-c3d5-f0fd-0b11b3b7646b)
16:09:12.053     ~/chunks/ssr/1da7c_4d71bfb8._.js (sourcemap at 1da7c_4d71bfb8._.js.map, debug id af6c83bf-9aaf-2775-0247-a8d34202b9ab)
16:09:12.053     ~/chunks/ssr/1da7c_4e0e3f3b._.js (sourcemap at 1da7c_4e0e3f3b._.js.map, debug id a06b1047-0d13-fc44-c281-e65786da5d4d)
16:09:12.053     ~/chunks/ssr/1da7c_4f6772db._.js (sourcemap at 1da7c_4f6772db._.js.map, debug id 0bc098a3-e482-e0f6-b226-fea88cf42fa1)
16:09:12.053     ~/chunks/ssr/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_0dcef83c._.js (sourcemap at 1da7c_%40opentelemetry_resources_build_esm_detectors_platform_node_machine-id_0dcef83c._.js.map, debug id b1c4d787-22cf-f572-fb67-7aba2b9c0e96)
16:09:12.053     ~/chunks/ssr/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_75c9de92._.js (sourcemap at 1da7c_%40opentelemetry_resources_build_esm_detectors_platform_node_machine-id_75c9de92._.js.map, debug id 587a9a6c-27cd-aada-3044-40d66007f228)
16:09:12.053     ~/chunks/ssr/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_9da8d312._.js (sourcemap at 1da7c_%40opentelemetry_resources_build_esm_detectors_platform_node_machine-id_9da8d312._.js.map, debug id 0fe9877a-53bc-ad33-f005-6952b9f10b78)
16:09:12.054     ~/chunks/ssr/1da7c_@radix-ui_react-popper_dist_index_mjs_2ad58864._.js (sourcemap at 1da7c_%40radix-ui_react-popper_dist_index_mjs_2ad58864._.js.map, debug id f75e849f-918d-49ca-ec38-8c15afb789aa)
16:09:12.054     ~/chunks/ssr/1da7c_@radix-ui_react-tooltip_dist_index_mjs_99b0816e._.js (sourcemap at 1da7c_%40radix-ui_react-tooltip_dist_index_mjs_99b0816e._.js.map, debug id 4e1901d3-ebee-8577-acf4-bbe6a92f9f71)
16:09:12.054     ~/chunks/ssr/1da7c_@tanstack_8c5fe470._.js (sourcemap at 1da7c_%40tanstack_8c5fe470._.js.map, debug id ad959641-353f-5e1e-36b8-1f3677e7d7a6)
16:09:12.054     ~/chunks/ssr/1da7c_@tanstack_react-query_build_modern_useQuery_0140a44e.js (sourcemap at 1da7c_%40tanstack_react-query_build_modern_useQuery_0140a44e.js.map, debug id adf7b1ee-a6f6-7f2d-f605-13d39ece08a9)
16:09:12.054     ~/chunks/ssr/1da7c_b3dbce65._.js (sourcemap at 1da7c_b3dbce65._.js.map, debug id 4e3ed1d1-f9af-4cdc-d4b3-8751bb2fe8f4)
16:09:12.054     ~/chunks/ssr/1da7c_lucide-react_dist_esm_icons_1e752d28._.js (sourcemap at 1da7c_lucide-react_dist_esm_icons_1e752d28._.js.map, debug id 5f8014d8-909f-ee30-56f4-b2d2368bca5c)
16:09:12.054     ~/chunks/ssr/1da7c_lucide-react_dist_esm_icons_f8bc5ecc._.js (sourcemap at 1da7c_lucide-react_dist_esm_icons_f8bc5ecc._.js.map, debug id d0093865-370c-fe68-321a-39eebb41eb43)
16:09:12.054     ~/chunks/ssr/1da7c_lucide-react_dist_esm_icons_settings_41516ee0.js (sourcemap at 1da7c_lucide-react_dist_esm_icons_settings_41516ee0.js.map, debug id cb2bf54a-f11f-aaec-c8e6-b83912856ba4)
16:09:12.054     ~/chunks/ssr/1da7c_next_b8ad55ac._.js (sourcemap at 1da7c_next_b8ad55ac._.js.map, debug id 3761de60-e420-50d8-7f74-2e17c960d7d2)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_0784f779._.js (sourcemap at 1da7c_next_dist_0784f779._.js.map, debug id 89b44f04-bf68-d93f-1e4a-4f7daed1fdb9)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_0b11b2c7._.js (sourcemap at 1da7c_next_dist_0b11b2c7._.js.map, debug id 7d69a2c4-52ef-a0ac-cef2-bd63f5282874)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_2d90c7b2._.js (sourcemap at 1da7c_next_dist_2d90c7b2._.js.map, debug id 78730bf9-7234-5a26-7cbd-31ef1c2f8bc0)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_67b842e4._.js (sourcemap at 1da7c_next_dist_67b842e4._.js.map, debug id 50735cf4-920f-a020-d091-f109b0fc2663)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_8f122843._.js (sourcemap at 1da7c_next_dist_8f122843._.js.map, debug id 89f95fec-0fce-b464-4cdf-56d6620d28e1)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_client_components_07c4e3fe._.js (sourcemap at 1da7c_next_dist_client_components_07c4e3fe._.js.map, debug id 960f1f32-b0e5-a644-60cb-a618fcf4b0ef)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_client_components_builtin_forbidden_26e2a1e5.js (sourcemap at 1da7c_next_dist_client_components_builtin_forbidden_26e2a1e5.js.map, debug id bf037b3c-1eeb-9de0-7cbe-c36fe92b9503)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_client_components_builtin_unauthorized_fc936f1d.js (sourcemap at 1da7c_next_dist_client_components_builtin_unauthorized_fc936f1d.js.map, debug id c67f12bb-04f7-9e5e-d079-7ae4373ef467)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_esm_02b5ba7f._.js (sourcemap at 1da7c_next_dist_esm_02b5ba7f._.js.map, debug id 0561f801-c778-35fb-aa54-2fb54a89231d)
16:09:12.054     ~/chunks/ssr/1da7c_next_dist_esm_build_templates_app-page_e2c916d2.js (sourcemap at 1da7c_next_dist_esm_build_templates_app-page_e2c916d2.js.map, debug id ed0d1924-6533-4b94-f3bf-b4965cf6d209)
16:09:12.054     ~/chunks/ssr/1da7c_react-hook-form_dist_index_esm_mjs_8a10e602._.js (sourcemap at 1da7c_react-hook-form_dist_index_esm_mjs_8a10e602._.js.map, debug id e85ad3bc-3786-5dd9-2291-c6ae639c9efa)
16:09:12.054     ~/chunks/ssr/1da7c_sonner_dist_index_mjs_d5937113._.js (sourcemap at 1da7c_sonner_dist_index_mjs_d5937113._.js.map, debug id e93f3333-1251-6857-4812-778586e3d3e1)
16:09:12.054     ~/chunks/ssr/6118d__next-internal_server_app_(auth)_forgot-password_page_actions_5987a920.js (sourcemap at 6118d__next-internal_server_app_%28auth%29_forgot-password_page_actions_5987a920.js.map, debug id 94458ad6-2127-ca43-b978-bd22b8c2cda3)
16:09:12.055     ~/chunks/ssr/6118d__next-internal_server_app_(marketing)_legal_[slug]_page_actions_3cf8ff4f.js (sourcemap at 6118d__next-internal_server_app_%28marketing%29_legal_%5Bslug%5D_page_actions_3cf8ff4f.js.map, debug id 2ddead6e-590a-dafd-14f2-283721df85b6)
16:09:12.055     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_chat_[chatId]_page_actions_40693ad0.js (sourcemap at 6118d__next-internal_server_app_dashboard_chat_%5BchatId%5D_page_actions_40693ad0.js.map, debug id e8d590b4-07db-9f12-2992-3eef4f5d0965)
16:09:12.055     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_help_[slug]_page_actions_6a786b56.js (sourcemap at 6118d__next-internal_server_app_dashboard_help_%5Bslug%5D_page_actions_6a786b56.js.map, debug id e9c10803-deb6-4d0d-b34d-bcc515ceb2b0)
16:09:12.055     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_billing_page_actions_fe756f85.js (sourcemap at 6118d__next-internal_server_app_dashboard_settings_billing_page_actions_fe756f85.js.map, debug id f8983a4f-1daf-07a7-1205-6b3989ffd77a)
16:09:12.055     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_data-sources_page_actions_0cd33e5c.js (sourcemap at 6118d__next-internal_server_app_dashboard_settings_data-sources_page_actions_0cd33e5c.js.map, debug id b1e243cb-7aaa-c93b-fa68-18c3af0059d0)
16:09:12.055     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_failed-tasks_page_actions_aafc47d7.js (sourcemap at 6118d__next-internal_server_app_dashboard_settings_failed-tasks_page_actions_aafc47d7.js.map, debug id 66f0e749-3623-9879-a3f8-bcf8e7c6301e)
16:09:12.055     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_general_page_actions_e1e78074.js (sourcemap at 6118d__next-internal_server_app_dashboard_settings_general_page_actions_e1e78074.js.map, debug id d8e16f8f-d509-ecb5-d617-32a5bd64653d)
16:09:12.055     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_team_page_actions_95695693.js (sourcemap at 6118d__next-internal_server_app_dashboard_settings_team_page_actions_95695693.js.map, debug id 78a5921e-c12d-caae-ed1a-5d9c168d49f1)
16:09:12.055     ~/chunks/ssr/734e0_next-internal_server_app_dashboard_settings_notifications_page_actions_e7b69ca9.js (sourcemap at 734e0_next-internal_server_app_dashboard_settings_notifications_page_actions_e7b69ca9.js.map, debug id b313af24-f985-e07e-4e5f-8466d5a95d2f)
16:09:12.055     ~/chunks/ssr/[externals]_node:inspector_7a4283c6._.js (sourcemap at %5Bexternals%5D_node%3Ainspector_7a4283c6._.js.map, debug id 5f41589b-d010-1718-2c15-d0250c8535f0)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__088fb375._.js (sourcemap at %5Broot-of-the-server%5D__088fb375._.js.map, debug id 4a955a23-1506-40e5-ae46-89850e7f5d15)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__0d8abd2f._.js (sourcemap at %5Broot-of-the-server%5D__0d8abd2f._.js.map, debug id 835699c9-5554-4715-8aa4-27b61ea7cfd4)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__0d919162._.js (sourcemap at %5Broot-of-the-server%5D__0d919162._.js.map, debug id cba992e2-3cbf-0e58-9d58-4d45ad91d591)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__100aa689._.js (sourcemap at %5Broot-of-the-server%5D__100aa689._.js.map, debug id 01f197d7-516c-3394-c11a-3b5725fec01f)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__15bbd683._.js (sourcemap at %5Broot-of-the-server%5D__15bbd683._.js.map, debug id d2d7690d-27bc-ad87-0002-ff9e48d6082f)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__25125dc0._.js (sourcemap at %5Broot-of-the-server%5D__25125dc0._.js.map, debug id 6ae4e90e-e19e-a9af-7355-58bc210456ea)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__3098c850._.js (sourcemap at %5Broot-of-the-server%5D__3098c850._.js.map, debug id fec378ad-6fa5-5d5a-87e0-40269e70fee8)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__36728547._.js (sourcemap at %5Broot-of-the-server%5D__36728547._.js.map, debug id 69ca096f-a705-2f8a-8a86-f3b8041dc693)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__3c59eab8._.js (sourcemap at %5Broot-of-the-server%5D__3c59eab8._.js.map, debug id 91636e71-7a03-9418-1b9d-9f72a83f7929)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__3edaf77c._.js (sourcemap at %5Broot-of-the-server%5D__3edaf77c._.js.map, debug id 0348ed2d-672e-ad6c-1397-2d6aea4a0630)
16:09:12.055     ~/chunks/ssr/[root-of-the-server]__45909684._.js (sourcemap at %5Broot-of-the-server%5D__45909684._.js.map, debug id 283ee66b-13e0-55fd-a206-cc3beef83f58)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__4f0f17b1._.js (sourcemap at %5Broot-of-the-server%5D__4f0f17b1._.js.map, debug id 6b756fc8-eb3d-e3bd-eb2c-44ec533238ef)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__5565b0cd._.js (sourcemap at %5Broot-of-the-server%5D__5565b0cd._.js.map, debug id 77eebf94-738b-bb17-3ce9-4de8fbc47642)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__59b47646._.js (sourcemap at %5Broot-of-the-server%5D__59b47646._.js.map, debug id dd2fe526-0217-014d-061d-8497ffc4e625)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__835c65ab._.js (sourcemap at %5Broot-of-the-server%5D__835c65ab._.js.map, debug id 9520d7dc-aae1-da92-c84f-931ad8c057ad)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__8609e7f2._.js (sourcemap at %5Broot-of-the-server%5D__8609e7f2._.js.map, debug id e6255368-6d13-87e8-6a2f-1b58bdd0ed2d)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__92e09ac8._.js (sourcemap at %5Broot-of-the-server%5D__92e09ac8._.js.map, debug id 2f6df708-afe1-9f5f-0353-02bd08a5c196)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__a2f492bb._.js (sourcemap at %5Broot-of-the-server%5D__a2f492bb._.js.map, debug id 046f0a37-4d9e-9ff4-28d0-1f9f7e26e6e2)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__a347a19c._.js (sourcemap at %5Broot-of-the-server%5D__a347a19c._.js.map, debug id 92142c05-a98a-563f-a0b1-5672afebaa6b)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__a3b992f9._.js (sourcemap at %5Broot-of-the-server%5D__a3b992f9._.js.map, debug id 87908fee-b663-e23e-43c4-af3c3e2acdc6)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__aac6418c._.js (sourcemap at %5Broot-of-the-server%5D__aac6418c._.js.map, debug id 3d086d99-0a50-e46a-4a86-e20ce33a27d5)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__b098f0e0._.js (sourcemap at %5Broot-of-the-server%5D__b098f0e0._.js.map, debug id 0f7248c5-3418-5089-cd9e-3f696ae02202)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__b4c43e30._.js (sourcemap at %5Broot-of-the-server%5D__b4c43e30._.js.map, debug id 6139d6d5-bffc-79ee-d527-fb6bb964df02)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__b6781b6d._.js (sourcemap at %5Broot-of-the-server%5D__b6781b6d._.js.map, debug id 3b581610-e733-35f5-31aa-98c1d9ba3d2c)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__bfa3f14c._.js (sourcemap at %5Broot-of-the-server%5D__bfa3f14c._.js.map, debug id 158a826f-414f-ab7e-d174-166a11089e92)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__c6a529a4._.js (sourcemap at %5Broot-of-the-server%5D__c6a529a4._.js.map, debug id 5214b15e-4eee-9ffa-3832-30137a8ddcd4)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__cc584089._.js (sourcemap at %5Broot-of-the-server%5D__cc584089._.js.map, debug id a68b8ab5-89c0-6ddc-e572-d00412a136a0)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__d3064e36._.js (sourcemap at %5Broot-of-the-server%5D__d3064e36._.js.map, debug id 05550f9e-89e5-c5e5-07f6-6ac50d7bc7ba)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__d7f121f9._.js (sourcemap at %5Broot-of-the-server%5D__d7f121f9._.js.map, debug id 6834336f-8006-58db-7197-43b930ee235d)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__d8026068._.js (sourcemap at %5Broot-of-the-server%5D__d8026068._.js.map, debug id caa9f4d4-0838-1ef4-69d7-9148d141eb3f)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__ef46dcb6._.js (sourcemap at %5Broot-of-the-server%5D__ef46dcb6._.js.map, debug id 43d68aeb-4cf8-01b1-656e-187c5d025a00)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__f0bfff96._.js (sourcemap at %5Broot-of-the-server%5D__f0bfff96._.js.map, debug id de7f1532-454a-d51a-08ba-c7fecde2c966)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__f48f4b27._.js (sourcemap at %5Broot-of-the-server%5D__f48f4b27._.js.map, debug id 679fe6ac-2345-8e4f-767b-ef6650cab38c)
16:09:12.056     ~/chunks/ssr/[root-of-the-server]__fc451734._.js (sourcemap at %5Broot-of-the-server%5D__fc451734._.js.map, debug id 30939323-861b-9b62-3924-e5d4d2cd7e67)
16:09:12.057     ~/chunks/ssr/[turbopack]_runtime.js (sourcemap at %5Bturbopack%5D_runtime.js.map)
16:09:12.057     ~/chunks/ssr/e66f5_server_app_dashboard_settings_knowledge-base_page_actions_a0f98f9c.js (sourcemap at e66f5_server_app_dashboard_settings_knowledge-base_page_actions_a0f98f9c.js.map, debug id 6aed5621-da6d-8be1-8d53-acd0d5852132)
16:09:12.057     ~/chunks/ssr/frontend-new_00172161._.js (sourcemap at frontend-new_00172161._.js.map, debug id 77a7bcbc-429b-55a0-45cf-744dc14d3119)
16:09:12.057     ~/chunks/ssr/frontend-new_0580cb9d._.js (sourcemap at frontend-new_0580cb9d._.js.map, debug id bbad3e47-b22b-d8d2-9df2-1d8043b9777e)
16:09:12.057     ~/chunks/ssr/frontend-new_06074e2d._.js (sourcemap at frontend-new_06074e2d._.js.map, debug id 99640d64-2a5a-4418-a45d-3056562cdf01)
16:09:12.057     ~/chunks/ssr/frontend-new_0cb4b52a._.js (sourcemap at frontend-new_0cb4b52a._.js.map, debug id b40008da-acc2-a0e4-678f-6eeeb3f2a6a5)
16:09:12.058     ~/chunks/ssr/frontend-new_1d164b28._.js (sourcemap at frontend-new_1d164b28._.js.map, debug id 0c06fcb8-3b4c-e25c-a0ca-66cd928aceb2)
16:09:12.058     ~/chunks/ssr/frontend-new_1dc726f5._.js (sourcemap at frontend-new_1dc726f5._.js.map, debug id e690c603-c242-4f44-8fc7-79a24a907106)
16:09:12.058     ~/chunks/ssr/frontend-new_1ff8f695._.js (sourcemap at frontend-new_1ff8f695._.js.map, debug id 5025b9eb-9b48-c10c-ca20-099de48e1834)
16:09:12.058     ~/chunks/ssr/frontend-new_289f075e._.js (sourcemap at frontend-new_289f075e._.js.map, debug id 0d45eeb5-1d2b-edd2-fa73-1203c7f5d7a7)
16:09:12.058     ~/chunks/ssr/frontend-new_2975814d._.js (sourcemap at frontend-new_2975814d._.js.map, debug id d49a43a0-9bb5-f3d5-6ec2-9d53ea38adf9)
16:09:12.058     ~/chunks/ssr/frontend-new_32816aee._.js (sourcemap at frontend-new_32816aee._.js.map, debug id fff4ef7a-0822-c400-d972-69383df76c81)
16:09:12.058     ~/chunks/ssr/frontend-new_35897e86._.js (sourcemap at frontend-new_35897e86._.js.map, debug id 2cb81a34-d3f4-119d-e39e-d8d922c7f94e)
16:09:12.058     ~/chunks/ssr/frontend-new_36cff9b1._.js (sourcemap at frontend-new_36cff9b1._.js.map, debug id 1ad335e2-1e3e-4c95-1add-f858f9402aba)
16:09:12.058     ~/chunks/ssr/frontend-new_469c2c8f._.js (sourcemap at frontend-new_469c2c8f._.js.map, debug id 999588d8-9f1a-0dcf-d09e-561f307100ba)
16:09:12.058     ~/chunks/ssr/frontend-new_56fc1bec._.js (sourcemap at frontend-new_56fc1bec._.js.map, debug id 15af6a82-494a-5b0c-754a-84eb0a1e0583)
16:09:12.058     ~/chunks/ssr/frontend-new_5f017408._.js (sourcemap at frontend-new_5f017408._.js.map, debug id a416313d-7d15-1215-8d89-50166c5481c9)
16:09:12.058     ~/chunks/ssr/frontend-new_619ead6a._.js (sourcemap at frontend-new_619ead6a._.js.map, debug id 8fca85c2-347d-7454-f618-f30543dfe5e1)
16:09:12.058     ~/chunks/ssr/frontend-new_6bf15c89._.js (sourcemap at frontend-new_6bf15c89._.js.map, debug id 1a0c47b9-c899-c60f-24cc-e2a971be3b46)
16:09:12.058     ~/chunks/ssr/frontend-new_707ef70a._.js (sourcemap at frontend-new_707ef70a._.js.map, debug id a3fcb60b-a9e9-bfdc-43c4-d6f669cb458c)
16:09:12.058     ~/chunks/ssr/frontend-new_769c2d97._.js (sourcemap at frontend-new_769c2d97._.js.map, debug id 60ebc8d2-5c6d-b3f8-c0a7-c06da23f013d)
16:09:12.058     ~/chunks/ssr/frontend-new_7f90c052._.js (sourcemap at frontend-new_7f90c052._.js.map, debug id ad7bb659-c892-f950-929a-7ad971022bab)
16:09:12.058     ~/chunks/ssr/frontend-new_815e2b35._.js (sourcemap at frontend-new_815e2b35._.js.map, debug id 0efbd83a-4825-e5f0-27fc-e03b563843e6)
16:09:12.058     ~/chunks/ssr/frontend-new_82e4bfa2._.js (sourcemap at frontend-new_82e4bfa2._.js.map, debug id 86e6e1fa-5e4c-9f97-cb5f-be5654e2aa2d)
16:09:12.058     ~/chunks/ssr/frontend-new_92d61db2._.js (sourcemap at frontend-new_92d61db2._.js.map, debug id b1fc0a7d-eca0-c8d7-0282-2c392cc1c949)
16:09:12.058     ~/chunks/ssr/frontend-new_93bbbc47._.js (sourcemap at frontend-new_93bbbc47._.js.map, debug id 1aef5e28-c4b1-7f00-40b8-6842d7afb149)
16:09:12.058     ~/chunks/ssr/frontend-new_95cee9f6._.js (sourcemap at frontend-new_95cee9f6._.js.map, debug id b52d2e09-02d2-b028-9065-12d938b89c18)
16:09:12.058     ~/chunks/ssr/frontend-new_9715338a._.js (sourcemap at frontend-new_9715338a._.js.map, debug id 659bb694-e798-f03a-b8fc-ab009eb43eba)
16:09:12.058     ~/chunks/ssr/frontend-new_9da6666e._.js (sourcemap at frontend-new_9da6666e._.js.map, debug id 7f57fcca-dc39-4935-7f0e-ac9191dd69f0)
16:09:12.058     ~/chunks/ssr/frontend-new__next-internal_server_app_(auth)_login_page_actions_d50acbaa.js (sourcemap at frontend-new__next-internal_server_app_%28auth%29_login_page_actions_d50acbaa.js.map, debug id 1478a0b8-a771-191b-c3c0-d5c1aeba9964)
16:09:12.058     ~/chunks/ssr/frontend-new__next-internal_server_app_(auth)_register_page_actions_8d965127.js (sourcemap at frontend-new__next-internal_server_app_%28auth%29_register_page_actions_8d965127.js.map, debug id 7f62f2c4-f55f-9046-0877-86e0b4a9e2e9)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app__global-error_page_actions_c4349f01.js (sourcemap at frontend-new__next-internal_server_app__global-error_page_actions_c4349f01.js.map, debug id 287c4d81-73d6-a2a3-4e19-24e4e0e283c1)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app__not-found_page_actions_b3ddd383.js (sourcemap at frontend-new__next-internal_server_app__not-found_page_actions_b3ddd383.js.map, debug id 7545c100-9ccb-1109-c1d0-1b6754bd77c7)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app_auth_reset-password_page_actions_3d91cf70.js (sourcemap at frontend-new__next-internal_server_app_auth_reset-password_page_actions_3d91cf70.js.map, debug id 63dfb33b-2a21-03a6-8260-4c6f0874c82b)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app_dashboard_documents_page_actions_266dcc75.js (sourcemap at frontend-new__next-internal_server_app_dashboard_documents_page_actions_266dcc75.js.map, debug id 425e57d0-4d59-e961-cd52-91c7260e494f)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app_dashboard_help_page_actions_0ce1c43a.js (sourcemap at frontend-new__next-internal_server_app_dashboard_help_page_actions_0ce1c43a.js.map, debug id e7213e0f-dbb4-3cae-17a3-8b31aa032148)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app_dashboard_page_actions_5ecd764e.js (sourcemap at frontend-new__next-internal_server_app_dashboard_page_actions_5ecd764e.js.map, debug id 814fd74f-1775-25a4-df66-e9eaba15b844)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app_dashboard_settings_page_actions_a3f8376d.js (sourcemap at frontend-new__next-internal_server_app_dashboard_settings_page_actions_a3f8376d.js.map, debug id f5ad9668-e1de-db07-8d6c-fc3d1cf3c2c4)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app_invite_[token]_page_actions_01dc77c7.js (sourcemap at frontend-new__next-internal_server_app_invite_%5Btoken%5D_page_actions_01dc77c7.js.map, debug id ebf8ee5a-d28d-c748-1b71-39df113e0e53)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app_oauth_callback_page_actions_f1f1bfac.js (sourcemap at frontend-new__next-internal_server_app_oauth_callback_page_actions_f1f1bfac.js.map, debug id 6843a54e-3c69-d071-4efb-bfaeb58993ff)
16:09:12.059     ~/chunks/ssr/frontend-new__next-internal_server_app_page_actions_9f673df2.js (sourcemap at frontend-new__next-internal_server_app_page_actions_9f673df2.js.map, debug id 0b2a5bfa-fb95-c405-30e8-bf3af5ee7677)
16:09:12.059     ~/chunks/ssr/frontend-new_a3743ed2._.js (sourcemap at frontend-new_a3743ed2._.js.map, debug id b5101db1-d72b-0d57-98f8-150565114858)
16:09:12.059     ~/chunks/ssr/frontend-new_aba77583._.js (sourcemap at frontend-new_aba77583._.js.map, debug id 4174a6ac-cfc8-362b-62f3-1efbb9aab2f1)
16:09:12.059     ~/chunks/ssr/frontend-new_af2a1bd0._.js (sourcemap at frontend-new_af2a1bd0._.js.map, debug id 2efde651-33d0-025c-e067-2b33d51f5319)
16:09:12.059     ~/chunks/ssr/frontend-new_app_(auth)_layout_tsx_994428af._.js (sourcemap at frontend-new_app_%28auth%29_layout_tsx_994428af._.js.map, debug id 50b9b6c4-19e3-9a5a-cf48-3f11a34f930d)
16:09:12.059     ~/chunks/ssr/frontend-new_app_8c427f53._.js (sourcemap at frontend-new_app_8c427f53._.js.map, debug id 28816304-f792-3a96-8fc1-7420290d741e)
16:09:12.059     ~/chunks/ssr/frontend-new_app_dashboard_chat_[chatId]_page_tsx_0c63778c._.js (sourcemap at frontend-new_app_dashboard_chat_%5BchatId%5D_page_tsx_0c63778c._.js.map, debug id b991b56b-ef6a-dc44-d0b7-231717a53e46)
16:09:12.059     ~/chunks/ssr/frontend-new_app_dashboard_layout_tsx_04d7c767._.js (sourcemap at frontend-new_app_dashboard_layout_tsx_04d7c767._.js.map, debug id 9eea4756-ad34-b454-10ad-3f70c3199921)
16:09:12.059     ~/chunks/ssr/frontend-new_app_dashboard_layout_tsx_865783bd._.js (sourcemap at frontend-new_app_dashboard_layout_tsx_865783bd._.js.map, debug id c432467e-c8a6-f9d7-bcfb-8648f9254ca3)
16:09:12.059     ~/chunks/ssr/frontend-new_app_dashboard_page_tsx_e8847695._.js (sourcemap at frontend-new_app_dashboard_page_tsx_e8847695._.js.map, debug id b8fab383-1969-67ff-b02d-597a4719230f)
16:09:12.059     ~/chunks/ssr/frontend-new_app_dashboard_settings_layout_tsx_14bb581c._.js (sourcemap at frontend-new_app_dashboard_settings_layout_tsx_14bb581c._.js.map, debug id 73350dca-daba-6050-d4cb-3339ec2e932a)
16:09:12.059     ~/chunks/ssr/frontend-new_app_dashboard_settings_layout_tsx_7aca702d._.js (sourcemap at frontend-new_app_dashboard_settings_layout_tsx_7aca702d._.js.map, debug id 26c3b637-9003-fb7e-25e2-ac48c2872ae3)
16:09:12.059     ~/chunks/ssr/frontend-new_app_global-error_tsx_f440b12b._.js (sourcemap at frontend-new_app_global-error_tsx_f440b12b._.js.map, debug id df5d470b-7381-d350-a38b-ebca92efff5f)
16:09:12.060     ~/chunks/ssr/frontend-new_b68ce830._.js (sourcemap at frontend-new_b68ce830._.js.map, debug id 044fdef2-a774-7e87-cc3c-3424b7b58eea)
16:09:12.060     ~/chunks/ssr/frontend-new_c37f21e4._.js (sourcemap at frontend-new_c37f21e4._.js.map, debug id b096dc47-838a-60e8-ff00-ca6fcdb3f503)
16:09:12.060     ~/chunks/ssr/frontend-new_c51f1e75._.js (sourcemap at frontend-new_c51f1e75._.js.map, debug id 5691c099-f458-0ced-0982-32a6a964a0c2)
16:09:12.060     ~/chunks/ssr/frontend-new_components_help_2f7832de._.js (sourcemap at frontend-new_components_help_2f7832de._.js.map, debug id f0bd69c7-924a-3810-aa59-0c923ec6f140)
16:09:12.060     ~/chunks/ssr/frontend-new_components_help_HelpSearch_tsx_0294adcb._.js (sourcemap at frontend-new_components_help_HelpSearch_tsx_0294adcb._.js.map, debug id 3fb03b5a-4e63-79ad-66d5-75c0ec4e4f88)
16:09:12.060     ~/chunks/ssr/frontend-new_components_knowledge-base_DocumentsTable_tsx_938da837._.js (sourcemap at frontend-new_components_knowledge-base_DocumentsTable_tsx_938da837._.js.map, debug id b99eff8a-3b9a-3646-83f1-de675f96b499)
16:09:12.060     ~/chunks/ssr/frontend-new_components_settings_BillingSettings_tsx_93b4f8da._.js (sourcemap at frontend-new_components_settings_BillingSettings_tsx_93b4f8da._.js.map, debug id 827a9f19-6e44-c92c-6dc7-158703efccb9)
16:09:12.060     ~/chunks/ssr/frontend-new_components_settings_GeneralSettings_tsx_4800bf3e._.js (sourcemap at frontend-new_components_settings_GeneralSettings_tsx_4800bf3e._.js.map, debug id 57bbd7a6-a2ea-35fd-92a8-59adbe6a8bfa)
16:09:12.060     ~/chunks/ssr/frontend-new_components_ui_dropdown-menu_tsx_c0a4daf9._.js (sourcemap at frontend-new_components_ui_dropdown-menu_tsx_c0a4daf9._.js.map, debug id 048fdb0e-7a23-5c46-d845-fec39ad46bc0)
16:09:12.060     ~/chunks/ssr/frontend-new_d9ac8530._.js (sourcemap at frontend-new_d9ac8530._.js.map, debug id 97974cf0-d4eb-f789-2966-42712bbd7d38)
16:09:12.060     ~/chunks/ssr/frontend-new_de892a01._.js (sourcemap at frontend-new_de892a01._.js.map, debug id cb406a6c-d77b-e085-c97e-c194636c395a)
16:09:12.060     ~/chunks/ssr/frontend-new_e1f70c03._.js (sourcemap at frontend-new_e1f70c03._.js.map, debug id 20d4fc63-9642-3fe8-bc12-4c0514a12178)
16:09:12.060     ~/chunks/ssr/frontend-new_e2a60983._.js (sourcemap at frontend-new_e2a60983._.js.map, debug id ee56c36b-3417-dc89-ab63-ad245fc8e0fa)
16:09:12.060     ~/chunks/ssr/frontend-new_ea59bf87._.js (sourcemap at frontend-new_ea59bf87._.js.map, debug id dc3a512c-c902-2c9c-ab29-a868ea33763b)
16:09:12.060     ~/chunks/ssr/frontend-new_eca020aa._.js (sourcemap at frontend-new_eca020aa._.js.map, debug id 64868d83-156c-d26f-2386-66b1d040debd)
16:09:12.060     ~/chunks/ssr/frontend-new_f0d843ef._.js (sourcemap at frontend-new_f0d843ef._.js.map, debug id aff12749-af11-ed7e-c0ad-5b92b3817854)
16:09:12.060     ~/chunks/ssr/frontend-new_f5b803cb._.js (sourcemap at frontend-new_f5b803cb._.js.map, debug id 815a47ff-3b3c-b87d-9e18-77ae2c07fdd1)
16:09:12.060     ~/chunks/ssr/frontend-new_f8d78cf9._.js (sourcemap at frontend-new_f8d78cf9._.js.map, debug id a9e645ec-44ee-efb2-1813-55450824385d)
16:09:12.060     ~/chunks/ssr/frontend-new_fbe3b9d0._.js (sourcemap at frontend-new_fbe3b9d0._.js.map, debug id 360996fc-6acc-89c7-5e65-80262940cc5b)
16:09:12.060     ~/chunks/ssr/frontend-new_fd3da809._.js (sourcemap at frontend-new_fd3da809._.js.map, debug id bfccebb2-100a-736c-bd05-9e7034c57482)
16:09:12.060     ~/chunks/ssr/frontend-new_feefddc1._.js (sourcemap at frontend-new_feefddc1._.js.map, debug id 492584b1-13e1-1837-6c2b-8d7e12d82c0d)
16:09:12.060     ~/chunks/ssr/frontend-new_lib_utils_ts_ada99aa0._.js (sourcemap at frontend-new_lib_utils_ts_ada99aa0._.js.map, debug id 60e79602-7785-33a7-9917-87407775246b)
16:09:12.061     ~/chunks/ssr/frontend-new_lib_utils_ts_ed8c84b7._.js (sourcemap at frontend-new_lib_utils_ts_ed8c84b7._.js.map, debug id a585f980-162d-3524-eb9d-475ba6d3ae2f)
16:09:12.061     ~/edge/chunks/1da7c_@sentry_dca9e4ed._.js (sourcemap at 1da7c_%40sentry_dca9e4ed._.js.map)
16:09:12.061     ~/edge/chunks/[root-of-the-server]__59471a3c._.js (sourcemap at %5Broot-of-the-server%5D__59471a3c._.js.map)
16:09:12.061     ~/edge/chunks/frontend-new_a3b50720._.js (sourcemap at frontend-new_a3b50720._.js.map)
16:09:12.061     ~/edge/chunks/turbopack-frontend-new_edge-wrapper_dca65f86.js (sourcemap at frontend-new_edge-wrapper_dca65f86.js.map)
16:09:12.061     ~/instrumentation.js (sourcemap at instrumentation.js.map)
16:09:12.061     ~/interception-route-rewrite-manifest.js (no sourcemap found)
16:09:12.061       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/interception-route-rewrite-manifest.js)
16:09:12.061     ~/middleware-build-manifest.js (no sourcemap found)
16:09:12.061       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/middleware-build-manifest.js)
16:09:12.061     ~/middleware.js (sourcemap at middleware.js.map)
16:09:12.061     ~/next-font-manifest.js (no sourcemap found)
16:09:12.061       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/next-font-manifest.js)
16:09:12.061     ~/server-reference-manifest.js (no sourcemap found)
16:09:12.061       - warning: could not determine a source map reference (Could not auto-detect referenced sourcemap for ~/server-reference-manifest.js)
16:09:12.061   Source Maps
16:09:12.061     ~/app/(auth)/forgot-password/page.js.map
16:09:12.061     ~/app/(auth)/login/page.js.map
16:09:12.061     ~/app/(auth)/register/page.js.map
16:09:12.061     ~/app/(marketing)/legal/[slug]/page.js.map
16:09:12.061     ~/app/_global-error/page.js.map
16:09:12.061     ~/app/_not-found/page.js.map
16:09:12.061     ~/app/auth/callback/route.js.map
16:09:12.062     ~/app/auth/reset-password/page.js.map
16:09:12.062     ~/app/dashboard/chat/[chatId]/page.js.map
16:09:12.062     ~/app/dashboard/documents/page.js.map
16:09:12.062     ~/app/dashboard/help/[slug]/page.js.map
16:09:12.062     ~/app/dashboard/help/page.js.map
16:09:12.062     ~/app/dashboard/page.js.map
16:09:12.062     ~/app/dashboard/settings/billing/page.js.map
16:09:12.062     ~/app/dashboard/settings/data-sources/page.js.map
16:09:12.062     ~/app/dashboard/settings/failed-tasks/page.js.map
16:09:12.062     ~/app/dashboard/settings/general/page.js.map
16:09:12.062     ~/app/dashboard/settings/knowledge-base/page.js.map
16:09:12.062     ~/app/dashboard/settings/notifications/page.js.map
16:09:12.062     ~/app/dashboard/settings/page.js.map
16:09:12.062     ~/app/dashboard/settings/team/page.js.map
16:09:12.062     ~/app/favicon.ico/route.js.map
16:09:12.062     ~/app/invite/[token]/page.js.map
16:09:12.062     ~/app/oauth/callback/page.js.map
16:09:12.062     ~/app/page.js.map
16:09:12.062     ~/chunks/13956_build_esm_detectors_platform_node_machine-id_getMachineId-linux_0c68c229.js.map (debug id f7b0e6ea-26dc-10ad-ad8c-115697123160)
16:09:12.062     ~/chunks/13956_build_esm_detectors_platform_node_machine-id_getMachineId-unsupported_236ca858.js.map (debug id e56edd19-6895-87f3-b482-010601eed038)
16:09:12.062     ~/chunks/1da7c_7c615a46._.js.map (debug id 6dc4e3e2-8442-a7f5-b181-c0df6db52521)
16:09:12.062     ~/chunks/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_a6e355df._.js.map (debug id 5544189a-ee47-c8ed-3bbc-1b44a228c142)
16:09:12.063     ~/chunks/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_b2241ed2._.js.map (debug id fc89a005-6f20-a4f6-597c-35a271f82211)
16:09:12.063     ~/chunks/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_fbf9b753._.js.map (debug id d7be5e49-86d3-96d5-026b-151dd91f92a3)
16:09:12.063     ~/chunks/1da7c_c5d00c00._.js.map (debug id 4fc69fbd-84c6-b7b8-4c16-f6251b668b19)
16:09:12.063     ~/chunks/1da7c_next_dist_esm_build_templates_app-route_cf5e7020.js.map (debug id 1e220094-b07c-f67f-c6e0-5ee454416b46)
16:09:12.063     ~/chunks/[externals]_node:inspector_7a4283c6._.js.map (debug id bbb7096f-41e0-233c-11dd-d03d0fc428b4)
16:09:12.063     ~/chunks/[root-of-the-server]__28821955._.js.map (debug id 2c5f937c-db64-4f5b-a0c5-6cef48d8c041)
16:09:12.063     ~/chunks/[root-of-the-server]__86eb7852._.js.map (debug id 0f42ff8e-f625-236f-a8ea-df6c00c689fd)
16:09:12.063     ~/chunks/[root-of-the-server]__ab52b825._.js.map (debug id 0a4e70a7-dd05-a9be-b594-7c7699031a06)
16:09:12.063     ~/chunks/[root-of-the-server]__b89b5a39._.js.map (debug id 5ac8d800-056e-59bb-275e-a2f608c27d4d)
16:09:12.063     ~/chunks/[root-of-the-server]__b8d37178._.js.map (debug id 6461ebce-e6ed-7298-fb07-275ceff12363)
16:09:12.063     ~/chunks/[turbopack]_runtime.js.map
16:09:12.063     ~/chunks/frontend-new__next-internal_server_app_auth_callback_route_actions_8ffb3c0e.js.map (debug id c94eda45-421e-10e9-fb1e-d78bf7fa4ede)
16:09:12.063     ~/chunks/frontend-new__next-internal_server_app_favicon_ico_route_actions_fa397e36.js.map (debug id d412fe64-89fc-adf4-7d0a-61c597ca21ed)
16:09:12.063     ~/chunks/frontend-new_sentry_server_config_ts_fb78c4fb._.js.map (debug id c5291ba3-0de6-1e2a-cdfe-180faa98bae9)
16:09:12.063     ~/chunks/ssr/13956_build_esm_detectors_platform_node_machine-id_getMachineId-linux_d7cb7675.js.map (debug id 0478fb4e-6b4a-e2d1-d28f-cc566114ce72)
16:09:12.063     ~/chunks/ssr/13956_build_esm_detectors_platform_node_machine-id_getMachineId-unsupported_8b7aecf9.js.map (debug id e6b7b94e-af54-5ad3-79d3-c78671fc687e)
16:09:12.063     ~/chunks/ssr/1da7c_02c30ede._.js.map (debug id 9a79e254-72c9-ad22-c6af-c4e3534b74d7)
16:09:12.063     ~/chunks/ssr/1da7c_4c86d122._.js.map (debug id 12549ee1-ffb5-c3d5-f0fd-0b11b3b7646b)
16:09:12.063     ~/chunks/ssr/1da7c_4d71bfb8._.js.map (debug id af6c83bf-9aaf-2775-0247-a8d34202b9ab)
16:09:12.063     ~/chunks/ssr/1da7c_4e0e3f3b._.js.map (debug id a06b1047-0d13-fc44-c281-e65786da5d4d)
16:09:12.064     ~/chunks/ssr/1da7c_4f6772db._.js.map (debug id 0bc098a3-e482-e0f6-b226-fea88cf42fa1)
16:09:12.064     ~/chunks/ssr/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_0dcef83c._.js.map (debug id b1c4d787-22cf-f572-fb67-7aba2b9c0e96)
16:09:12.064     ~/chunks/ssr/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_75c9de92._.js.map (debug id 587a9a6c-27cd-aada-3044-40d66007f228)
16:09:12.064     ~/chunks/ssr/1da7c_@opentelemetry_resources_build_esm_detectors_platform_node_machine-id_9da8d312._.js.map (debug id 0fe9877a-53bc-ad33-f005-6952b9f10b78)
16:09:12.064     ~/chunks/ssr/1da7c_@radix-ui_react-popper_dist_index_mjs_2ad58864._.js.map (debug id f75e849f-918d-49ca-ec38-8c15afb789aa)
16:09:12.067     ~/chunks/ssr/1da7c_@radix-ui_react-tooltip_dist_index_mjs_99b0816e._.js.map (debug id 4e1901d3-ebee-8577-acf4-bbe6a92f9f71)
16:09:12.067     ~/chunks/ssr/1da7c_@tanstack_8c5fe470._.js.map (debug id ad959641-353f-5e1e-36b8-1f3677e7d7a6)
16:09:12.067     ~/chunks/ssr/1da7c_@tanstack_react-query_build_modern_useQuery_0140a44e.js.map (debug id adf7b1ee-a6f6-7f2d-f605-13d39ece08a9)
16:09:12.067     ~/chunks/ssr/1da7c_b3dbce65._.js.map (debug id 4e3ed1d1-f9af-4cdc-d4b3-8751bb2fe8f4)
16:09:12.067     ~/chunks/ssr/1da7c_lucide-react_dist_esm_icons_1e752d28._.js.map (debug id 5f8014d8-909f-ee30-56f4-b2d2368bca5c)
16:09:12.067     ~/chunks/ssr/1da7c_lucide-react_dist_esm_icons_f8bc5ecc._.js.map (debug id d0093865-370c-fe68-321a-39eebb41eb43)
16:09:12.067     ~/chunks/ssr/1da7c_lucide-react_dist_esm_icons_settings_41516ee0.js.map (debug id cb2bf54a-f11f-aaec-c8e6-b83912856ba4)
16:09:12.067     ~/chunks/ssr/1da7c_next_b8ad55ac._.js.map (debug id 3761de60-e420-50d8-7f74-2e17c960d7d2)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_0784f779._.js.map (debug id 89b44f04-bf68-d93f-1e4a-4f7daed1fdb9)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_0b11b2c7._.js.map (debug id 7d69a2c4-52ef-a0ac-cef2-bd63f5282874)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_2d90c7b2._.js.map (debug id 78730bf9-7234-5a26-7cbd-31ef1c2f8bc0)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_67b842e4._.js.map (debug id 50735cf4-920f-a020-d091-f109b0fc2663)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_8f122843._.js.map (debug id 89f95fec-0fce-b464-4cdf-56d6620d28e1)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_client_components_07c4e3fe._.js.map (debug id 960f1f32-b0e5-a644-60cb-a618fcf4b0ef)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_client_components_builtin_forbidden_26e2a1e5.js.map (debug id bf037b3c-1eeb-9de0-7cbe-c36fe92b9503)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_client_components_builtin_unauthorized_fc936f1d.js.map (debug id c67f12bb-04f7-9e5e-d079-7ae4373ef467)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_esm_02b5ba7f._.js.map (debug id 0561f801-c778-35fb-aa54-2fb54a89231d)
16:09:12.067     ~/chunks/ssr/1da7c_next_dist_esm_build_templates_app-page_e2c916d2.js.map (debug id ed0d1924-6533-4b94-f3bf-b4965cf6d209)
16:09:12.067     ~/chunks/ssr/1da7c_react-hook-form_dist_index_esm_mjs_8a10e602._.js.map (debug id e85ad3bc-3786-5dd9-2291-c6ae639c9efa)
16:09:12.067     ~/chunks/ssr/1da7c_sonner_dist_index_mjs_d5937113._.js.map (debug id e93f3333-1251-6857-4812-778586e3d3e1)
16:09:12.067     ~/chunks/ssr/6118d__next-internal_server_app_(auth)_forgot-password_page_actions_5987a920.js.map (debug id 94458ad6-2127-ca43-b978-bd22b8c2cda3)
16:09:12.067     ~/chunks/ssr/6118d__next-internal_server_app_(marketing)_legal_[slug]_page_actions_3cf8ff4f.js.map (debug id 2ddead6e-590a-dafd-14f2-283721df85b6)
16:09:12.067     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_chat_[chatId]_page_actions_40693ad0.js.map (debug id e8d590b4-07db-9f12-2992-3eef4f5d0965)
16:09:12.068     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_help_[slug]_page_actions_6a786b56.js.map (debug id e9c10803-deb6-4d0d-b34d-bcc515ceb2b0)
16:09:12.068     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_billing_page_actions_fe756f85.js.map (debug id f8983a4f-1daf-07a7-1205-6b3989ffd77a)
16:09:12.068     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_data-sources_page_actions_0cd33e5c.js.map (debug id b1e243cb-7aaa-c93b-fa68-18c3af0059d0)
16:09:12.068     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_failed-tasks_page_actions_aafc47d7.js.map (debug id 66f0e749-3623-9879-a3f8-bcf8e7c6301e)
16:09:12.068     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_general_page_actions_e1e78074.js.map (debug id d8e16f8f-d509-ecb5-d617-32a5bd64653d)
16:09:12.068     ~/chunks/ssr/6118d__next-internal_server_app_dashboard_settings_team_page_actions_95695693.js.map (debug id 78a5921e-c12d-caae-ed1a-5d9c168d49f1)
16:09:12.068     ~/chunks/ssr/734e0_next-internal_server_app_dashboard_settings_notifications_page_actions_e7b69ca9.js.map (debug id b313af24-f985-e07e-4e5f-8466d5a95d2f)
16:09:12.068     ~/chunks/ssr/[externals]_node:inspector_7a4283c6._.js.map (debug id 5f41589b-d010-1718-2c15-d0250c8535f0)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__088fb375._.js.map (debug id 4a955a23-1506-40e5-ae46-89850e7f5d15)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__0d8abd2f._.js.map (debug id 835699c9-5554-4715-8aa4-27b61ea7cfd4)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__0d919162._.js.map (debug id cba992e2-3cbf-0e58-9d58-4d45ad91d591)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__100aa689._.js.map (debug id 01f197d7-516c-3394-c11a-3b5725fec01f)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__15bbd683._.js.map (debug id d2d7690d-27bc-ad87-0002-ff9e48d6082f)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__25125dc0._.js.map (debug id 6ae4e90e-e19e-a9af-7355-58bc210456ea)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__3098c850._.js.map (debug id fec378ad-6fa5-5d5a-87e0-40269e70fee8)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__36728547._.js.map (debug id 69ca096f-a705-2f8a-8a86-f3b8041dc693)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__3c59eab8._.js.map (debug id 91636e71-7a03-9418-1b9d-9f72a83f7929)
16:09:12.068     ~/chunks/ssr/[root-of-the-server]__3edaf77c._.js.map (debug id 0348ed2d-672e-ad6c-1397-2d6aea4a0630)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__45909684._.js.map (debug id 283ee66b-13e0-55fd-a206-cc3beef83f58)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__4f0f17b1._.js.map (debug id 6b756fc8-eb3d-e3bd-eb2c-44ec533238ef)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__5565b0cd._.js.map (debug id 77eebf94-738b-bb17-3ce9-4de8fbc47642)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__59b47646._.js.map (debug id dd2fe526-0217-014d-061d-8497ffc4e625)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__835c65ab._.js.map (debug id 9520d7dc-aae1-da92-c84f-931ad8c057ad)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__8609e7f2._.js.map (debug id e6255368-6d13-87e8-6a2f-1b58bdd0ed2d)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__92e09ac8._.js.map (debug id 2f6df708-afe1-9f5f-0353-02bd08a5c196)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__a2f492bb._.js.map (debug id 046f0a37-4d9e-9ff4-28d0-1f9f7e26e6e2)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__a347a19c._.js.map (debug id 92142c05-a98a-563f-a0b1-5672afebaa6b)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__a3b992f9._.js.map (debug id 87908fee-b663-e23e-43c4-af3c3e2acdc6)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__aac6418c._.js.map (debug id 3d086d99-0a50-e46a-4a86-e20ce33a27d5)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__b098f0e0._.js.map (debug id 0f7248c5-3418-5089-cd9e-3f696ae02202)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__b4c43e30._.js.map (debug id 6139d6d5-bffc-79ee-d527-fb6bb964df02)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__b6781b6d._.js.map (debug id 3b581610-e733-35f5-31aa-98c1d9ba3d2c)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__bfa3f14c._.js.map (debug id 158a826f-414f-ab7e-d174-166a11089e92)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__c6a529a4._.js.map (debug id 5214b15e-4eee-9ffa-3832-30137a8ddcd4)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__cc584089._.js.map (debug id a68b8ab5-89c0-6ddc-e572-d00412a136a0)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__d3064e36._.js.map (debug id 05550f9e-89e5-c5e5-07f6-6ac50d7bc7ba)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__d7f121f9._.js.map (debug id 6834336f-8006-58db-7197-43b930ee235d)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__d8026068._.js.map (debug id caa9f4d4-0838-1ef4-69d7-9148d141eb3f)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__ef46dcb6._.js.map (debug id 43d68aeb-4cf8-01b1-656e-187c5d025a00)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__f0bfff96._.js.map (debug id de7f1532-454a-d51a-08ba-c7fecde2c966)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__f48f4b27._.js.map (debug id 679fe6ac-2345-8e4f-767b-ef6650cab38c)
16:09:12.069     ~/chunks/ssr/[root-of-the-server]__fc451734._.js.map (debug id 30939323-861b-9b62-3924-e5d4d2cd7e67)
16:09:12.069     ~/chunks/ssr/[turbopack]_runtime.js.map
16:09:12.069     ~/chunks/ssr/e66f5_server_app_dashboard_settings_knowledge-base_page_actions_a0f98f9c.js.map (debug id 6aed5621-da6d-8be1-8d53-acd0d5852132)
16:09:12.069     ~/chunks/ssr/frontend-new_00172161._.js.map (debug id 77a7bcbc-429b-55a0-45cf-744dc14d3119)
16:09:12.069     ~/chunks/ssr/frontend-new_0580cb9d._.js.map (debug id bbad3e47-b22b-d8d2-9df2-1d8043b9777e)
16:09:12.069     ~/chunks/ssr/frontend-new_06074e2d._.js.map (debug id 99640d64-2a5a-4418-a45d-3056562cdf01)
16:09:12.069     ~/chunks/ssr/frontend-new_0cb4b52a._.js.map (debug id b40008da-acc2-a0e4-678f-6eeeb3f2a6a5)
16:09:12.069     ~/chunks/ssr/frontend-new_1d164b28._.js.map (debug id 0c06fcb8-3b4c-e25c-a0ca-66cd928aceb2)
16:09:12.069     ~/chunks/ssr/frontend-new_1dc726f5._.js.map (debug id e690c603-c242-4f44-8fc7-79a24a907106)
16:09:12.069     ~/chunks/ssr/frontend-new_1ff8f695._.js.map (debug id 5025b9eb-9b48-c10c-ca20-099de48e1834)
16:09:12.069     ~/chunks/ssr/frontend-new_289f075e._.js.map (debug id 0d45eeb5-1d2b-edd2-fa73-1203c7f5d7a7)
16:09:12.070     ~/chunks/ssr/frontend-new_2975814d._.js.map (debug id d49a43a0-9bb5-f3d5-6ec2-9d53ea38adf9)
16:09:12.070     ~/chunks/ssr/frontend-new_32816aee._.js.map (debug id fff4ef7a-0822-c400-d972-69383df76c81)
16:09:12.070     ~/chunks/ssr/frontend-new_35897e86._.js.map (debug id 2cb81a34-d3f4-119d-e39e-d8d922c7f94e)
16:09:12.070     ~/chunks/ssr/frontend-new_36cff9b1._.js.map (debug id 1ad335e2-1e3e-4c95-1add-f858f9402aba)
16:09:12.070     ~/chunks/ssr/frontend-new_469c2c8f._.js.map (debug id 999588d8-9f1a-0dcf-d09e-561f307100ba)
16:09:12.070     ~/chunks/ssr/frontend-new_56fc1bec._.js.map (debug id 15af6a82-494a-5b0c-754a-84eb0a1e0583)
16:09:12.070     ~/chunks/ssr/frontend-new_5f017408._.js.map (debug id a416313d-7d15-1215-8d89-50166c5481c9)
16:09:12.070     ~/chunks/ssr/frontend-new_619ead6a._.js.map (debug id 8fca85c2-347d-7454-f618-f30543dfe5e1)
16:09:12.070     ~/chunks/ssr/frontend-new_6bf15c89._.js.map (debug id 1a0c47b9-c899-c60f-24cc-e2a971be3b46)
16:09:12.070     ~/chunks/ssr/frontend-new_707ef70a._.js.map (debug id a3fcb60b-a9e9-bfdc-43c4-d6f669cb458c)
16:09:12.070     ~/chunks/ssr/frontend-new_769c2d97._.js.map (debug id 60ebc8d2-5c6d-b3f8-c0a7-c06da23f013d)
16:09:12.070     ~/chunks/ssr/frontend-new_7f90c052._.js.map (debug id ad7bb659-c892-f950-929a-7ad971022bab)
16:09:12.070     ~/chunks/ssr/frontend-new_815e2b35._.js.map (debug id 0efbd83a-4825-e5f0-27fc-e03b563843e6)
16:09:12.070     ~/chunks/ssr/frontend-new_82e4bfa2._.js.map (debug id 86e6e1fa-5e4c-9f97-cb5f-be5654e2aa2d)
16:09:12.070     ~/chunks/ssr/frontend-new_92d61db2._.js.map (debug id b1fc0a7d-eca0-c8d7-0282-2c392cc1c949)
16:09:12.070     ~/chunks/ssr/frontend-new_93bbbc47._.js.map (debug id 1aef5e28-c4b1-7f00-40b8-6842d7afb149)
16:09:12.070     ~/chunks/ssr/frontend-new_95cee9f6._.js.map (debug id b52d2e09-02d2-b028-9065-12d938b89c18)
16:09:12.070     ~/chunks/ssr/frontend-new_9715338a._.js.map (debug id 659bb694-e798-f03a-b8fc-ab009eb43eba)
16:09:12.070     ~/chunks/ssr/frontend-new_9da6666e._.js.map (debug id 7f57fcca-dc39-4935-7f0e-ac9191dd69f0)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_(auth)_login_page_actions_d50acbaa.js.map (debug id 1478a0b8-a771-191b-c3c0-d5c1aeba9964)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_(auth)_register_page_actions_8d965127.js.map (debug id 7f62f2c4-f55f-9046-0877-86e0b4a9e2e9)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app__global-error_page_actions_c4349f01.js.map (debug id 287c4d81-73d6-a2a3-4e19-24e4e0e283c1)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app__not-found_page_actions_b3ddd383.js.map (debug id 7545c100-9ccb-1109-c1d0-1b6754bd77c7)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_auth_reset-password_page_actions_3d91cf70.js.map (debug id 63dfb33b-2a21-03a6-8260-4c6f0874c82b)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_dashboard_documents_page_actions_266dcc75.js.map (debug id 425e57d0-4d59-e961-cd52-91c7260e494f)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_dashboard_help_page_actions_0ce1c43a.js.map (debug id e7213e0f-dbb4-3cae-17a3-8b31aa032148)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_dashboard_page_actions_5ecd764e.js.map (debug id 814fd74f-1775-25a4-df66-e9eaba15b844)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_dashboard_settings_page_actions_a3f8376d.js.map (debug id f5ad9668-e1de-db07-8d6c-fc3d1cf3c2c4)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_invite_[token]_page_actions_01dc77c7.js.map (debug id ebf8ee5a-d28d-c748-1b71-39df113e0e53)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_oauth_callback_page_actions_f1f1bfac.js.map (debug id 6843a54e-3c69-d071-4efb-bfaeb58993ff)
16:09:12.070     ~/chunks/ssr/frontend-new__next-internal_server_app_page_actions_9f673df2.js.map (debug id 0b2a5bfa-fb95-c405-30e8-bf3af5ee7677)
16:09:12.070     ~/chunks/ssr/frontend-new_a3743ed2._.js.map (debug id b5101db1-d72b-0d57-98f8-150565114858)
16:09:12.070     ~/chunks/ssr/frontend-new_aba77583._.js.map (debug id 4174a6ac-cfc8-362b-62f3-1efbb9aab2f1)
16:09:12.070     ~/chunks/ssr/frontend-new_af2a1bd0._.js.map (debug id 2efde651-33d0-025c-e067-2b33d51f5319)
16:09:12.071     ~/chunks/ssr/frontend-new_app_(auth)_layout_tsx_994428af._.js.map (debug id 50b9b6c4-19e3-9a5a-cf48-3f11a34f930d)
16:09:12.071     ~/chunks/ssr/frontend-new_app_8c427f53._.js.map (debug id 28816304-f792-3a96-8fc1-7420290d741e)
16:09:12.071     ~/chunks/ssr/frontend-new_app_dashboard_chat_[chatId]_page_tsx_0c63778c._.js.map (debug id b991b56b-ef6a-dc44-d0b7-231717a53e46)
16:09:12.071     ~/chunks/ssr/frontend-new_app_dashboard_layout_tsx_04d7c767._.js.map (debug id 9eea4756-ad34-b454-10ad-3f70c3199921)
16:09:12.071     ~/chunks/ssr/frontend-new_app_dashboard_layout_tsx_865783bd._.js.map (debug id c432467e-c8a6-f9d7-bcfb-8648f9254ca3)
16:09:12.071     ~/chunks/ssr/frontend-new_app_dashboard_page_tsx_e8847695._.js.map (debug id b8fab383-1969-67ff-b02d-597a4719230f)
16:09:12.071     ~/chunks/ssr/frontend-new_app_dashboard_settings_layout_tsx_14bb581c._.js.map (debug id 73350dca-daba-6050-d4cb-3339ec2e932a)
16:09:12.071     ~/chunks/ssr/frontend-new_app_dashboard_settings_layout_tsx_7aca702d._.js.map (debug id 26c3b637-9003-fb7e-25e2-ac48c2872ae3)
16:09:12.071     ~/chunks/ssr/frontend-new_app_global-error_tsx_f440b12b._.js.map (debug id df5d470b-7381-d350-a38b-ebca92efff5f)
16:09:12.071     ~/chunks/ssr/frontend-new_b68ce830._.js.map (debug id 044fdef2-a774-7e87-cc3c-3424b7b58eea)
16:09:12.071     ~/chunks/ssr/frontend-new_c37f21e4._.js.map (debug id b096dc47-838a-60e8-ff00-ca6fcdb3f503)
16:09:12.071     ~/chunks/ssr/frontend-new_c51f1e75._.js.map (debug id 5691c099-f458-0ced-0982-32a6a964a0c2)
16:09:12.071     ~/chunks/ssr/frontend-new_components_help_2f7832de._.js.map (debug id f0bd69c7-924a-3810-aa59-0c923ec6f140)
16:09:12.071     ~/chunks/ssr/frontend-new_components_help_HelpSearch_tsx_0294adcb._.js.map (debug id 3fb03b5a-4e63-79ad-66d5-75c0ec4e4f88)
16:09:12.071     ~/chunks/ssr/frontend-new_components_knowledge-base_DocumentsTable_tsx_938da837._.js.map (debug id b99eff8a-3b9a-3646-83f1-de675f96b499)
16:09:12.071     ~/chunks/ssr/frontend-new_components_settings_BillingSettings_tsx_93b4f8da._.js.map (debug id 827a9f19-6e44-c92c-6dc7-158703efccb9)
16:09:12.071     ~/chunks/ssr/frontend-new_components_settings_GeneralSettings_tsx_4800bf3e._.js.map (debug id 57bbd7a6-a2ea-35fd-92a8-59adbe6a8bfa)
16:09:12.071     ~/chunks/ssr/frontend-new_components_ui_dropdown-menu_tsx_c0a4daf9._.js.map (debug id 048fdb0e-7a23-5c46-d845-fec39ad46bc0)
16:09:12.071     ~/chunks/ssr/frontend-new_d9ac8530._.js.map (debug id 97974cf0-d4eb-f789-2966-42712bbd7d38)
16:09:12.071     ~/chunks/ssr/frontend-new_de892a01._.js.map (debug id cb406a6c-d77b-e085-c97e-c194636c395a)
16:09:12.071     ~/chunks/ssr/frontend-new_e1f70c03._.js.map (debug id 20d4fc63-9642-3fe8-bc12-4c0514a12178)
16:09:12.071     ~/chunks/ssr/frontend-new_e2a60983._.js.map (debug id ee56c36b-3417-dc89-ab63-ad245fc8e0fa)
16:09:12.071     ~/chunks/ssr/frontend-new_ea59bf87._.js.map (debug id dc3a512c-c902-2c9c-ab29-a868ea33763b)
16:09:12.071     ~/chunks/ssr/frontend-new_eca020aa._.js.map (debug id 64868d83-156c-d26f-2386-66b1d040debd)
16:09:12.071     ~/chunks/ssr/frontend-new_f0d843ef._.js.map (debug id aff12749-af11-ed7e-c0ad-5b92b3817854)
16:09:12.071     ~/chunks/ssr/frontend-new_f5b803cb._.js.map (debug id 815a47ff-3b3c-b87d-9e18-77ae2c07fdd1)
16:09:12.071     ~/chunks/ssr/frontend-new_f8d78cf9._.js.map (debug id a9e645ec-44ee-efb2-1813-55450824385d)
16:09:12.071     ~/chunks/ssr/frontend-new_fbe3b9d0._.js.map (debug id 360996fc-6acc-89c7-5e65-80262940cc5b)
16:09:12.071     ~/chunks/ssr/frontend-new_fd3da809._.js.map (debug id bfccebb2-100a-736c-bd05-9e7034c57482)
16:09:12.071     ~/chunks/ssr/frontend-new_feefddc1._.js.map (debug id 492584b1-13e1-1837-6c2b-8d7e12d82c0d)
16:09:12.071     ~/chunks/ssr/frontend-new_lib_utils_ts_ada99aa0._.js.map (debug id 60e79602-7785-33a7-9917-87407775246b)
16:09:12.071     ~/chunks/ssr/frontend-new_lib_utils_ts_ed8c84b7._.js.map (debug id a585f980-162d-3524-eb9d-475ba6d3ae2f)
16:09:12.071     ~/edge/chunks/1da7c_@sentry_dca9e4ed._.js.map
16:09:12.071     ~/edge/chunks/[root-of-the-server]__59471a3c._.js.map
16:09:12.071     ~/edge/chunks/frontend-new_a3b50720._.js.map
16:09:12.072     ~/edge/chunks/frontend-new_edge-wrapper_dca65f86.js.map
16:09:12.072     ~/instrumentation.js.map
16:09:12.072     ~/middleware.js.map
16:09:12.072 [@sentry/nextjs - After Production Compile] Info: Successfully uploaded source maps to Sentry
16:09:12.088  ✓ Completed runAfterProductionCompile in 9201ms
16:09:12.089    Running TypeScript ...
16:09:24.051    Collecting page data using 3 workers ...
16:09:24.620    Generating static pages using 3 workers (0/28) ...
16:09:25.565    Generating static pages using 3 workers (7/28) 
16:09:25.605    Generating static pages using 3 workers (14/28) 
16:09:25.728    Generating static pages using 3 workers (21/28) 
16:09:25.781  ✓ Generating static pages using 3 workers (28/28) in 1160.7ms
16:09:25.802    Finalizing page optimization ...
16:09:25.812 
16:09:25.814 Route (app)
16:09:25.814 ┌ ○ /
16:09:25.815 ├ ○ /_not-found
16:09:25.815 ├ ƒ /auth/callback
16:09:25.815 ├ ○ /auth/reset-password
16:09:25.816 ├ ○ /dashboard
16:09:25.816 ├ ƒ /dashboard/chat/[chatId]
16:09:25.816 ├ ○ /dashboard/documents
16:09:25.816 ├ ○ /dashboard/help
16:09:25.816 ├ ● /dashboard/help/[slug]
16:09:25.817 │ ├ /dashboard/help/01-getting-started
16:09:25.817 │ ├ /dashboard/help/02-uploading-data
16:09:25.817 │ ├ /dashboard/help/03-chat-guide
16:09:25.817 │ └ [+2 more paths]
16:09:25.817 ├ ○ /dashboard/settings
16:09:25.817 ├ ○ /dashboard/settings/billing
16:09:25.817 ├ ○ /dashboard/settings/data-sources
16:09:25.817 ├ ○ /dashboard/settings/failed-tasks
16:09:25.817 ├ ○ /dashboard/settings/general
16:09:25.817 ├ ○ /dashboard/settings/knowledge-base
16:09:25.817 ├ ○ /dashboard/settings/notifications
16:09:25.817 ├ ○ /dashboard/settings/team
16:09:25.817 ├ ○ /forgot-password
16:09:25.817 ├ ƒ /invite/[token]
16:09:25.817 ├ ● /legal/[slug]
16:09:25.817 │ ├ /legal/terms
16:09:25.817 │ └ /legal/privacy
16:09:25.817 ├ ○ /login
16:09:25.817 ├ ○ /oauth/callback
16:09:25.817 └ ○ /register
16:09:25.818 
16:09:25.818 
16:09:25.818 ƒ Proxy (Middleware)
16:09:25.818 
16:09:25.818 ○  (Static)   prerendered as static content
16:09:25.818 ●  (SSG)      prerendered as static HTML (uses generateStaticParams)
16:09:25.818 ƒ  (Dynamic)  server-rendered on demand
16:09:25.818 
16:09:26.628 Traced Next.js server files in: 114.151ms
16:09:26.993 Created all serverless functions in: 364.234ms
16:09:27.010 Collected static files (public/, static/, .next/static): 4.986ms
16:09:27.320 Build Completed in /vercel/output [47s]
16:09:27.561 Deploying outputs...
16:09:39.776 Deployment completed
16:09:40.766 Creating build cache...
16:10:06.430 Created build cache: 25.663s
16:10:06.431 Uploading build cache [218.89 MB]
16:10:09.353 Build cache uploaded: 2.922s