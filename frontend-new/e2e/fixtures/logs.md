2026-01-16T23:00:40.000000000Z [inf]  Starting Container
2026-01-16T23:00:41.143786929Z [inf]  Fri Jan 16 23:00:40 2026 -> ClamAV update process started at Fri Jan 16 23:00:40 2026
2026-01-16T23:00:41.143790846Z [inf]  Fri Jan 16 23:00:40 2026 -> daily database available for update (local version: 27880, remote version: 27882)
2026-01-16T23:00:41.153596313Z [inf]  Fri Jan 16 23:00:41 2026 -> Testing database: '/var/lib/clamav/tmp.4ebe51d61c/clamav-78d604dbb56294b5c7df742e0e27595a.tmp-daily.cld' ...
2026-01-16T23:00:44.837023839Z [inf]  Fri Jan 16 23:00:44 2026 -> Database test passed.
2026-01-16T23:00:44.837033280Z [inf]  Fri Jan 16 23:00:44 2026 -> daily.cld updated (version: 27882, sigs: 354806, f-level: 90, builder: svc.clamav-publisher)
2026-01-16T23:00:44.853170759Z [inf]  Fri Jan 16 23:00:44 2026 -> main.cvd database is up-to-date (version: 63, sigs: 3287027, f-level: 90, builder: tomjudge)
2026-01-16T23:00:44.853180159Z [inf]  Fri Jan 16 23:00:44 2026 -> bytecode.cvd database is up-to-date (version: 339, sigs: 80, f-level: 90, builder: nrandolp)
2026-01-16T23:00:44.853185781Z [inf]  WARNING: Fri Jan 16 23:00:44 2026 -> Clamd was NOT notified: Can't connect to clamd through /var/run/clamav/clamd.ctl: No such file or directory
2026-01-16T23:00:44.854655200Z [inf]  🛡️ Starting ClamAV daemon...
2026-01-16T23:00:54.267338211Z [err]  /usr/local/lib/python3.11/site-packages/clamd/__init__.py:6: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
2026-01-16T23:00:54.267343252Z [err]    __version__ = __import__('pkg_resources').get_distribution('clamd').version
2026-01-16T23:00:54.390818506Z [inf]   
2026-01-16T23:00:54.390823317Z [inf]  --- ***** ----- 
2026-01-16T23:00:54.390833191Z [inf]   -------------- celery@c4701f4f4512 v5.3.6 (emerald-rush)
2026-01-16T23:00:54.390838724Z [inf]   -------------- [queues]
2026-01-16T23:00:54.390843428Z [inf]  --- ***** ----- 
2026-01-16T23:00:54.390851308Z [inf]                  .> celery           exchange=celery(direct) key=celery
2026-01-16T23:00:54.390852182Z [inf]  -- ******* ---- Linux-6.1.0-40-cloud-amd64-x86_64-with-glibc2.41 2026-01-16 23:00:54
2026-01-16T23:00:54.390861031Z [inf]  - *** --- * --- 
2026-01-16T23:00:54.390862178Z [inf]                  .> queues.embedding exchange=celery(direct) key=celery
2026-01-16T23:00:54.390871718Z [inf]                  .> queues.indexing  exchange=celery(direct) key=celery
2026-01-16T23:00:54.390882603Z [inf]                  .> queues.parsing   exchange=celery(direct) key=celery
2026-01-16T23:00:54.390892191Z [inf]  
2026-01-16T23:00:54.390894627Z [inf]  - ** ---------- [config]
2026-01-16T23:00:54.390901578Z [inf]  [tasks]
2026-01-16T23:00:54.390905075Z [inf]  - ** ---------- .> app:         axial_worker:0x7f62648e7490
2026-01-16T23:00:54.390913284Z [inf]    . finalize_job_task
2026-01-16T23:00:54.390915384Z [inf]  - ** ---------- .> transport:   redis://default:**@redis.railway.internal:6379//
2026-01-16T23:00:54.390924707Z [inf]    . process_file_task
2026-01-16T23:00:54.390927144Z [inf]  - ** ---------- .> results:     redis://default:**@redis.railway.internal:6379/
2026-01-16T23:00:54.390934709Z [inf]    . unified_ingest_task
2026-01-16T23:00:54.390941347Z [inf]    . worker.tasks.check_scheduled_crawls
2026-01-16T23:00:54.390949925Z [inf]    . worker.tasks.cleanup_old_jobs
2026-01-16T23:00:54.390968044Z [inf]  - *** --- * --- .> concurrency: 10 (gevent)
2026-01-16T23:00:54.390976446Z [inf]  -- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
2026-01-16T23:00:54.391820915Z [inf]    . worker.tasks.health_check_task
2026-01-16T23:00:54.391833976Z [inf]    . worker.tasks.index_chunks_task
2026-01-16T23:00:54.391843937Z [inf]    . worker.tasks.crawl_discovery_task
2026-01-16T23:00:54.391845532Z [inf]    . worker.tasks.process_page_task
2026-01-16T23:00:54.391853558Z [inf]    . worker.tasks.finalize_crawl_task
2026-01-16T23:00:54.391858806Z [inf]  
2026-01-16T23:00:54.391864550Z [inf]    . worker.tasks.generate_embeddings_task
2026-01-16T23:00:54.469615167Z [err]  [2026-01-16 23:00:54,457: INFO/MainProcess] Connected to redis://default:**@redis.railway.internal:6379//
2026-01-16T23:00:54.486825386Z [err]  [2026-01-16 23:00:54,483: INFO/MainProcess] mingle: searching for neighbors
2026-01-16T23:00:55.582648672Z [err]  [2026-01-16 23:00:55,580: INFO/MainProcess] mingle: sync with 1 nodes
2026-01-16T23:00:55.582657739Z [err]  [2026-01-16 23:00:55,582: INFO/MainProcess] mingle: sync complete
2026-01-16T23:00:55.616115731Z [err]  [2026-01-16 23:00:55,614: INFO/MainProcess] pidbox: Connected to redis://default:**@redis.railway.internal:6379//.
2026-01-16T23:00:55.641263439Z [err]  [2026-01-16 23:00:55,635: INFO/MainProcess] celery@c4701f4f4512 ready.
2026-01-16T23:00:56.365334613Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: Global time limit set to 120000 milliseconds.
2026-01-16T23:00:56.365348050Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: Global size limit set to 1048576000 bytes.
2026-01-16T23:00:56.365355697Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: File size limit set to 1048576000 bytes.
2026-01-16T23:00:56.365362274Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: Recursion level limit set to 17.
2026-01-16T23:00:56.365368979Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: Files limit set to 10000.
2026-01-16T23:00:56.365374577Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: Core-dump limit is 0.
2026-01-16T23:00:56.365380919Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: MaxEmbeddedPE limit set to 41943040 bytes.
2026-01-16T23:00:56.365387627Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: MaxHTMLNormalize limit set to 41943040 bytes.
2026-01-16T23:00:56.365393900Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: MaxHTMLNoTags limit set to 8388608 bytes.
2026-01-16T23:00:56.365400487Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: MaxScriptNormalize limit set to 20971520 bytes.
2026-01-16T23:00:56.365407077Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: MaxZipTypeRcg limit set to 1048576 bytes.
2026-01-16T23:00:56.365415404Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: MaxPartitions limit set to 50.
2026-01-16T23:00:56.365424176Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: MaxIconsPE limit set to 100.
2026-01-16T23:00:56.365432760Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: MaxRecHWP3 limit set to 16.
2026-01-16T23:00:56.365441431Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: PCREMatchLimit limit set to 100000.
2026-01-16T23:00:56.365450277Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: PCRERecMatchLimit limit set to 2000.
2026-01-16T23:00:56.365467364Z [inf]  Fri Jan 16 23:00:56 2026 -> Limits: PCREMaxFileSize limit set to 104857600.
2026-01-16T23:00:56.365472901Z [inf]  Fri Jan 16 23:00:56 2026 -> Archive support enabled.
2026-01-16T23:00:56.366839902Z [inf]  Fri Jan 16 23:00:56 2026 -> HTML support enabled.
2026-01-16T23:00:56.366848344Z [inf]  Fri Jan 16 23:00:56 2026 -> Image (graphics) scanning support enabled.
2026-01-16T23:00:56.366857902Z [inf]  Fri Jan 16 23:00:56 2026 -> XMLDOCS support enabled.
2026-01-16T23:00:56.366860751Z [inf]  Fri Jan 16 23:00:56 2026 -> Detection using image fuzzy hash enabled.
2026-01-16T23:00:56.366870249Z [inf]  Fri Jan 16 23:00:56 2026 -> AlertExceedsMax heuristic detection disabled.
2026-01-16T23:00:56.366875595Z [inf]  Fri Jan 16 23:00:56 2026 -> HWP3 support enabled.
2026-01-16T23:00:56.366879913Z [inf]  Fri Jan 16 23:00:56 2026 -> Heuristic alerts enabled.
2026-01-16T23:00:56.366889077Z [inf]  Fri Jan 16 23:00:56 2026 -> Portable Executable support enabled.
2026-01-16T23:00:56.366892700Z [inf]  Fri Jan 16 23:00:56 2026 -> OneNote support enabled.
2026-01-16T23:00:56.366897329Z [inf]  Fri Jan 16 23:00:56 2026 -> ELF support enabled.
2026-01-16T23:00:56.366906249Z [inf]  Fri Jan 16 23:00:56 2026 -> Mail files support enabled.
2026-01-16T23:00:56.366908059Z [inf]  Fri Jan 16 23:00:56 2026 -> Self checking every 600 seconds.
2026-01-16T23:00:56.366913601Z [inf]  Fri Jan 16 23:00:56 2026 -> OLE2 support enabled.
2026-01-16T23:00:56.366923512Z [inf]  Fri Jan 16 23:00:56 2026 -> PDF support enabled.
2026-01-16T23:00:56.366924481Z [inf]  Fri Jan 16 23:00:56 2026 -> Listening daemon: PID: 15
2026-01-16T23:00:56.366930897Z [inf]  Fri Jan 16 23:00:56 2026 -> SWF support enabled.
2026-01-16T23:00:56.366937138Z [inf]  Fri Jan 16 23:00:56 2026 -> MaxQueue set to: 100
2026-01-16T23:10:58.482174314Z [inf]  Fri Jan 16 23:10:56 2026 -> SelfCheck: Database status OK.
2026-01-16T23:21:00.325058129Z [inf]  Fri Jan 16 23:20:56 2026 -> SelfCheck: Database status OK.
2026-01-16T23:31:01.325791309Z [inf]  Fri Jan 16 23:30:56 2026 -> SelfCheck: Database status OK.
2026-01-16T23:41:02.395064078Z [inf]  Fri Jan 16 23:40:56 2026 -> SelfCheck: Database status OK.
2026-01-16T23:43:02.337031962Z [err]  [2026-01-16 23:42:52,982: INFO/MainProcess] Task unified_ingest_task[0f89e356-5fd2-4329-a7e5-4ec5c90b2f66] received
2026-01-16T23:43:02.337042458Z [err]  [2026-01-16 23:42:52,987: INFO/MainProcess] [UnifiedIngest:0f89e356-5fd2-4329-a7e5-4ec5c90b2f66] Starting FAN-OUT: file_upload, Job: 8f864d5c-7abd-40a5-acf1-0f02a5b590dd, Plan: enterprise_large
2026-01-16T23:43:02.337048632Z [err]  [2026-01-16 23:42:52,987: INFO/MainProcess] 🔌 Initializing Supabase client with connection pool
2026-01-16T23:43:02.337053758Z [err]  [2026-01-16 23:42:53,000: INFO/MainProcess] ✅ Supabase client initialized successfully
2026-01-16T23:43:02.337060434Z [err]  [2026-01-16 23:42:53,100: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?select=organization_id&id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.337066188Z [err]  [2026-01-16 23:42:53,152: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.337071399Z [err]  [2026-01-16 23:42:53,194: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?select=status&id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.337075785Z [err]  [2026-01-16 23:42:53,234: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.337080386Z [err]  [2026-01-16 23:42:53,307: INFO/MainProcess] 📊 [Job:8f864d5c-7abd-40a5-acf1-0f02a5b590dd] Status: processing, Processed: None
2026-01-16T23:43:02.337085494Z [err]  [2026-01-16 23:42:53,343: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.337089837Z [err]  [2026-01-16 23:42:53,388: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/notifications "HTTP/2 201 Created"
2026-01-16T23:43:02.337795377Z [err]  [2026-01-16 23:42:53,389: INFO/MainProcess] 🔔 [Notification] Created info: Processing Started
2026-01-16T23:43:02.337801154Z [err]  [2026-01-16 23:42:53,390: INFO/MainProcess] [UnifiedIngest:0f89e356-5fd2-4329-a7e5-4ec5c90b2f66] Streaming documents from file_upload...
2026-01-16T23:43:02.337805253Z [err]  [2026-01-16 23:42:53,480: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.337809918Z [err]  [2026-01-16 23:42:53,532: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/rpc/get_effective_plan "HTTP/2 400 Bad Request"
2026-01-16T23:43:02.337813728Z [err]  [2026-01-16 23:42:53,533: WARNING/MainProcess] [TeamService] RPC failed, trying direct query: {'message': 'column "subscription_status" does not exist', 'code': '42703', 'hint': None, 'details': None}
2026-01-16T23:43:02.337817732Z [err]  [2026-01-16 23:42:53,578: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/rpc/get_user_team_data "HTTP/2 404 Not Found"
2026-01-16T23:43:02.337821437Z [err]  [2026-01-16 23:42:53,579: WARNING/MainProcess] [TeamService] RPC call failed, falling back to sequential queries: {'message': 'Could not find the function public.get_user_team_data(target_user_id) in the schema cache', 'code': 'PGRST202', 'hint': 'Perhaps you meant to call the function public.get_user_team_data(p_user_id)', 'details': 'Searched for the function public.get_user_team_data with parameter target_user_id or with a single unnamed json/jsonb parameter, but no matches were found in the schema cache.'}
2026-01-16T23:43:02.337825536Z [err]  [2026-01-16 23:42:53,626: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:43:02.337830126Z [err]  [2026-01-16 23:42:53,675: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/subscriptions?select=plan_type%2Cstatus&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:43:02.338701563Z [err]  [2026-01-16 23:42:53,677: INFO/MainProcess] [TeamService] User 94e02b27... has active subscription: enterprise
2026-01-16T23:43:02.338706609Z [err]  [2026-01-16 23:42:53,725: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/scope_identities?select=id&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:43:02.338711054Z [err]  [2026-01-16 23:42:53,727: INFO/MainProcess] [FileUpload] Fetching: uploads/94e02b27-3523-42ff-a0c2-858dd8e77f85/61a619d2-faeb-4f29-b38d-14bbce77a603/CONFIDENTIAL_PROJECT_OMEGA.txt
2026-01-16T23:43:02.338715177Z [err]  [2026-01-16 23:42:53,740: WARNING/MainProcess] Storage endpoint URL should have a trailing slash.
2026-01-16T23:43:02.338719524Z [err]  [2026-01-16 23:42:54,160: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/storage/v1/object/ephemeral-staging/uploads/94e02b27-3523-42ff-a0c2-858dd8e77f85/61a619d2-faeb-4f29-b38d-14bbce77a603/CONFIDENTIAL_PROJECT_OMEGA.txt "HTTP/2 200 OK"
2026-01-16T23:43:02.338723902Z [err]  [2026-01-16 23:42:54,195: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status "HTTP/2 201 Created"
2026-01-16T23:43:02.338727770Z [err]  [2026-01-16 23:42:54,239: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/rpc/try_create_scope_placeholder "HTTP/2 200 OK"
2026-01-16T23:43:02.338731388Z [err]  [2026-01-16 23:42:54,240: INFO/MainProcess] [FileUpload] Fetched CONFIDENTIAL_PROJECT_OMEGA.txt (2175 bytes)
2026-01-16T23:43:02.338749088Z [err]  [2026-01-16 23:42:54,286: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.338754478Z [err]  [2026-01-16 23:42:54,311: INFO/MainProcess] Task process_file_task[fcccef43-0ccc-46db-89f4-f24076934b58] received
2026-01-16T23:43:02.338758205Z [err]  [2026-01-16 23:42:54,312: INFO/MainProcess] [ProcessFile:fcccef43-0ccc-46db-89f4-f24076934b58] Starting: CONFIDENTIAL_PROJECT_OMEGA.txt (job: 8f864d5c-7abd-40a5-acf1-0f02a5b590dd)
2026-01-16T23:43:02.339740839Z [err]  [2026-01-16 23:42:54,320: INFO/MainProcess] [UnifiedIngest:0f89e356-5fd2-4329-a7e5-4ec5c90b2f66] ✅ Dispatched batch with 1 tasks, group_id: b326e76f-9a49-4557-b040-be08f69d97e6
2026-01-16T23:43:02.339747634Z [err]  [2026-01-16 23:42:54,367: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?id=eq.18de5ebf-24de-4f0c-a23b-389c493b0aa4 "HTTP/2 200 OK"
2026-01-16T23:43:02.339753718Z [err]  [2026-01-16 23:42:54,377: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.339759462Z [err]  [2026-01-16 23:42:54,389: INFO/MainProcess] Task unified_ingest_task[0f89e356-5fd2-4329-a7e5-4ec5c90b2f66] succeeded in 1.403697095811367s: {'status': 'dispatched', 'job_id': '8f864d5c-7abd-40a5-acf1-0f02a5b590dd', 'total_files': 1, 'group_id': 'b326e76f-9a49-4557-b040-be08f69d97e6'}
2026-01-16T23:43:02.339764557Z [err]  [2026-01-16 23:42:54,423: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/storage/v1/object/ephemeral-staging/uploads/94e02b27-3523-42ff-a0c2-858dd8e77f85/61a619d2-faeb-4f29-b38d-14bbce77a603/CONFIDENTIAL_PROJECT_OMEGA.txt "HTTP/2 200 OK"
2026-01-16T23:43:02.339769523Z [err]  [2026-01-16 23:42:54,461: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?id=eq.18de5ebf-24de-4f0c-a23b-389c493b0aa4 "HTTP/2 200 OK"
2026-01-16T23:43:02.339774608Z [err]  [2026-01-16 23:42:54,529: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?id=eq.18de5ebf-24de-4f0c-a23b-389c493b0aa4 "HTTP/2 200 OK"
2026-01-16T23:43:02.339779302Z [err]  [2026-01-16 23:42:54,583: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id%2Ccontent_hash&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&source_id=eq.uploads%2F94e02b27-3523-42ff-a0c2-858dd8e77f85%2F61a619d2-faeb-4f29-b38d-14bbce77a603%2FCONFIDENTIAL_PROJECT_OMEGA.txt&limit=1 "HTTP/2 200 OK"
2026-01-16T23:43:02.340574727Z [err]  [2026-01-16 23:42:54,621: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?id=eq.18de5ebf-24de-4f0c-a23b-389c493b0aa4 "HTTP/2 200 OK"
2026-01-16T23:43:02.340583596Z [err]  [2026-01-16 23:42:54,639: INFO/MainProcess] [PlainTextProcessor] CONFIDENTIAL_PROJECT_OMEGA.txt: 3 chunks
2026-01-16T23:43:02.340589377Z [err]  [2026-01-16 23:42:54,639: INFO/MainProcess] [Factory] Processed CONFIDENTIAL_PROJECT_OMEGA.txt: 3 chunks, type=text
2026-01-16T23:43:02.340593851Z [err]  [2026-01-16 23:42:54,673: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?id=eq.18de5ebf-24de-4f0c-a23b-389c493b0aa4 "HTTP/2 200 OK"
2026-01-16T23:43:02.340597998Z [err]  [2026-01-16 23:42:54,705: INFO/MainProcess] [ProcessFile:fcccef43-0ccc-46db-89f4-f24076934b58] ✅ Dispatched embedding task for CONFIDENTIAL_PROJECT_OMEGA.txt (job: 8f864d5c-7abd-40a5-acf1-0f02a5b590dd, plan=enterprise_large)
2026-01-16T23:43:02.340602003Z [err]  [2026-01-16 23:42:54,707: INFO/MainProcess] Task worker.tasks.generate_embeddings_task[491fd691-31b6-4d6c-ba6f-ad6bb7a64478] received
2026-01-16T23:43:02.340608883Z [err]  [2026-01-16 23:42:54,748: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?id=eq.18de5ebf-24de-4f0c-a23b-389c493b0aa4 "HTTP/2 200 OK"
2026-01-16T23:43:02.340614234Z [err]  [2026-01-16 23:42:54,780: INFO/MainProcess] 📊 [Embeddings] Initialized OpenAI embeddings model (text-embedding-3-small)
2026-01-16T23:43:02.340618269Z [err]  [2026-01-16 23:42:54,800: INFO/MainProcess] HTTP Request: DELETE https://jxvcxmqqxwnracluelwq.supabase.co/storage/v1/object/ephemeral-staging "HTTP/2 200 OK"
2026-01-16T23:43:02.340622090Z [err]  [2026-01-16 23:42:54,801: INFO/MainProcess] [ProcessFile:fcccef43-0ccc-46db-89f4-f24076934b58] 🧹 Removed staged upload: uploads/94e02b27-3523-42ff-a0c2-858dd8e77f85/61a619d2-faeb-4f29-b38d-14bbce77a603/CONFIDENTIAL_PROJECT_OMEGA.txt
2026-01-16T23:43:02.341665389Z [err]  [2026-01-16 23:42:54,801: INFO/MainProcess] Task process_file_task[fcccef43-0ccc-46db-89f4-f24076934b58] succeeded in 0.48973059095442295s: {'status': 'queued_embedding', 'filename': 'CONFIDENTIAL_PROJECT_OMEGA.txt'}
2026-01-16T23:43:02.341672835Z [err]  [2026-01-16 23:42:55,552: INFO/MainProcess] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
2026-01-16T23:43:02.341678372Z [err]  [2026-01-16 23:42:55,563: INFO/MainProcess] 📊 [Embeddings] Batch 1/1: 3 texts in 0.78s (3.8/sec)
2026-01-16T23:43:02.341685214Z [err]  [2026-01-16 23:42:55,563: INFO/MainProcess] 📊 [Embeddings] Generated 3 embeddings in 1 batches (3.8/sec, rate_limit_hits=0, error_batches=0)
2026-01-16T23:43:02.341691550Z [err]  [2026-01-16 23:42:55,597: INFO/MainProcess] [EmbedTask:491fd691-31b6-4d6c-ba6f-ad6bb7a64478] ✅ Dispatched indexing for CONFIDENTIAL_PROJECT_OMEGA.txt (job: 8f864d5c-7abd-40a5-acf1-0f02a5b590dd, plan=enterprise_large)
2026-01-16T23:43:02.341698479Z [err]  [2026-01-16 23:42:55,597: INFO/MainProcess] Task worker.tasks.generate_embeddings_task[491fd691-31b6-4d6c-ba6f-ad6bb7a64478] succeeded in 0.8892653998918831s: None
2026-01-16T23:43:02.341705044Z [err]  [2026-01-16 23:42:55,616: INFO/MainProcess] Task worker.tasks.index_chunks_task[46102bbe-56fb-4d92-97ab-125279a3817c] received
2026-01-16T23:43:02.341712122Z [err]  [2026-01-16 23:42:55,656: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?id=eq.18de5ebf-24de-4f0c-a23b-389c493b0aa4 "HTTP/2 200 OK"
2026-01-16T23:43:02.341717840Z [err]  [2026-01-16 23:42:55,760: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/rpc/try_create_scope_placeholder "HTTP/2 200 OK"
2026-01-16T23:43:02.341722452Z [err]  [2026-01-16 23:42:55,795: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id%2Ccontent_hash&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&source_id=eq.uploads%2F94e02b27-3523-42ff-a0c2-858dd8e77f85%2F61a619d2-faeb-4f29-b38d-14bbce77a603%2FCONFIDENTIAL_PROJECT_OMEGA.txt&limit=1 "HTTP/2 200 OK"
2026-01-16T23:43:02.342410909Z [err]  [2026-01-16 23:42:55,831: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents "HTTP/2 201 Created"
2026-01-16T23:43:02.342417207Z [err]  [2026-01-16 23:42:55,832: INFO/MainProcess] 📄 Created document 94f07db8-a68b-43e1-8135-763b82f8c453: CONFIDENTIAL_PROJECT_OMEGA.txt
2026-01-16T23:43:02.342422210Z [err]  [2026-01-16 23:42:55,909: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/document_chunks?columns=%22document_id%22%2C%22chunk_index%22%2C%22embedding%22%2C%22content%22 "HTTP/2 201 Created"
2026-01-16T23:43:02.342425989Z [err]  [2026-01-16 23:42:55,910: INFO/MainProcess] 🧩 [DB] Inserted 3 rows into document_chunks in 0.08s (doc_id=94f07db8-a68b-43e1-8135-763b82f8c453 batch=1)
2026-01-16T23:43:02.342430089Z [err]  [2026-01-16 23:42:55,910: INFO/MainProcess] ✅ Inserted 3 chunks for document 94f07db8-a68b-43e1-8135-763b82f8c453
2026-01-16T23:43:02.342434848Z [err]  [2026-01-16 23:42:55,941: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?id=eq.18de5ebf-24de-4f0c-a23b-389c493b0aa4 "HTTP/2 200 OK"
2026-01-16T23:43:02.342438984Z [err]  [2026-01-16 23:42:56,006: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.342442592Z [err]  [2026-01-16 23:42:56,019: INFO/MainProcess] 📊 [Job:8f864d5c-7abd-40a5-acf1-0f02a5b590dd] Status: processing, Processed: 1
2026-01-16T23:43:02.342446678Z [err]  [2026-01-16 23:42:56,047: INFO/MainProcess] [IndexTask:46102bbe-56fb-4d92-97ab-125279a3817c] ✅ Stored 3 chunks for CONFIDENTIAL_PROJECT_OMEGA.txt (doc=94f07db8-a68b-43e1-8135-763b82f8c453)
2026-01-16T23:43:02.342451520Z [err]  [2026-01-16 23:42:56,047: INFO/MainProcess] Task worker.tasks.index_chunks_task[46102bbe-56fb-4d92-97ab-125279a3817c] succeeded in 0.4278089590370655s: None
2026-01-16T23:43:02.343406994Z [err]  [2026-01-16 23:42:56,069: INFO/MainProcess] Task finalize_job_task[39c40bd2-cb80-4a8f-83e0-6f52e7fc25cb] received
2026-01-16T23:43:02.343412549Z [err]  [2026-01-16 23:42:56,071: INFO/MainProcess] [FinalizeJob:39c40bd2-cb80-4a8f-83e0-6f52e7fc25cb] Finalizing job 8f864d5c-7abd-40a5-acf1-0f02a5b590dd
2026-01-16T23:43:02.343416919Z [err]  [2026-01-16 23:42:56,101: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?select=status%2Ctotal_files%2Corganization_id&id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.343420628Z [err]  [2026-01-16 23:42:56,142: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?select=status&job_id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.343424584Z [err]  [2026-01-16 23:42:56,143: INFO/MainProcess] [FinalizeJob:39c40bd2-cb80-4a8f-83e0-6f52e7fc25cb] Job 8f864d5c-7abd-40a5-acf1-0f02a5b590dd status updates: job=1 file=8 source=redis
2026-01-16T23:43:02.343428388Z [err]  [2026-01-16 23:42:56,190: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?select=document_id%2Cfilename%2Cfile_size_bytes&job_id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd&status=eq.completed "HTTP/2 200 OK"
2026-01-16T23:43:02.343431980Z [err]  [2026-01-16 23:42:56,224: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id%2Ctitle%2Cmetadata%2Cfile_size_bytes%2Csource_type%2Cscope_id&id=in.%2894f07db8-a68b-43e1-8135-763b82f8c453%29 "HTTP/2 200 OK"
2026-01-16T23:43:02.343435993Z [err]  [2026-01-16 23:42:56,264: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/scope_identities?select=id%2Cstatus%2Cattributes&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&id=eq.upload%3A%2F%2F94e02b27-3523-42ff-a0c2-858dd8e77f85%2Fmanual&limit=1 "HTTP/2 200 OK"
2026-01-16T23:43:02.344663879Z [err]  [2026-01-16 23:42:56,301: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/scope_identities?on_conflict=organization_id%2Cid "HTTP/2 200 OK"
2026-01-16T23:43:02.344673412Z [err]  [2026-01-16 23:42:56,302: INFO/MainProcess] [ScopeIdentity] ✅ Updated identity for upload://94e02b27-3523-42ff-a0c2-858dd8e77f85/manu... (1 files, file_upload)
2026-01-16T23:43:02.344680728Z [err]  [2026-01-16 23:42:57,049: INFO/MainProcess] HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
2026-01-16T23:43:02.344699539Z [err]  [2026-01-16 23:42:57,051: INFO/MainProcess] 📊 [Embeddings] Batch 1/1: 1 texts in 0.75s (1.3/sec)
2026-01-16T23:43:02.344705687Z [err]  [2026-01-16 23:42:57,051: INFO/MainProcess] 📊 [Embeddings] Generated 1 embeddings in 1 batches (1.3/sec, rate_limit_hits=0, error_batches=0)
2026-01-16T23:43:02.344716371Z [err]  [2026-01-16 23:42:57,102: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/rpc/upsert_scope_identity_document "HTTP/2 200 OK"
2026-01-16T23:43:02.344722419Z [err]  [2026-01-16 23:42:57,139: INFO/MainProcess] HTTP Request: PATCH https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?id=eq.8f864d5c-7abd-40a5-acf1-0f02a5b590dd "HTTP/2 200 OK"
2026-01-16T23:43:02.344728515Z [err]  [2026-01-16 23:42:57,219: INFO/MainProcess] HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/notifications "HTTP/2 201 Created"
2026-01-16T23:43:02.344734277Z [err]  [2026-01-16 23:42:57,220: INFO/MainProcess] 🔔 [Notification] Created success: Ingestion Complete
2026-01-16T23:43:02.344740868Z [err]  [2026-01-16 23:42:57,265: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=display_name%2Cfull_name&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 400 Bad Request"
2026-01-16T23:43:02.344746852Z [err]  [2026-01-16 23:42:57,374: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/auth/v1/admin/users/94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:43:02.345495283Z [err]  [2026-01-16 23:42:57,428: INFO/MainProcess] HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_notification_settings?select=enabled&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&setting_key=eq.email_on_ingestion_complete "HTTP/2 200 OK"
2026-01-16T23:43:02.345500231Z [err]  [2026-01-16 23:42:57,577: INFO/MainProcess] 📧 Sent ingestion complete email to o.onder@fittechs.com, id=dc5bd5d4-65a4-4ac7-8ef6-bb29c046af34
2026-01-16T23:43:02.345504035Z [err]  [2026-01-16 23:42:57,578: INFO/MainProcess] [FinalizeJob:39c40bd2-cb80-4a8f-83e0-6f52e7fc25cb] ✅ Job 8f864d5c-7abd-40a5-acf1-0f02a5b590dd: Processed 1/1 files
2026-01-16T23:43:02.345509161Z [err]  [2026-01-16 23:42:57,588: INFO/MainProcess] Task finalize_job_task[39c40bd2-cb80-4a8f-83e0-6f52e7fc25cb] succeeded in 1.5170559389516711s: None


2026-01-16T23:12:57.000000000Z [inf]  Starting Container
2026-01-16T23:12:58.534933966Z [inf]  Fri Jan 16 23:12:57 2026 -> ClamAV update process started at Fri Jan 16 23:12:57 2026
2026-01-16T23:12:58.534939464Z [inf]  Fri Jan 16 23:12:57 2026 -> daily database available for update (local version: 27880, remote version: 27882)
2026-01-16T23:12:58.643730617Z [inf]  Fri Jan 16 23:12:58 2026 -> Testing database: '/var/lib/clamav/tmp.9ac1e9c6d4/clamav-99b377fd8c0d5995fb1bb4edb29d8bbd.tmp-daily.cld' ...
2026-01-16T23:13:03.604658968Z [inf]  Fri Jan 16 23:13:02 2026 -> Database test passed.
2026-01-16T23:13:03.604665609Z [inf]  Fri Jan 16 23:13:02 2026 -> daily.cld updated (version: 27882, sigs: 354806, f-level: 90, builder: svc.clamav-publisher)
2026-01-16T23:13:03.604671496Z [inf]  Fri Jan 16 23:13:02 2026 -> main.cvd database is up-to-date (version: 63, sigs: 3287027, f-level: 90, builder: tomjudge)
2026-01-16T23:13:03.604677792Z [inf]  Fri Jan 16 23:13:02 2026 -> bytecode.cvd database is up-to-date (version: 339, sigs: 80, f-level: 90, builder: nrandolp)
2026-01-16T23:13:03.604684125Z [inf]  WARNING: Fri Jan 16 23:13:02 2026 -> Clamd was NOT notified: Can't connect to clamd through /var/run/clamav/clamd.ctl: No such file or directory
2026-01-16T23:13:03.604691117Z [inf]  🛡️ Starting ClamAV daemon...
2026-01-16T23:13:10.592653201Z [err]  2026-01-16 23:13:10,156 - main - INFO - 🔭 Sentry initialized with logging and error tracking
2026-01-16T23:13:10.592660460Z [err]  2026-01-16 23:13:10,266 - core.resilience - INFO - 🔌 Circuit breakers initialized for: OpenAI, LlamaParse, Supabase
2026-01-16T23:13:10.592667633Z [err]  2026-01-16 23:13:10,266 - core.resilience - INFO - ✅ Retry configurations loaded: OpenAI, Supabase, LlamaParse
2026-01-16T23:13:10.911155199Z [err]  2026-01-16 23:13:10,909 - main - INFO - 🔒 CORS: Loaded 2 origin(s) from ALLOWED_ORIGINS
2026-01-16T23:13:10.914661360Z [err]  2026-01-16 23:13:10,909 - main - INFO - 🔒 CORS: Production mode - 2 strict origin(s)
2026-01-16T23:13:11.675564244Z [err]  2026-01-16 23:13:11,029 - core.metrics - INFO - 📊 Prometheus metrics initialized
2026-01-16T23:13:11.675570400Z [err]  2026-01-16 23:13:11,051 - services.email - INFO - 📧 EmailService initialized with Resend API
2026-01-16T23:13:11.811353880Z [err]  2026-01-16 23:13:11,779 - worker.tasks - INFO - ✅ Worker tasks module loaded - Cache buster 001
2026-01-16T23:13:11.811515993Z [err]  /usr/local/lib/python3.11/site-packages/clamd/__init__.py:6: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
2026-01-16T23:13:11.811521876Z [err]    __version__ = __import__('pkg_resources').get_distribution('clamd').version
2026-01-16T23:13:12.737885589Z [err]  INFO:     Started server process [1]
2026-01-16T23:13:12.737890931Z [err]  INFO:     Waiting for application startup.
2026-01-16T23:13:12.737896982Z [err]  2026-01-16 23:13:12,014 - main - INFO - 🚀 Starting Axio Hub API...
2026-01-16T23:13:12.737903470Z [err]  2026-01-16 23:13:12,014 - core.db - INFO - 🔌 Initializing Supabase client with connection pool
2026-01-16T23:13:12.737909779Z [err]  2026-01-16 23:13:12,022 - core.db - INFO - ✅ Supabase client initialized successfully
2026-01-16T23:13:12.737915464Z [err]  2026-01-16 23:13:12,187 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id&limit=1 "HTTP/2 206 Partial Content"
2026-01-16T23:13:12.737921524Z [err]  2026-01-16 23:13:12,188 - main - INFO - ✅ Database connection verified
2026-01-16T23:13:12.737927207Z [err]  INFO:     Application startup complete.
2026-01-16T23:13:12.737932989Z [err]  INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
2026-01-16T23:13:15.781549254Z [inf]  Fri Jan 16 23:13:15 2026 -> Detection using image fuzzy hash enabled.
2026-01-16T23:13:15.781564901Z [inf]  Fri Jan 16 23:13:15 2026 -> AlertExceedsMax heuristic detection disabled.
2026-01-16T23:13:15.781588645Z [inf]  Fri Jan 16 23:13:15 2026 -> XMLDOCS support enabled.
2026-01-16T23:13:15.781588809Z [inf]  Fri Jan 16 23:13:15 2026 -> Listening daemon: PID: 15
2026-01-16T23:13:15.781593332Z [inf]  Fri Jan 16 23:13:15 2026 -> Heuristic alerts enabled.
2026-01-16T23:13:15.781595060Z [inf]  Fri Jan 16 23:13:15 2026 -> ELF support enabled.
2026-01-16T23:13:15.781595105Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: Global time limit set to 120000 milliseconds.
2026-01-16T23:13:15.781604902Z [inf]  Fri Jan 16 23:13:15 2026 -> Image (graphics) scanning support enabled.
2026-01-16T23:13:15.781605445Z [inf]  Fri Jan 16 23:13:15 2026 -> HWP3 support enabled.
2026-01-16T23:13:15.781605723Z [inf]  Fri Jan 16 23:13:15 2026 -> MaxQueue set to: 100
2026-01-16T23:13:15.781608832Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: Global size limit set to 1048576000 bytes.
2026-01-16T23:13:15.781616747Z [inf]  Fri Jan 16 23:13:15 2026 -> Mail files support enabled.
2026-01-16T23:13:15.781618847Z [inf]  Fri Jan 16 23:13:15 2026 -> Portable Executable support enabled.
2026-01-16T23:13:15.781621357Z [inf]  Fri Jan 16 23:13:15 2026 -> OneNote support enabled.
2026-01-16T23:13:15.781622337Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: File size limit set to 1048576000 bytes.
2026-01-16T23:13:15.781628804Z [inf]  Fri Jan 16 23:13:15 2026 -> OLE2 support enabled.
2026-01-16T23:13:15.781636547Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: Recursion level limit set to 17.
2026-01-16T23:13:15.781636807Z [inf]  Fri Jan 16 23:13:15 2026 -> Self checking every 600 seconds.
2026-01-16T23:13:15.781640442Z [inf]  Fri Jan 16 23:13:15 2026 -> PDF support enabled.
2026-01-16T23:13:15.781648649Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: Files limit set to 10000.
2026-01-16T23:13:15.781651080Z [inf]  Fri Jan 16 23:13:15 2026 -> SWF support enabled.
2026-01-16T23:13:15.781656315Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: Core-dump limit is 0.
2026-01-16T23:13:15.781662039Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: MaxEmbeddedPE limit set to 41943040 bytes.
2026-01-16T23:13:15.781669154Z [inf]  Fri Jan 16 23:13:15 2026 -> HTML support enabled.
2026-01-16T23:13:15.781676674Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: MaxHTMLNormalize limit set to 41943040 bytes.
2026-01-16T23:13:15.781686057Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: MaxHTMLNoTags limit set to 8388608 bytes.
2026-01-16T23:13:15.781692473Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: MaxScriptNormalize limit set to 20971520 bytes.
2026-01-16T23:13:15.781697500Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: MaxZipTypeRcg limit set to 1048576 bytes.
2026-01-16T23:13:15.781702766Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: MaxPartitions limit set to 50.
2026-01-16T23:13:15.781708974Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: MaxIconsPE limit set to 100.
2026-01-16T23:13:15.781714560Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: MaxRecHWP3 limit set to 16.
2026-01-16T23:13:15.781720280Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: PCREMatchLimit limit set to 100000.
2026-01-16T23:13:15.781726804Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: PCRERecMatchLimit limit set to 2000.
2026-01-16T23:13:15.781731744Z [inf]  Fri Jan 16 23:13:15 2026 -> Limits: PCREMaxFileSize limit set to 104857600.
2026-01-16T23:13:15.781737431Z [inf]  Fri Jan 16 23:13:15 2026 -> Archive support enabled.
2026-01-16T23:23:19.312352936Z [inf]  Fri Jan 16 23:23:15 2026 -> SelfCheck: Database status OK.
2026-01-16T23:33:22.850262792Z [inf]  Fri Jan 16 23:33:15 2026 -> SelfCheck: Database status OK.
2026-01-16T23:42:45.965011947Z [err]  2026-01-16 23:42:39,836 - core.tracing - INFO - ➡️  [d7e06767] GET /api/v1/billing/plans (user: eyJhbGci...)
2026-01-16T23:42:45.965015675Z [err]  2026-01-16 23:42:40,067 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:45.965019657Z [err]  2026-01-16 23:42:40,100 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:45.965023436Z [err]  2026-01-16 23:42:40,118 - core.tracing - INFO - ➡️  [bd0ce527] GET /api/v1/team/effective-plan (user: eyJhbGci...)
2026-01-16T23:42:45.965026984Z [err]  2026-01-16 23:42:40,163 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:45.965031032Z [err]  2026-01-16 23:42:40,191 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:45.965034883Z [err]  2026-01-16 23:42:40,231 - httpx - INFO - HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/rpc/get_effective_plan "HTTP/2 400 Bad Request"
2026-01-16T23:42:45.965038712Z [err]  2026-01-16 23:42:40,232 - services.team_service - WARNING - [TeamService] RPC failed, trying direct query: {'message': 'column "subscription_status" does not exist', 'code': '42703', 'hint': None, 'details': None}
2026-01-16T23:42:45.965042538Z [err]  2026-01-16 23:42:40,265 - httpx - INFO - HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/rpc/get_user_team_data "HTTP/2 404 Not Found"
2026-01-16T23:42:45.965046885Z [err]  2026-01-16 23:42:40,268 - services.team_service - WARNING - [TeamService] RPC call failed, falling back to sequential queries: {'message': 'Could not find the function public.get_user_team_data(target_user_id) in the schema cache', 'code': 'PGRST202', 'hint': 'Perhaps you meant to call the function public.get_user_team_data(p_user_id)', 'details': 'Searched for the function public.get_user_team_data with parameter target_user_id or with a single unnamed json/jsonb parameter, but no matches were found in the schema cache.'}
2026-01-16T23:42:46.003860585Z [err]  2026-01-16 23:42:42,196 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.003871531Z [err]  2026-01-16 23:42:40,303 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.003875213Z [err]  2026-01-16 23:42:42,237 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.003880666Z [err]  2026-01-16 23:42:40,337 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/subscriptions?select=plan_type%2Cstatus&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.003890390Z [err]  2026-01-16 23:42:40,338 - services.team_service - INFO - [TeamService] User 94e02b27... has active subscription: enterprise
2026-01-16T23:42:46.003894753Z [err]  2026-01-16 23:42:42,417 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.003905088Z [err]  2026-01-16 23:42:40,370 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.003906415Z [err]  2026-01-16 23:42:42,444 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.003917343Z [err]  2026-01-16 23:42:42,471 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.003921229Z [err]  2026-01-16 23:42:40,416 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.003924623Z [err]  2026-01-16 23:42:42,305 - core.tracing - INFO - ➡️  [5d4bbf3c] GET /api/v1/team/effective-plan (user: eyJhbGci...)
2026-01-16T23:42:46.003932880Z [err]  2026-01-16 23:42:40,417 - core.tracing - INFO - ✅ [bd0ce527] GET /api/v1/team/effective-plan → 200 (299.0ms)
2026-01-16T23:42:46.003933531Z [err]  2026-01-16 23:42:42,473 - core.tracing - INFO - ✅ [5d4bbf3c] GET /api/v1/team/effective-plan → 200 (167.7ms)
2026-01-16T23:42:46.003942290Z [inf]  INFO:     100.64.0.3:21360 - "GET /api/v1/team/effective-plan HTTP/1.1" 200 OK
2026-01-16T23:42:46.003947575Z [err]  2026-01-16 23:42:42,307 - httpx - INFO - HTTP Request: GET https://api.polar.sh/v1/products?is_archived=false "HTTP/1.1 307 Temporary Redirect"
2026-01-16T23:42:46.003952966Z [err]  2026-01-16 23:42:40,440 - core.tracing - INFO - ➡️  [45d8cbe2] GET /api/v1/usage (user: eyJhbGci...)
2026-01-16T23:42:46.003958270Z [err]  2026-01-16 23:42:42,365 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.003964687Z [err]  2026-01-16 23:42:40,486 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.003977082Z [err]  2026-01-16 23:42:40,524 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.004103013Z [inf]  INFO:     100.64.0.2:32048 - "GET /api/v1/team/effective-plan HTTP/1.1" 200 OK
2026-01-16T23:42:46.004116046Z [err]  2026-01-16 23:42:42,651 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.004122779Z [err]  2026-01-16 23:42:42,682 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.004129108Z [err]  2026-01-16 23:42:42,713 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=plan&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:42:46.004138298Z [err]  2026-01-16 23:42:42,477 - core.tracing - INFO - ➡️  [ac427e5e] GET /api/v1/settings/profile (user: eyJhbGci...)
2026-01-16T23:42:46.004145341Z [err]  2026-01-16 23:42:42,478 - core.tracing - INFO - ➡️  [3c4bb73a] GET /api/v1/usage (user: eyJhbGci...)
2026-01-16T23:42:46.004151384Z [err]  2026-01-16 23:42:42,511 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.004166276Z [err]  2026-01-16 23:42:42,551 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.004174815Z [err]  2026-01-16 23:42:42,588 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:42:46.004181155Z [err]  2026-01-16 23:42:42,623 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.004420731Z [err]  2026-01-16 23:42:40,557 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=plan&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:42:46.004426244Z [err]  2026-01-16 23:42:40,627 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.004431957Z [err]  2026-01-16 23:42:40,658 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/subscriptions?select=status&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.004437768Z [err]  2026-01-16 23:42:40,689 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id%2Cfile_size_bytes&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&source_type=neq.identity&source_type=neq.scope_identity "HTTP/2 200 OK"
2026-01-16T23:42:46.004443625Z [err]  2026-01-16 23:42:40,691 - core.tracing - INFO - ✅ [45d8cbe2] GET /api/v1/usage → 200 (251.6ms)
2026-01-16T23:42:46.004449902Z [err]  2026-01-16 23:42:40,692 - httpx - INFO - HTTP Request: GET https://api.polar.sh/v1/products?is_archived=false "HTTP/1.1 307 Temporary Redirect"
2026-01-16T23:42:46.004457038Z [inf]  INFO:     100.64.0.2:32060 - "GET /api/v1/usage HTTP/1.1" 200 OK
2026-01-16T23:42:46.004463034Z [err]  2026-01-16 23:42:40,778 - httpx - INFO - HTTP Request: GET https://api.polar.sh/v1/products/?is_archived=false "HTTP/1.1 200 OK"
2026-01-16T23:42:46.004469327Z [err]  2026-01-16 23:42:40,781 - core.tracing - INFO - ✅ [d7e06767] GET /api/v1/billing/plans → 200 (945.4ms)
2026-01-16T23:42:46.004474980Z [inf]  INFO:     100.64.0.2:32048 - "GET /api/v1/billing/plans HTTP/1.1" 200 OK
2026-01-16T23:42:46.004481276Z [err]  2026-01-16 23:42:42,158 - core.tracing - INFO - ➡️  [943468cf] GET /api/v1/billing/plans (user: eyJhbGci...)
2026-01-16T23:42:46.005276486Z [err]  2026-01-16 23:42:42,745 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.005281972Z [err]  2026-01-16 23:42:42,803 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/subscriptions?select=status&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.005288256Z [err]  2026-01-16 23:42:42,832 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id%2Cfile_size_bytes&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&source_type=neq.identity&source_type=neq.scope_identity "HTTP/2 200 OK"
2026-01-16T23:42:46.005293501Z [err]  2026-01-16 23:42:42,835 - core.tracing - INFO - ✅ [ac427e5e] GET /api/v1/settings/profile → 200 (358.2ms)
2026-01-16T23:42:46.005300134Z [err]  2026-01-16 23:42:42,836 - core.tracing - INFO - ✅ [3c4bb73a] GET /api/v1/usage → 200 (357.2ms)
2026-01-16T23:42:46.005305188Z [err]  2026-01-16 23:42:42,836 - httpx - INFO - HTTP Request: GET https://api.polar.sh/v1/products/?is_archived=false "HTTP/1.1 200 OK"
2026-01-16T23:42:46.005310864Z [inf]  INFO:     100.64.0.4:16020 - "GET /api/v1/settings/profile HTTP/1.1" 200 OK
2026-01-16T23:42:46.005316739Z [inf]  INFO:     100.64.0.4:16026 - "GET /api/v1/usage HTTP/1.1" 200 OK
2026-01-16T23:42:46.005322307Z [err]  2026-01-16 23:42:42,844 - core.tracing - INFO - ✅ [943468cf] GET /api/v1/billing/plans → 200 (686.3ms)
2026-01-16T23:42:46.005328382Z [inf]  INFO:     100.64.0.3:21360 - "GET /api/v1/billing/plans HTTP/1.1" 200 OK
2026-01-16T23:42:46.005334668Z [err]  2026-01-16 23:42:42,931 - core.tracing - INFO - ➡️  [cfacdeb8] GET /api/v1/team/effective-plan (user: eyJhbGci...)
2026-01-16T23:42:46.005340759Z [err]  2026-01-16 23:42:42,981 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.005533780Z [err]  2026-01-16 23:42:43,019 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.005539633Z [err]  2026-01-16 23:42:43,051 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.005548190Z [err]  2026-01-16 23:42:43,077 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.005553267Z [err]  2026-01-16 23:42:43,080 - core.tracing - INFO - ✅ [cfacdeb8] GET /api/v1/team/effective-plan → 200 (148.5ms)
2026-01-16T23:42:46.005558458Z [err]  2026-01-16 23:42:43,082 - core.tracing - INFO - ➡️  [7d777b32] GET /api/v1/usage (user: eyJhbGci...)
2026-01-16T23:42:46.005563940Z [err]  2026-01-16 23:42:43,083 - core.tracing - INFO - ➡️  [20d26aad] GET /api/v1/settings/profile (user: eyJhbGci...)
2026-01-16T23:42:46.005569103Z [err]  2026-01-16 23:42:43,111 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.005575141Z [err]  2026-01-16 23:42:43,139 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.005580557Z [err]  2026-01-16 23:42:43,166 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=plan&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:42:46.005585381Z [err]  2026-01-16 23:42:43,200 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.008510766Z [err]  2026-01-16 23:42:43,227 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/subscriptions?select=status&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.008516436Z [err]  2026-01-16 23:42:43,258 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id%2Cfile_size_bytes&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&source_type=neq.identity&source_type=neq.scope_identity "HTTP/2 200 OK"
2026-01-16T23:42:46.008522416Z [err]  2026-01-16 23:42:43,295 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.008527229Z [err]  2026-01-16 23:42:43,321 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.008532317Z [err]  2026-01-16 23:42:43,363 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:42:46.008537764Z [err]  2026-01-16 23:42:43,409 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.008544180Z [inf]  INFO:     100.64.0.4:16026 - "GET /api/v1/team/effective-plan HTTP/1.1" 200 OK
2026-01-16T23:42:46.008549224Z [err]  2026-01-16 23:42:43,415 - core.tracing - INFO - ✅ [7d777b32] GET /api/v1/usage → 200 (333.0ms)
2026-01-16T23:42:46.008554362Z [err]  2026-01-16 23:42:43,415 - core.tracing - INFO - ✅ [20d26aad] GET /api/v1/settings/profile → 200 (332.3ms)
2026-01-16T23:42:46.008560083Z [inf]  INFO:     100.64.0.2:32048 - "GET /api/v1/usage HTTP/1.1" 200 OK
2026-01-16T23:42:46.008665957Z [inf]  INFO:     100.64.0.2:32060 - "GET /api/v1/settings/profile HTTP/1.1" 200 OK
2026-01-16T23:42:46.008672535Z [err]  2026-01-16 23:42:43,418 - core.tracing - INFO - ➡️  [11f3dc0a] GET /api/v1/billing/plans (user: eyJhbGci...)
2026-01-16T23:42:46.008677907Z [err]  2026-01-16 23:42:43,460 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.008683826Z [err]  2026-01-16 23:42:43,490 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.008689636Z [err]  2026-01-16 23:42:43,573 - httpx - INFO - HTTP Request: GET https://api.polar.sh/v1/products?is_archived=false "HTTP/1.1 307 Temporary Redirect"
2026-01-16T23:42:46.008695471Z [err]  2026-01-16 23:42:43,665 - httpx - INFO - HTTP Request: GET https://api.polar.sh/v1/products/?is_archived=false "HTTP/1.1 200 OK"
2026-01-16T23:42:46.008701599Z [err]  2026-01-16 23:42:43,667 - core.tracing - INFO - ✅ [11f3dc0a] GET /api/v1/billing/plans → 200 (249.2ms)
2026-01-16T23:42:46.008708107Z [inf]  INFO:     100.64.0.5:43004 - "GET /api/v1/billing/plans HTTP/1.1" 200 OK
2026-01-16T23:42:46.008715096Z [err]  2026-01-16 23:42:43,704 - core.tracing - INFO - ➡️  [e1874b49] GET /api/v1/conversations (user: eyJhbGci...)
2026-01-16T23:42:46.008722863Z [err]  2026-01-16 23:42:43,734 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.008728778Z [err]  2026-01-16 23:42:43,763 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.009568551Z [err]  2026-01-16 23:42:43,794 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.009574933Z [err]  2026-01-16 23:42:43,826 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.009580670Z [err]  2026-01-16 23:42:43,863 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/conversations?select=%2A&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&order=updated_at.desc "HTTP/2 200 OK"
2026-01-16T23:42:46.010025502Z [err]  2026-01-16 23:42:43,865 - core.tracing - INFO - ✅ [e1874b49] GET /api/v1/conversations → 200 (160.1ms)
2026-01-16T23:42:46.010036737Z [inf]  INFO:     100.64.0.2:32060 - "GET /api/v1/conversations HTTP/1.1" 200 OK
2026-01-16T23:42:46.010048477Z [err]  2026-01-16 23:42:43,969 - core.tracing - INFO - ➡️  [b2efbd61] GET /api/v1/settings/profile (user: eyJhbGci...)
2026-01-16T23:42:46.010056753Z [err]  2026-01-16 23:42:44,001 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.010063541Z [err]  2026-01-16 23:42:44,037 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.010071203Z [err]  2026-01-16 23:42:44,069 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:42:46.010078594Z [err]  2026-01-16 23:42:44,103 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.011805202Z [err]  2026-01-16 23:42:44,105 - core.tracing - INFO - ✅ [b2efbd61] GET /api/v1/settings/profile → 200 (135.9ms)
2026-01-16T23:42:46.011811373Z [err]  2026-01-16 23:42:44,106 - core.tracing - INFO - ➡️  [ea21efb6] GET /api/v1/documents (user: eyJhbGci...)
2026-01-16T23:42:46.011816688Z [err]  2026-01-16 23:42:44,106 - core.tracing - INFO - ➡️  [2e4d6627] GET /api/v1/notifications/unread-count (user: eyJhbGci...)
2026-01-16T23:42:46.011822638Z [err]  2026-01-16 23:42:44,137 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.011827814Z [err]  2026-01-16 23:42:44,167 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.011838278Z [err]  2026-01-16 23:42:44,232 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.011843419Z [err]  2026-01-16 23:42:44,257 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.011848405Z [err]  2026-01-16 23:42:44,304 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=%2A&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&source_type=neq.identity&source_type=neq.scope_identity&order=created_at.desc&offset=0&limit=10 "HTTP/2 206 Partial Content"
2026-01-16T23:42:46.011853031Z [err]  2026-01-16 23:42:44,338 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_file_status?select=%2A&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&status=eq.failed&document_id=is.null&order=created_at.desc&limit=10 "HTTP/2 200 OK"
2026-01-16T23:42:46.014795172Z [err]  2026-01-16 23:42:44,437 - core.tracing - INFO - ✅ [ea21efb6] GET /api/v1/documents → 200 (331.3ms)
2026-01-16T23:42:46.014807361Z [err]  2026-01-16 23:42:44,437 - core.tracing - INFO - ✅ [2e4d6627] GET /api/v1/notifications/unread-count → 200 (330.9ms)
2026-01-16T23:42:46.014814781Z [err]  2026-01-16 23:42:44,438 - core.tracing - INFO - ➡️  [001621ff] GET /api/v1/integrations/status (user: eyJhbGci...)
2026-01-16T23:42:46.014822756Z [err]  2026-01-16 23:42:44,470 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.014830420Z [err]  2026-01-16 23:42:44,500 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.014838377Z [err]  2026-01-16 23:42:44,537 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations?select=id%2Cconnector_definition_id%2Clast_sync_at%2Cconnector_definitions%28type%2Cname%2Cicon_path%2Ccategory%29&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:42:46.014857454Z [err]  2026-01-16 23:42:44,373 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.014862148Z [err]  2026-01-16 23:42:44,403 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.014867683Z [err]  2026-01-16 23:42:44,434 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/notifications?select=id&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&is_read=eq.False "HTTP/2 200 OK"
2026-01-16T23:42:46.014872113Z [inf]  INFO:     100.64.0.3:21360 - "GET /api/v1/settings/profile HTTP/1.1" 200 OK
2026-01-16T23:42:46.017276590Z [err]  2026-01-16 23:42:44,859 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.017309698Z [inf]  INFO:     100.64.0.5:43004 - "GET /api/v1/documents?limit=10&offset=0&q= HTTP/1.1" 200 OK
2026-01-16T23:42:46.017316574Z [inf]  INFO:     100.64.0.4:16026 - "GET /api/v1/notifications/unread-count HTTP/1.1" 200 OK
2026-01-16T23:42:46.017327775Z [err]  2026-01-16 23:42:44,541 - core.tracing - INFO - ✅ [001621ff] GET /api/v1/integrations/status → 200 (102.2ms)
2026-01-16T23:42:46.017333227Z [err]  2026-01-16 23:42:44,541 - core.tracing - INFO - ➡️  [c5d812ab] GET /api/v1/integrations/available (user: eyJhbGci...)
2026-01-16T23:42:46.017338979Z [err]  2026-01-16 23:42:44,570 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:46.017344512Z [err]  2026-01-16 23:42:44,611 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.017350065Z [err]  2026-01-16 23:42:44,643 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/connector_definitions?select=%2A&is_active=eq.True "HTTP/2 200 OK"
2026-01-16T23:42:46.017353969Z [inf]  INFO:     100.64.0.4:16020 - "GET /api/v1/integrations/status HTTP/1.1" 200 OK
2026-01-16T23:42:46.017359784Z [err]  2026-01-16 23:42:44,653 - core.tracing - INFO - ✅ [c5d812ab] GET /api/v1/integrations/available → 200 (111.2ms)
2026-01-16T23:42:46.017366580Z [inf]  INFO:     100.64.0.4:16050 - "GET /api/v1/integrations/available HTTP/1.1" 200 OK
2026-01-16T23:42:46.017371774Z [err]  2026-01-16 23:42:44,816 - core.tracing - INFO - ➡️  [399b253a] GET /api/v1/notifications/unread-count (user: eyJhbGci...)
2026-01-16T23:42:46.025043671Z [err]  2026-01-16 23:42:44,916 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:46.025049903Z [err]  2026-01-16 23:42:44,943 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/notifications?select=id&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&is_read=eq.False "HTTP/2 200 OK"
2026-01-16T23:42:46.025055346Z [err]  2026-01-16 23:42:44,945 - core.tracing - INFO - ✅ [399b253a] GET /api/v1/notifications/unread-count → 200 (128.8ms)
2026-01-16T23:42:46.025061469Z [inf]  INFO:     100.64.0.2:32060 - "GET /api/v1/notifications/unread-count HTTP/1.1" 200 OK
2026-01-16T23:42:51.132549666Z [err]  2026-01-16 23:42:50,324 - core.tracing - INFO - ➡️  [33fa21fe] POST /api/v1/uploads/upload-url (user: eyJhbGci...)
2026-01-16T23:42:51.132556404Z [err]  2026-01-16 23:42:50,392 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:51.132563278Z [err]  2026-01-16 23:42:50,434 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:51.132569821Z [err]  2026-01-16 23:42:50,468 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:51.132577510Z [err]  2026-01-16 23:42:50,515 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:51.132585112Z [err]  2026-01-16 23:42:50,552 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:51.132591119Z [err]  2026-01-16 23:42:50,584 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:51.132598356Z [err]  2026-01-16 23:42:50,625 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=plan&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:42:51.132604428Z [err]  2026-01-16 23:42:50,668 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:51.133018972Z [err]  2026-01-16 23:42:50,796 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/org_usage?select=storage_used_mb%2Cjob_count_cycle&org_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:51.133028963Z [err]  2026-01-16 23:42:50,835 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:51.133036803Z [err]  2026-01-16 23:42:50,880 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=member_user_id&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:51.133042210Z [err]  2026-01-16 23:42:50,917 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?select=id&user_id=in.%2894e02b27-3523-42ff-a0c2-858dd8e77f85%2C3cbf4dbe-c5a4-4253-b72b-6b89a15859ab%29&status=in.%28pending%2Cprocessing%29 "HTTP/2 200 OK"
2026-01-16T23:42:51.133047904Z [inf]  Storage endpoint URL should have a trailing slash.
2026-01-16T23:42:51.133125074Z [err]  2026-01-16 23:42:51,031 - httpx - INFO - HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/storage/v1/object/upload/sign/ephemeral-staging/uploads/94e02b27-3523-42ff-a0c2-858dd8e77f85/61a619d2-faeb-4f29-b38d-14bbce77a603/CONFIDENTIAL_PROJECT_OMEGA.txt "HTTP/2 200 OK"
2026-01-16T23:42:51.133130841Z [err]  2026-01-16 23:42:50,699 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/subscriptions?select=status&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:51.133145447Z [err]  2026-01-16 23:42:50,735 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id%2Cfile_size_bytes&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&source_type=neq.identity&source_type=neq.scope_identity "HTTP/2 200 OK"
2026-01-16T23:42:51.135928203Z [err]  2026-01-16 23:42:51,032 - api.v1.uploads - INFO - [Upload] Generated presigned URL for CONFIDENTIAL_PROJECT_OMEGA.txt (uploads/94e02b27-3523-42ff-a0c2-858dd8e77f85/61a619d2-faeb-4f29-b38d-14bbce77a603/CONFIDENTIAL_PROJECT_OMEGA.txt)
2026-01-16T23:42:51.135932889Z [err]  2026-01-16 23:42:51,033 - core.tracing - INFO - ✅ [33fa21fe] POST /api/v1/uploads/upload-url → 200 (709.3ms)
2026-01-16T23:42:51.135938477Z [inf]  INFO:     100.64.0.4:50950 - "POST /api/v1/uploads/upload-url HTTP/1.1" 200 OK
2026-01-16T23:42:51.972096278Z [err]  2026-01-16 23:42:51,965 - core.tracing - INFO - ➡️  [ebdda500] POST /api/v1/uploads/file/reference (user: eyJhbGci...)
2026-01-16T23:42:52.031105077Z [err]  2026-01-16 23:42:52,023 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:52.075180905Z [err]  2026-01-16 23:42:52,072 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:52.107892024Z [err]  2026-01-16 23:42:52,102 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:52.154826147Z [err]  2026-01-16 23:42:52,149 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:52.243545878Z [err]  2026-01-16 23:42:52,218 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole%2Cjoined_at&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:52.251979877Z [err]  2026-01-16 23:42:52,249 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:53.119153711Z [err]  2026-01-16 23:42:52,544 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/documents?select=id%2Cfile_size_bytes&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&source_type=neq.identity&source_type=neq.scope_identity "HTTP/2 200 OK"
2026-01-16T23:42:53.119164684Z [err]  2026-01-16 23:42:52,591 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/org_usage?select=storage_used_mb%2Cjob_count_cycle&org_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:53.119171701Z [err]  2026-01-16 23:42:52,627 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:53.119266319Z [err]  2026-01-16 23:42:52,674 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=member_user_id&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
2026-01-16T23:42:53.119276277Z [err]  2026-01-16 23:42:52,716 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs?select=id&user_id=in.%2894e02b27-3523-42ff-a0c2-858dd8e77f85%2C3cbf4dbe-c5a4-4253-b72b-6b89a15859ab%29&status=in.%28pending%2Cprocessing%29 "HTTP/2 200 OK"
2026-01-16T23:42:53.119317028Z [err]  2026-01-16 23:42:52,305 - httpx - INFO - HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/storage/v1/object/list/ephemeral-staging "HTTP/2 200 OK"
2026-01-16T23:42:53.119327370Z [err]  2026-01-16 23:42:52,359 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_profiles?select=plan&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85 "HTTP/2 200 OK"
2026-01-16T23:42:53.119335186Z [err]  2026-01-16 23:42:52,409 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:53.119343344Z [err]  2026-01-16 23:42:52,452 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/subscriptions?select=status&team_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:42:53.127102103Z [err]  2026-01-16 23:42:52,987 - core.tracing - INFO - ✅ [ebdda500] POST /api/v1/uploads/file/reference → 200 (1021.7ms)
2026-01-16T23:42:53.127239679Z [err]  2026-01-16 23:42:52,884 - httpx - INFO - HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/org_usage?on_conflict=org_id "HTTP/2 200 OK"
2026-01-16T23:42:53.127249107Z [err]  2026-01-16 23:42:52,886 - services.quotas - INFO - ✅ [Quotas] Incremented usage org=3cbf4dbe-c5a4-4253-b72b-6b89a15859ab storage+=0.00MB jobs+=1
2026-01-16T23:42:53.127258984Z [inf]  INFO:     100.64.0.4:50950 - "POST /api/v1/uploads/file/reference HTTP/1.1" 200 OK
2026-01-16T23:42:53.127267293Z [err]  2026-01-16 23:42:52,986 - api.v1.uploads - INFO - [Upload] Unified task queued: CONFIDENTIAL_PROJECT_OMEGA.txt, task=0f89e356-5fd2-4329-a7e5-4ec5c90b2f66
2026-01-16T23:42:53.127306845Z [err]  2026-01-16 23:42:52,755 - httpx - INFO - HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs "HTTP/2 201 Created"
2026-01-16T23:42:53.127313513Z [err]  2026-01-16 23:42:52,810 - httpx - INFO - HTTP Request: POST https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/audit_logs "HTTP/2 201 Created"
2026-01-16T23:42:53.127319057Z [err]  2026-01-16 23:42:52,846 - httpx - INFO - HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/org_usage?select=storage_used_mb%2Cjob_count_cycle&org_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab&limit=1 "HTTP/2 200 OK"
2026-01-16T23:43:23.140463643Z [inf]  Fri Jan 16 23:43:15 2026 -> SelfCheck: Database status OK.


2026-01-12T20:41:45.471995742Z [inf]  1:M 12 Jan 2026 20:41:44.164 * 1 changes in 60 seconds. Saving...
2026-01-12T20:41:45.472001255Z [inf]  1:M 12 Jan 2026 20:41:44.165 * Background saving started by pid 298
2026-01-12T20:41:45.472005878Z [inf]  298:C 12 Jan 2026 20:41:44.202 * DB saved on disk
2026-01-12T20:41:45.472011438Z [inf]  298:C 12 Jan 2026 20:41:44.203 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-12T20:41:45.472017869Z [inf]  1:M 12 Jan 2026 20:41:44.266 * Background saving terminated with success
2026-01-12T20:42:45.485921923Z [inf]  1:M 12 Jan 2026 20:42:45.054 * 1 changes in 60 seconds. Saving...
2026-01-12T20:42:45.485928208Z [inf]  1:M 12 Jan 2026 20:42:45.056 * Background saving started by pid 299
2026-01-12T20:42:45.485932980Z [inf]  299:C 12 Jan 2026 20:42:45.069 * DB saved on disk
2026-01-12T20:42:45.485936983Z [inf]  299:C 12 Jan 2026 20:42:45.070 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-12T20:42:45.485942239Z [inf]  1:M 12 Jan 2026 20:42:45.156 * Background saving terminated with success
2026-01-12T21:05:57.264141673Z [inf]  1:M 12 Jan 2026 21:05:52.439 * 1 changes in 60 seconds. Saving...
2026-01-12T21:05:57.264153109Z [inf]  1:M 12 Jan 2026 21:05:52.440 * Background saving started by pid 300
2026-01-12T21:05:57.264160391Z [inf]  300:C 12 Jan 2026 21:05:52.463 * DB saved on disk
2026-01-12T21:05:57.264166766Z [inf]  300:C 12 Jan 2026 21:05:52.464 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-12T21:05:57.264172707Z [inf]  1:M 12 Jan 2026 21:05:52.541 * Background saving terminated with success
2026-01-12T21:06:57.264218479Z [inf]  1:M 12 Jan 2026 21:06:53.063 * 1 changes in 60 seconds. Saving...
2026-01-12T21:06:57.264227147Z [inf]  1:M 12 Jan 2026 21:06:53.064 * Background saving started by pid 301
2026-01-12T21:06:57.264234010Z [inf]  301:C 12 Jan 2026 21:06:53.105 * DB saved on disk
2026-01-12T21:06:57.264240765Z [inf]  301:C 12 Jan 2026 21:06:53.107 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-12T21:06:57.264246883Z [inf]  1:M 12 Jan 2026 21:06:53.166 * Background saving terminated with success
2026-01-12T21:39:19.008805110Z [inf]  1:M 12 Jan 2026 21:39:17.606 * 1 changes in 60 seconds. Saving...
2026-01-12T21:39:19.008812170Z [inf]  1:M 12 Jan 2026 21:39:17.607 * Background saving started by pid 302
2026-01-12T21:39:19.008817051Z [inf]  302:C 12 Jan 2026 21:39:17.630 * DB saved on disk
2026-01-12T21:39:19.008824043Z [inf]  302:C 12 Jan 2026 21:39:17.631 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-12T21:39:19.008828901Z [inf]  1:M 12 Jan 2026 21:39:17.708 * Background saving terminated with success
2026-01-12T21:40:19.016784446Z [inf]  1:M 12 Jan 2026 21:40:18.010 * 1 changes in 60 seconds. Saving...
2026-01-12T21:40:19.016792895Z [inf]  1:M 12 Jan 2026 21:40:18.011 * Background saving started by pid 303
2026-01-12T21:40:19.016799124Z [inf]  303:C 12 Jan 2026 21:40:18.024 * DB saved on disk
2026-01-12T21:40:19.016804468Z [inf]  303:C 12 Jan 2026 21:40:18.025 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-12T21:40:19.016808797Z [inf]  1:M 12 Jan 2026 21:40:18.112 * Background saving terminated with success
2026-01-13T05:38:09.392858339Z [inf]  1:M 13 Jan 2026 05:38:07.133 * 1 changes in 60 seconds. Saving...
2026-01-13T05:38:09.392866508Z [inf]  1:M 13 Jan 2026 05:38:07.134 * Background saving started by pid 304
2026-01-13T05:38:09.392873403Z [inf]  304:C 13 Jan 2026 05:38:07.147 * DB saved on disk
2026-01-13T05:38:09.392879741Z [inf]  304:C 13 Jan 2026 05:38:07.148 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T05:38:09.392884461Z [inf]  1:M 13 Jan 2026 05:38:07.235 * Background saving terminated with success
2026-01-13T05:39:09.341245780Z [inf]  1:M 13 Jan 2026 05:39:08.030 * 1 changes in 60 seconds. Saving...
2026-01-13T05:39:09.341256778Z [inf]  1:M 13 Jan 2026 05:39:08.031 * Background saving started by pid 305
2026-01-13T05:39:09.341263024Z [inf]  305:C 13 Jan 2026 05:39:08.064 * DB saved on disk
2026-01-13T05:39:09.341272592Z [inf]  305:C 13 Jan 2026 05:39:08.065 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T05:39:09.341278373Z [inf]  1:M 13 Jan 2026 05:39:08.132 * Background saving terminated with success
2026-01-13T09:14:35.442197422Z [inf]  306:C 13 Jan 2026 09:14:31.267 * DB saved on disk
2026-01-13T09:14:35.442202065Z [inf]  1:M 13 Jan 2026 09:14:31.215 * 1 changes in 60 seconds. Saving...
2026-01-13T09:14:35.442208631Z [inf]  1:M 13 Jan 2026 09:14:31.216 * Background saving started by pid 306
2026-01-13T09:14:35.442210164Z [inf]  306:C 13 Jan 2026 09:14:31.267 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:14:35.442216693Z [inf]  1:M 13 Jan 2026 09:14:31.316 * Background saving terminated with success
2026-01-13T09:15:35.429418474Z [inf]  1:M 13 Jan 2026 09:15:32.015 * 1 changes in 60 seconds. Saving...
2026-01-13T09:15:35.429422404Z [inf]  1:M 13 Jan 2026 09:15:32.016 * Background saving started by pid 307
2026-01-13T09:15:35.429426494Z [inf]  307:C 13 Jan 2026 09:15:32.040 * DB saved on disk
2026-01-13T09:15:35.429430763Z [inf]  307:C 13 Jan 2026 09:15:32.041 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:15:35.429434956Z [inf]  1:M 13 Jan 2026 09:15:32.117 * Background saving terminated with success
2026-01-13T09:21:25.450537053Z [inf]  1:M 13 Jan 2026 09:21:22.106 * 1 changes in 60 seconds. Saving...
2026-01-13T09:21:25.450544020Z [inf]  1:M 13 Jan 2026 09:21:22.107 * Background saving started by pid 308
2026-01-13T09:21:25.450553085Z [inf]  308:C 13 Jan 2026 09:21:22.127 * DB saved on disk
2026-01-13T09:21:25.450560427Z [inf]  308:C 13 Jan 2026 09:21:22.128 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:21:25.450565286Z [inf]  1:M 13 Jan 2026 09:21:22.207 * Background saving terminated with success
2026-01-13T09:22:25.450559361Z [inf]  1:M 13 Jan 2026 09:22:23.008 * 1 changes in 60 seconds. Saving...
2026-01-13T09:22:25.450565015Z [inf]  1:M 13 Jan 2026 09:22:23.009 * Background saving started by pid 309
2026-01-13T09:22:25.450569599Z [inf]  309:C 13 Jan 2026 09:22:23.021 * DB saved on disk
2026-01-13T09:22:25.450575366Z [inf]  309:C 13 Jan 2026 09:22:23.022 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:22:25.450579669Z [inf]  1:M 13 Jan 2026 09:22:23.110 * Background saving terminated with success
2026-01-13T09:48:17.862485338Z [inf]  1:M 13 Jan 2026 09:48:16.607 * 1 changes in 60 seconds. Saving...
2026-01-13T09:48:17.862496296Z [inf]  1:M 13 Jan 2026 09:48:16.609 * Background saving started by pid 310
2026-01-13T09:48:17.862501890Z [inf]  310:C 13 Jan 2026 09:48:16.621 * DB saved on disk
2026-01-13T09:48:17.862506540Z [inf]  310:C 13 Jan 2026 09:48:16.621 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:48:17.862511417Z [inf]  1:M 13 Jan 2026 09:48:16.710 * Background saving terminated with success
2026-01-13T09:49:17.863764725Z [inf]  1:M 13 Jan 2026 09:49:17.011 * 1 changes in 60 seconds. Saving...
2026-01-13T09:49:17.863772869Z [inf]  1:M 13 Jan 2026 09:49:17.012 * Background saving started by pid 311
2026-01-13T09:49:17.863778098Z [inf]  311:C 13 Jan 2026 09:49:17.038 * DB saved on disk
2026-01-13T09:49:17.863783287Z [inf]  311:C 13 Jan 2026 09:49:17.039 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:49:17.863788981Z [inf]  1:M 13 Jan 2026 09:49:17.114 * Background saving terminated with success
2026-01-13T09:50:27.877091354Z [inf]  1:M 13 Jan 2026 09:50:18.009 * 1 changes in 60 seconds. Saving...
2026-01-13T09:50:27.877102158Z [inf]  1:M 13 Jan 2026 09:50:18.010 * Background saving started by pid 312
2026-01-13T09:50:27.877108839Z [inf]  312:C 13 Jan 2026 09:50:18.042 * DB saved on disk
2026-01-13T09:50:27.877114633Z [inf]  312:C 13 Jan 2026 09:50:18.043 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:50:27.877119578Z [inf]  1:M 13 Jan 2026 09:50:18.111 * Background saving terminated with success
2026-01-13T09:51:27.882843267Z [inf]  1:M 13 Jan 2026 09:51:25.341 * 1 changes in 60 seconds. Saving...
2026-01-13T09:51:27.882850063Z [inf]  1:M 13 Jan 2026 09:51:25.342 * Background saving started by pid 313
2026-01-13T09:51:27.882855367Z [inf]  313:C 13 Jan 2026 09:51:25.360 * DB saved on disk
2026-01-13T09:51:27.882860005Z [inf]  313:C 13 Jan 2026 09:51:25.361 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:51:27.882864048Z [inf]  1:M 13 Jan 2026 09:51:25.443 * Background saving terminated with success
2026-01-13T09:52:27.887092163Z [inf]  1:M 13 Jan 2026 09:52:26.100 * 1 changes in 60 seconds. Saving...
2026-01-13T09:52:27.887103306Z [inf]  1:M 13 Jan 2026 09:52:26.101 * Background saving started by pid 314
2026-01-13T09:52:27.887108957Z [inf]  314:C 13 Jan 2026 09:52:26.345 * DB saved on disk
2026-01-13T09:52:27.887114662Z [inf]  314:C 13 Jan 2026 09:52:26.346 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 1 MB
2026-01-13T09:52:27.887120168Z [inf]  1:M 13 Jan 2026 09:52:26.404 * Background saving terminated with success
2026-01-13T09:55:07.907507522Z [inf]  1:M 13 Jan 2026 09:55:04.672 * 1 changes in 60 seconds. Saving...
2026-01-13T09:55:07.907517745Z [inf]  1:M 13 Jan 2026 09:55:04.674 * Background saving started by pid 315
2026-01-13T09:55:07.907523717Z [inf]  315:C 13 Jan 2026 09:55:04.694 * DB saved on disk
2026-01-13T09:55:07.907528776Z [inf]  315:C 13 Jan 2026 09:55:04.695 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:55:07.907533701Z [inf]  1:M 13 Jan 2026 09:55:04.775 * Background saving terminated with success
2026-01-13T09:56:07.937780748Z [inf]  1:M 13 Jan 2026 09:56:05.020 * 1 changes in 60 seconds. Saving...
2026-01-13T09:56:07.937796151Z [inf]  1:M 13 Jan 2026 09:56:05.021 * Background saving started by pid 316
2026-01-13T09:56:07.937805645Z [inf]  316:C 13 Jan 2026 09:56:05.039 * DB saved on disk
2026-01-13T09:56:07.937813271Z [inf]  316:C 13 Jan 2026 09:56:05.040 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:56:07.937822001Z [inf]  1:M 13 Jan 2026 09:56:05.122 * Background saving terminated with success
2026-01-13T09:57:37.874643100Z [inf]  1:M 13 Jan 2026 09:57:37.257 * 1 changes in 60 seconds. Saving...
2026-01-13T09:57:37.874648252Z [inf]  1:M 13 Jan 2026 09:57:37.258 * Background saving started by pid 317
2026-01-13T09:57:37.874652466Z [inf]  317:C 13 Jan 2026 09:57:37.323 * DB saved on disk
2026-01-13T09:57:37.874656848Z [inf]  317:C 13 Jan 2026 09:57:37.324 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:57:37.874661604Z [inf]  1:M 13 Jan 2026 09:57:37.359 * Background saving terminated with success
2026-01-13T09:58:47.885745502Z [inf]  1:M 13 Jan 2026 09:58:38.078 * 1 changes in 60 seconds. Saving...
2026-01-13T09:58:47.885755321Z [inf]  1:M 13 Jan 2026 09:58:38.079 * Background saving started by pid 318
2026-01-13T09:58:47.885761536Z [inf]  318:C 13 Jan 2026 09:58:38.108 * DB saved on disk
2026-01-13T09:58:47.885768234Z [inf]  318:C 13 Jan 2026 09:58:38.109 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:58:47.885774765Z [inf]  1:M 13 Jan 2026 09:58:38.180 * Background saving terminated with success
2026-01-13T09:59:47.889264950Z [inf]  1:M 13 Jan 2026 09:59:39.031 * 1 changes in 60 seconds. Saving...
2026-01-13T09:59:47.889272112Z [inf]  1:M 13 Jan 2026 09:59:39.032 * Background saving started by pid 319
2026-01-13T09:59:47.889276778Z [inf]  319:C 13 Jan 2026 09:59:39.068 * DB saved on disk
2026-01-13T09:59:47.889282159Z [inf]  319:C 13 Jan 2026 09:59:39.068 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T09:59:47.889287591Z [inf]  1:M 13 Jan 2026 09:59:39.133 * Background saving terminated with success
2026-01-13T10:00:47.902205002Z [inf]  1:M 13 Jan 2026 10:00:40.039 * 1 changes in 60 seconds. Saving...
2026-01-13T10:00:47.902211691Z [inf]  1:M 13 Jan 2026 10:00:40.040 * Background saving started by pid 320
2026-01-13T10:00:47.902216053Z [inf]  320:C 13 Jan 2026 10:00:40.124 * DB saved on disk
2026-01-13T10:00:47.902220077Z [inf]  320:C 13 Jan 2026 10:00:40.125 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T10:00:47.902224304Z [inf]  1:M 13 Jan 2026 10:00:40.141 * Background saving terminated with success
2026-01-13T10:04:17.951822376Z [inf]  1:M 13 Jan 2026 10:04:09.063 * 1 changes in 60 seconds. Saving...
2026-01-13T10:04:17.951831714Z [inf]  1:M 13 Jan 2026 10:04:09.064 * Background saving started by pid 321
2026-01-13T10:04:17.951837589Z [inf]  321:C 13 Jan 2026 10:04:09.092 * DB saved on disk
2026-01-13T10:04:17.951843057Z [inf]  321:C 13 Jan 2026 10:04:09.093 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T10:04:17.951848099Z [inf]  1:M 13 Jan 2026 10:04:09.164 * Background saving terminated with success
2026-01-13T10:05:18.049169567Z [inf]  1:M 13 Jan 2026 10:05:10.077 * 1 changes in 60 seconds. Saving...
2026-01-13T10:05:18.049175900Z [inf]  1:M 13 Jan 2026 10:05:10.078 * Background saving started by pid 322
2026-01-13T10:05:18.049180559Z [inf]  322:C 13 Jan 2026 10:05:10.091 * DB saved on disk
2026-01-13T10:05:18.049184936Z [inf]  322:C 13 Jan 2026 10:05:10.092 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T10:05:18.049190338Z [inf]  1:M 13 Jan 2026 10:05:10.179 * Background saving terminated with success
2026-01-13T10:06:17.998259386Z [inf]  1:M 13 Jan 2026 10:06:11.078 * 1 changes in 60 seconds. Saving...
2026-01-13T10:06:17.998266788Z [inf]  1:M 13 Jan 2026 10:06:11.078 * Background saving started by pid 323
2026-01-13T10:06:17.998271895Z [inf]  323:C 13 Jan 2026 10:06:11.106 * DB saved on disk
2026-01-13T10:06:17.998278094Z [inf]  323:C 13 Jan 2026 10:06:11.107 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T10:06:17.998283644Z [inf]  1:M 13 Jan 2026 10:06:11.180 * Background saving terminated with success
2026-01-13T10:07:18.006781013Z [inf]  1:M 13 Jan 2026 10:07:12.089 * 1 changes in 60 seconds. Saving...
2026-01-13T10:07:18.006789802Z [inf]  1:M 13 Jan 2026 10:07:12.090 * Background saving started by pid 324
2026-01-13T10:07:18.006794369Z [inf]  324:C 13 Jan 2026 10:07:12.105 * DB saved on disk
2026-01-13T10:07:18.006798691Z [inf]  324:C 13 Jan 2026 10:07:12.106 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T10:07:18.006802745Z [inf]  1:M 13 Jan 2026 10:07:12.191 * Background saving terminated with success
2026-01-13T10:11:18.048470298Z [inf]  1:M 13 Jan 2026 10:11:14.048 * 1 changes in 60 seconds. Saving...
2026-01-13T10:11:18.048478635Z [inf]  1:M 13 Jan 2026 10:11:14.048 * Background saving started by pid 325
2026-01-13T10:11:18.048484908Z [inf]  325:C 13 Jan 2026 10:11:14.070 * DB saved on disk
2026-01-13T10:11:18.048491271Z [inf]  325:C 13 Jan 2026 10:11:14.071 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T10:11:18.048497214Z [inf]  1:M 13 Jan 2026 10:11:14.149 * Background saving terminated with success
2026-01-13T10:12:18.052423112Z [inf]  1:M 13 Jan 2026 10:12:15.066 * 1 changes in 60 seconds. Saving...
2026-01-13T10:12:18.052429572Z [inf]  1:M 13 Jan 2026 10:12:15.067 * Background saving started by pid 326
2026-01-13T10:12:18.052434034Z [inf]  326:C 13 Jan 2026 10:12:15.077 * DB saved on disk
2026-01-13T10:12:18.052438094Z [inf]  326:C 13 Jan 2026 10:12:15.078 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T10:12:18.052441736Z [inf]  1:M 13 Jan 2026 10:12:15.167 * Background saving terminated with success
2026-01-13T11:28:23.454722494Z [inf]  1:M 13 Jan 2026 11:28:13.653 * 1 changes in 60 seconds. Saving...
2026-01-13T11:28:23.454729116Z [inf]  1:M 13 Jan 2026 11:28:13.654 * Background saving started by pid 327
2026-01-13T11:28:23.454733625Z [inf]  327:C 13 Jan 2026 11:28:13.673 * DB saved on disk
2026-01-13T11:28:23.454739545Z [inf]  327:C 13 Jan 2026 11:28:13.674 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T11:28:23.454743540Z [inf]  1:M 13 Jan 2026 11:28:13.754 * Background saving terminated with success
2026-01-13T11:29:23.468947245Z [inf]  1:M 13 Jan 2026 11:29:14.070 * 1 changes in 60 seconds. Saving...
2026-01-13T11:29:23.468960667Z [inf]  1:M 13 Jan 2026 11:29:14.071 * Background saving started by pid 328
2026-01-13T11:29:23.468967973Z [inf]  328:C 13 Jan 2026 11:29:14.092 * DB saved on disk
2026-01-13T11:29:23.468974581Z [inf]  328:C 13 Jan 2026 11:29:14.092 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T11:29:23.468979549Z [inf]  1:M 13 Jan 2026 11:29:14.171 * Background saving terminated with success
2026-01-13T12:32:29.420280645Z [inf]  1:M 13 Jan 2026 12:32:20.234 * 1 changes in 60 seconds. Saving...
2026-01-13T12:32:29.420287785Z [inf]  1:M 13 Jan 2026 12:32:20.235 * Background saving started by pid 329
2026-01-13T12:32:29.420292851Z [inf]  329:C 13 Jan 2026 12:32:20.264 * DB saved on disk
2026-01-13T12:32:29.420297218Z [inf]  329:C 13 Jan 2026 12:32:20.265 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T12:32:29.420300950Z [inf]  1:M 13 Jan 2026 12:32:20.336 * Background saving terminated with success
2026-01-13T12:33:29.429118758Z [inf]  1:M 13 Jan 2026 12:33:21.037 * 1 changes in 60 seconds. Saving...
2026-01-13T12:33:29.429129237Z [inf]  1:M 13 Jan 2026 12:33:21.038 * Background saving started by pid 330
2026-01-13T12:33:29.429135538Z [inf]  330:C 13 Jan 2026 12:33:21.074 * DB saved on disk
2026-01-13T12:33:29.429141165Z [inf]  330:C 13 Jan 2026 12:33:21.075 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T12:33:29.429148356Z [inf]  1:M 13 Jan 2026 12:33:21.139 * Background saving terminated with success
2026-01-13T12:41:59.893437956Z [inf]  1:M 13 Jan 2026 12:41:51.500 * 1 changes in 60 seconds. Saving...
2026-01-13T12:41:59.893448169Z [inf]  1:M 13 Jan 2026 12:41:51.500 * Background saving started by pid 331
2026-01-13T12:41:59.893453927Z [inf]  331:C 13 Jan 2026 12:41:51.514 * DB saved on disk
2026-01-13T12:41:59.893460670Z [inf]  331:C 13 Jan 2026 12:41:51.515 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T12:41:59.893466567Z [inf]  1:M 13 Jan 2026 12:41:51.601 * Background saving terminated with success
2026-01-13T12:42:59.797306784Z [inf]  1:M 13 Jan 2026 12:42:52.093 * 1 changes in 60 seconds. Saving...
2026-01-13T12:42:59.797315090Z [inf]  1:M 13 Jan 2026 12:42:52.094 * Background saving started by pid 332
2026-01-13T12:42:59.797321499Z [inf]  332:C 13 Jan 2026 12:42:52.131 * DB saved on disk
2026-01-13T12:42:59.797327465Z [inf]  332:C 13 Jan 2026 12:42:52.132 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T12:42:59.797333030Z [inf]  1:M 13 Jan 2026 12:42:52.195 * Background saving terminated with success
2026-01-13T12:51:20.079245159Z [inf]  1:M 13 Jan 2026 12:51:14.808 * 1 changes in 60 seconds. Saving...
2026-01-13T12:51:20.079257361Z [inf]  1:M 13 Jan 2026 12:51:14.809 * Background saving started by pid 333
2026-01-13T12:51:20.079264361Z [inf]  333:C 13 Jan 2026 12:51:14.821 * DB saved on disk
2026-01-13T12:51:20.079270699Z [inf]  333:C 13 Jan 2026 12:51:14.822 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T12:51:20.079276212Z [inf]  1:M 13 Jan 2026 12:51:14.910 * Background saving terminated with success
2026-01-13T12:52:20.177405902Z [inf]  1:M 13 Jan 2026 12:52:15.097 * 1 changes in 60 seconds. Saving...
2026-01-13T12:52:20.177413285Z [inf]  1:M 13 Jan 2026 12:52:15.098 * Background saving started by pid 334
2026-01-13T12:52:20.177419343Z [inf]  334:C 13 Jan 2026 12:52:15.111 * DB saved on disk
2026-01-13T12:52:20.177423500Z [inf]  334:C 13 Jan 2026 12:52:15.112 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T12:52:20.177427999Z [inf]  1:M 13 Jan 2026 12:52:15.199 * Background saving terminated with success
2026-01-13T13:09:20.823003482Z [inf]  1:M 13 Jan 2026 13:09:13.949 * 1 changes in 60 seconds. Saving...
2026-01-13T13:09:20.823008430Z [inf]  1:M 13 Jan 2026 13:09:13.950 * Background saving started by pid 335
2026-01-13T13:09:20.823014231Z [inf]  335:C 13 Jan 2026 13:09:14.004 * DB saved on disk
2026-01-13T13:09:20.823019344Z [inf]  335:C 13 Jan 2026 13:09:14.005 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T13:09:20.823023884Z [inf]  1:M 13 Jan 2026 13:09:14.051 * Background saving terminated with success
2026-01-13T13:10:20.749924536Z [inf]  1:M 13 Jan 2026 13:10:15.051 * 1 changes in 60 seconds. Saving...
2026-01-13T13:10:20.749931213Z [inf]  1:M 13 Jan 2026 13:10:15.052 * Background saving started by pid 336
2026-01-13T13:10:20.749937413Z [inf]  336:C 13 Jan 2026 13:10:15.067 * DB saved on disk
2026-01-13T13:10:20.749943069Z [inf]  336:C 13 Jan 2026 13:10:15.067 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T13:10:20.749947892Z [inf]  1:M 13 Jan 2026 13:10:15.153 * Background saving terminated with success
2026-01-13T15:24:01.544213295Z [inf]  1:M 13 Jan 2026 15:23:56.082 * 1 changes in 60 seconds. Saving...
2026-01-13T15:24:01.544223284Z [inf]  1:M 13 Jan 2026 15:23:56.083 * Background saving started by pid 337
2026-01-13T15:24:01.544230133Z [inf]  337:C 13 Jan 2026 15:23:56.102 * DB saved on disk
2026-01-13T15:24:01.544238863Z [inf]  337:C 13 Jan 2026 15:23:56.103 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T15:24:01.544244530Z [inf]  1:M 13 Jan 2026 15:23:56.184 * Background saving terminated with success
2026-01-13T15:25:01.481677023Z [inf]  1:M 13 Jan 2026 15:24:57.092 * 1 changes in 60 seconds. Saving...
2026-01-13T15:25:01.481687796Z [inf]  1:M 13 Jan 2026 15:24:57.093 * Background saving started by pid 338
2026-01-13T15:25:01.481695341Z [inf]  338:C 13 Jan 2026 15:24:57.115 * DB saved on disk
2026-01-13T15:25:01.481702549Z [inf]  338:C 13 Jan 2026 15:24:57.116 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T15:25:01.481709087Z [inf]  1:M 13 Jan 2026 15:24:57.194 * Background saving terminated with success
2026-01-13T15:43:23.073035712Z [inf]  1:M 13 Jan 2026 15:43:19.048 * 1 changes in 60 seconds. Saving...
2026-01-13T15:43:23.073042971Z [inf]  1:M 13 Jan 2026 15:43:19.049 * Background saving started by pid 339
2026-01-13T15:43:23.073048646Z [inf]  339:C 13 Jan 2026 15:43:19.067 * DB saved on disk
2026-01-13T15:43:23.073053892Z [inf]  339:C 13 Jan 2026 15:43:19.068 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T15:43:23.073059182Z [inf]  1:M 13 Jan 2026 15:43:19.150 * Background saving terminated with success
2026-01-13T15:44:22.999317651Z [inf]  1:M 13 Jan 2026 15:44:20.054 * 1 changes in 60 seconds. Saving...
2026-01-13T15:44:22.999324551Z [inf]  1:M 13 Jan 2026 15:44:20.055 * Background saving started by pid 340
2026-01-13T15:44:22.999329433Z [inf]  340:C 13 Jan 2026 15:44:20.068 * DB saved on disk
2026-01-13T15:44:22.999333870Z [inf]  340:C 13 Jan 2026 15:44:20.069 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T15:44:22.999337857Z [inf]  1:M 13 Jan 2026 15:44:20.156 * Background saving terminated with success
2026-01-13T17:10:08.581623703Z [inf]  1:M 13 Jan 2026 17:09:59.221 * 1 changes in 60 seconds. Saving...
2026-01-13T17:10:08.581633138Z [inf]  1:M 13 Jan 2026 17:09:59.222 * Background saving started by pid 341
2026-01-13T17:10:08.581640281Z [inf]  341:C 13 Jan 2026 17:09:59.240 * DB saved on disk
2026-01-13T17:10:08.581644985Z [inf]  341:C 13 Jan 2026 17:09:59.241 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T17:10:08.581649755Z [inf]  1:M 13 Jan 2026 17:09:59.323 * Background saving terminated with success
2026-01-13T17:11:08.599803442Z [inf]  1:M 13 Jan 2026 17:11:00.027 * 1 changes in 60 seconds. Saving...
2026-01-13T17:11:08.599812787Z [inf]  1:M 13 Jan 2026 17:11:00.028 * Background saving started by pid 342
2026-01-13T17:11:08.599818469Z [inf]  342:C 13 Jan 2026 17:11:00.049 * DB saved on disk
2026-01-13T17:11:08.599823644Z [inf]  342:C 13 Jan 2026 17:11:00.050 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T17:11:08.599830246Z [inf]  1:M 13 Jan 2026 17:11:00.129 * Background saving terminated with success
2026-01-13T17:12:08.621356492Z [inf]  1:M 13 Jan 2026 17:12:01.031 * 1 changes in 60 seconds. Saving...
2026-01-13T17:12:08.621364446Z [inf]  1:M 13 Jan 2026 17:12:01.032 * Background saving started by pid 343
2026-01-13T17:12:08.621371022Z [inf]  343:C 13 Jan 2026 17:12:01.053 * DB saved on disk
2026-01-13T17:12:08.621376854Z [inf]  343:C 13 Jan 2026 17:12:01.054 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T17:12:08.621382080Z [inf]  1:M 13 Jan 2026 17:12:01.133 * Background saving terminated with success
2026-01-13T19:19:11.922112053Z [inf]  1:M 13 Jan 2026 19:19:10.546 * 1 changes in 60 seconds. Saving...
2026-01-13T19:19:11.922125231Z [inf]  1:M 13 Jan 2026 19:19:10.547 * Background saving started by pid 391
2026-01-13T19:19:11.922133243Z [inf]  391:C 13 Jan 2026 19:19:10.564 * DB saved on disk
2026-01-13T19:19:11.922139268Z [inf]  391:C 13 Jan 2026 19:19:10.565 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T19:19:11.922144706Z [inf]  1:M 13 Jan 2026 19:19:10.648 * Background saving terminated with success
2026-01-13T19:20:11.933664235Z [inf]  1:M 13 Jan 2026 19:20:11.054 * 1 changes in 60 seconds. Saving...
2026-01-13T19:20:11.933673563Z [inf]  1:M 13 Jan 2026 19:20:11.056 * Background saving started by pid 392
2026-01-13T19:20:11.933679485Z [inf]  392:C 13 Jan 2026 19:20:11.072 * DB saved on disk
2026-01-13T19:20:11.933685866Z [inf]  392:C 13 Jan 2026 19:20:11.072 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T19:20:11.933691238Z [inf]  1:M 13 Jan 2026 19:20:11.157 * Background saving terminated with success
2026-01-13T19:26:12.627408487Z [inf]  1:M 13 Jan 2026 19:26:08.237 * 1 changes in 60 seconds. Saving...
2026-01-13T19:26:12.627415946Z [inf]  1:M 13 Jan 2026 19:26:08.238 * Background saving started by pid 393
2026-01-13T19:26:12.627421185Z [inf]  393:C 13 Jan 2026 19:26:08.313 * DB saved on disk
2026-01-13T19:26:12.627428144Z [inf]  393:C 13 Jan 2026 19:26:08.314 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T19:26:12.627432519Z [inf]  1:M 13 Jan 2026 19:26:08.339 * Background saving terminated with success
2026-01-13T19:27:12.531895883Z [inf]  1:M 13 Jan 2026 19:27:09.044 * 1 changes in 60 seconds. Saving...
2026-01-13T19:27:12.531903171Z [inf]  1:M 13 Jan 2026 19:27:09.045 * Background saving started by pid 394
2026-01-13T19:27:12.531908042Z [inf]  394:C 13 Jan 2026 19:27:09.061 * DB saved on disk
2026-01-13T19:27:12.531912967Z [inf]  394:C 13 Jan 2026 19:27:09.062 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T19:27:12.531919350Z [inf]  1:M 13 Jan 2026 19:27:09.146 * Background saving terminated with success
2026-01-13T19:29:32.551527810Z [inf]  1:M 13 Jan 2026 19:29:24.515 * 1 changes in 60 seconds. Saving...
2026-01-13T19:29:32.551536488Z [inf]  1:M 13 Jan 2026 19:29:24.516 * Background saving started by pid 395
2026-01-13T19:29:32.551542594Z [inf]  395:C 13 Jan 2026 19:29:24.530 * DB saved on disk
2026-01-13T19:29:32.551547269Z [inf]  395:C 13 Jan 2026 19:29:24.531 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T19:29:32.551551759Z [inf]  1:M 13 Jan 2026 19:29:24.617 * Background saving terminated with success
2026-01-13T19:30:32.548890011Z [inf]  1:M 13 Jan 2026 19:30:25.024 * 1 changes in 60 seconds. Saving...
2026-01-13T19:30:32.548897429Z [inf]  1:M 13 Jan 2026 19:30:25.025 * Background saving started by pid 396
2026-01-13T19:30:32.548902320Z [inf]  396:C 13 Jan 2026 19:30:25.038 * DB saved on disk
2026-01-13T19:30:32.548907426Z [inf]  396:C 13 Jan 2026 19:30:25.039 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T19:30:32.548912366Z [inf]  1:M 13 Jan 2026 19:30:25.125 * Background saving terminated with success
2026-01-13T19:31:32.558974642Z [inf]  1:M 13 Jan 2026 19:31:26.041 * 1 changes in 60 seconds. Saving...
2026-01-13T19:31:32.558982521Z [inf]  1:M 13 Jan 2026 19:31:26.042 * Background saving started by pid 397
2026-01-13T19:31:32.558989088Z [inf]  397:C 13 Jan 2026 19:31:26.061 * DB saved on disk
2026-01-13T19:31:32.558993906Z [inf]  397:C 13 Jan 2026 19:31:26.062 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T19:31:32.558999136Z [inf]  1:M 13 Jan 2026 19:31:26.143 * Background saving terminated with success
2026-01-13T19:36:13.224906467Z [inf]  1:M 13 Jan 2026 19:36:10.476 * 1 changes in 60 seconds. Saving...
2026-01-13T19:36:13.224913933Z [inf]  1:M 13 Jan 2026 19:36:10.477 * Background saving started by pid 398
2026-01-13T19:36:13.224918879Z [inf]  398:C 13 Jan 2026 19:36:10.526 * DB saved on disk
2026-01-13T19:36:13.224923832Z [inf]  398:C 13 Jan 2026 19:36:10.526 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 1 MB
2026-01-13T19:36:13.224928238Z [inf]  1:M 13 Jan 2026 19:36:10.579 * Background saving terminated with success
2026-01-13T19:37:13.167717052Z [inf]  1:M 13 Jan 2026 19:37:11.052 * 1 changes in 60 seconds. Saving...
2026-01-13T19:37:13.167729904Z [inf]  1:M 13 Jan 2026 19:37:11.074 * Background saving started by pid 399
2026-01-13T19:37:33.168142942Z [inf]  399:C 13 Jan 2026 19:37:28.976 * DB saved on disk
2026-01-13T19:37:33.168151883Z [inf]  399:C 13 Jan 2026 19:37:28.979 * Fork CoW for RDB: current 9 MB, peak 9 MB, average 5 MB
2026-01-13T19:37:33.168158057Z [inf]  1:M 13 Jan 2026 19:37:29.053 * Background saving terminated with success
2026-01-13T19:38:33.194067778Z [inf]  1:M 13 Jan 2026 19:38:30.092 * 1 changes in 60 seconds. Saving...
2026-01-13T19:38:33.194075722Z [inf]  1:M 13 Jan 2026 19:38:30.108 * Background saving started by pid 400
2026-01-13T19:38:42.948629312Z [inf]  400:C 13 Jan 2026 19:38:42.946 * DB saved on disk
2026-01-13T19:38:42.949222401Z [inf]  400:C 13 Jan 2026 19:38:42.948 * Fork CoW for RDB: current 23 MB, peak 23 MB, average 12 MB
2026-01-13T19:38:43.043863360Z [inf]  1:M 13 Jan 2026 19:38:43.040 * Background saving terminated with success
2026-01-13T19:39:53.045632893Z [inf]  1:M 13 Jan 2026 19:39:44.023 * 1 changes in 60 seconds. Saving...
2026-01-13T19:39:53.045640644Z [inf]  1:M 13 Jan 2026 19:39:44.028 * Background saving started by pid 401
2026-01-13T19:39:53.045646464Z [inf]  401:C 13 Jan 2026 19:39:45.303 * DB saved on disk
2026-01-13T19:39:53.045652287Z [inf]  401:C 13 Jan 2026 19:39:45.304 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 1 MB
2026-01-13T19:39:53.045657600Z [inf]  1:M 13 Jan 2026 19:39:45.334 * Background saving terminated with success
2026-01-13T19:41:03.052758797Z [inf]  1:M 13 Jan 2026 19:40:55.380 * 1 changes in 60 seconds. Saving...
2026-01-13T19:41:03.052767315Z [inf]  1:M 13 Jan 2026 19:40:55.384 * Background saving started by pid 402
2026-01-13T19:41:03.052773696Z [inf]  402:C 13 Jan 2026 19:40:56.628 * DB saved on disk
2026-01-13T19:41:03.052780102Z [inf]  402:C 13 Jan 2026 19:40:56.629 * Fork CoW for RDB: current 2 MB, peak 2 MB, average 1 MB
2026-01-13T19:41:03.052786124Z [inf]  1:M 13 Jan 2026 19:40:56.691 * Background saving terminated with success
2026-01-13T19:42:03.116878295Z [inf]  1:M 13 Jan 2026 19:41:57.088 * 1 changes in 60 seconds. Saving...
2026-01-13T19:42:03.116888255Z [inf]  1:M 13 Jan 2026 19:41:57.090 * Background saving started by pid 403
2026-01-13T19:42:03.116894753Z [inf]  403:C 13 Jan 2026 19:41:57.105 * DB saved on disk
2026-01-13T19:42:03.116900898Z [inf]  403:C 13 Jan 2026 19:41:57.106 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T19:42:03.116913529Z [inf]  1:M 13 Jan 2026 19:41:57.191 * Background saving terminated with success
2026-01-13T21:40:14.952152395Z [inf]  1:M 13 Jan 2026 21:40:12.330 * 1 changes in 60 seconds. Saving...
2026-01-13T21:40:14.952164524Z [inf]  1:M 13 Jan 2026 21:40:12.333 * Background saving started by pid 404
2026-01-13T21:40:14.952172662Z [inf]  404:C 13 Jan 2026 21:40:12.854 * DB saved on disk
2026-01-13T21:40:14.952182019Z [inf]  404:C 13 Jan 2026 21:40:12.856 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 1 MB
2026-01-13T21:40:14.952191666Z [inf]  1:M 13 Jan 2026 21:40:12.937 * Background saving terminated with success
2026-01-13T21:41:15.059221954Z [inf]  1:M 13 Jan 2026 21:41:13.030 * 1 changes in 60 seconds. Saving...
2026-01-13T21:41:15.059230350Z [inf]  1:M 13 Jan 2026 21:41:13.033 * Background saving started by pid 405
2026-01-13T21:41:15.059236409Z [inf]  405:C 13 Jan 2026 21:41:13.047 * DB saved on disk
2026-01-13T21:41:15.059241432Z [inf]  405:C 13 Jan 2026 21:41:13.048 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-13T21:41:15.059245634Z [inf]  1:M 13 Jan 2026 21:41:13.134 * Background saving terminated with success
2026-01-14T07:00:21.135483550Z [inf]  1:M 14 Jan 2026 07:00:17.704 * 1 changes in 60 seconds. Saving...
2026-01-14T07:00:21.135487669Z [inf]  1:M 14 Jan 2026 07:00:17.707 * Background saving started by pid 406
2026-01-14T07:00:21.135491486Z [inf]  406:C 14 Jan 2026 07:00:17.781 * DB saved on disk
2026-01-14T07:00:21.135495470Z [inf]  406:C 14 Jan 2026 07:00:17.784 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T07:00:21.135499186Z [inf]  1:M 14 Jan 2026 07:00:17.808 * Background saving terminated with success
2026-01-14T07:01:21.059787114Z [inf]  1:M 14 Jan 2026 07:01:18.006 * 1 changes in 60 seconds. Saving...
2026-01-14T07:01:21.059795850Z [inf]  1:M 14 Jan 2026 07:01:18.009 * Background saving started by pid 407
2026-01-14T07:01:21.059802439Z [inf]  407:C 14 Jan 2026 07:01:18.040 * DB saved on disk
2026-01-14T07:01:21.059813457Z [inf]  407:C 14 Jan 2026 07:01:18.042 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T07:01:21.059819389Z [inf]  1:M 14 Jan 2026 07:01:18.110 * Background saving terminated with success
2026-01-14T07:43:25.365241323Z [inf]  1:M 14 Jan 2026 07:43:22.480 * 1 changes in 60 seconds. Saving...
2026-01-14T07:43:25.365246877Z [inf]  1:M 14 Jan 2026 07:43:22.483 * Background saving started by pid 408
2026-01-14T07:43:25.365252716Z [inf]  408:C 14 Jan 2026 07:43:22.497 * DB saved on disk
2026-01-14T07:43:25.365368820Z [inf]  408:C 14 Jan 2026 07:43:22.499 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T07:43:25.365375039Z [inf]  1:M 14 Jan 2026 07:43:22.583 * Background saving terminated with success
2026-01-14T07:44:25.487303327Z [inf]  1:M 14 Jan 2026 07:44:23.073 * 1 changes in 60 seconds. Saving...
2026-01-14T07:44:25.487310586Z [inf]  1:M 14 Jan 2026 07:44:23.076 * Background saving started by pid 409
2026-01-14T07:44:25.487319100Z [inf]  409:C 14 Jan 2026 07:44:23.113 * DB saved on disk
2026-01-14T07:44:25.487325791Z [inf]  409:C 14 Jan 2026 07:44:23.115 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 0 MB
2026-01-14T07:44:25.487330349Z [inf]  1:M 14 Jan 2026 07:44:23.177 * Background saving terminated with success
2026-01-14T07:45:25.416949324Z [inf]  1:M 14 Jan 2026 07:45:24.023 * 1 changes in 60 seconds. Saving...
2026-01-14T07:45:25.416957612Z [inf]  1:M 14 Jan 2026 07:45:24.025 * Background saving started by pid 410
2026-01-14T07:45:25.416965163Z [inf]  410:C 14 Jan 2026 07:45:24.064 * DB saved on disk
2026-01-14T07:45:25.416970220Z [inf]  410:C 14 Jan 2026 07:45:24.066 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T07:45:25.416974684Z [inf]  1:M 14 Jan 2026 07:45:24.127 * Background saving terminated with success
2026-01-14T09:07:01.991235748Z [inf]  1:M 14 Jan 2026 09:06:58.471 * 1 changes in 60 seconds. Saving...
2026-01-14T09:07:01.991246235Z [inf]  1:M 14 Jan 2026 09:06:58.473 * Background saving started by pid 411
2026-01-14T09:07:01.991252404Z [inf]  411:C 14 Jan 2026 09:06:58.501 * DB saved on disk
2026-01-14T09:07:01.991258045Z [inf]  411:C 14 Jan 2026 09:06:58.503 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T09:07:01.991263247Z [inf]  1:M 14 Jan 2026 09:06:58.577 * Background saving terminated with success
2026-01-14T09:08:02.119730258Z [inf]  1:M 14 Jan 2026 09:07:59.067 * 1 changes in 60 seconds. Saving...
2026-01-14T09:08:02.119739965Z [inf]  1:M 14 Jan 2026 09:07:59.070 * Background saving started by pid 412
2026-01-14T09:08:02.119751097Z [inf]  412:C 14 Jan 2026 09:07:59.087 * DB saved on disk
2026-01-14T09:08:02.119759055Z [inf]  412:C 14 Jan 2026 09:07:59.089 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T09:08:02.119765139Z [inf]  1:M 14 Jan 2026 09:07:59.170 * Background saving terminated with success
2026-01-14T09:28:43.479586689Z [inf]  1:M 14 Jan 2026 09:28:37.268 * 1 changes in 60 seconds. Saving...
2026-01-14T09:28:43.479596406Z [inf]  1:M 14 Jan 2026 09:28:37.272 * Background saving started by pid 413
2026-01-14T09:28:43.479603701Z [inf]  413:C 14 Jan 2026 09:28:37.290 * DB saved on disk
2026-01-14T09:28:43.479609769Z [inf]  413:C 14 Jan 2026 09:28:37.291 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T09:28:43.479615325Z [inf]  1:M 14 Jan 2026 09:28:37.372 * Background saving terminated with success
2026-01-14T09:29:43.479712010Z [inf]  1:M 14 Jan 2026 09:29:38.062 * 1 changes in 60 seconds. Saving...
2026-01-14T09:29:43.479719372Z [inf]  1:M 14 Jan 2026 09:29:38.065 * Background saving started by pid 414
2026-01-14T09:29:43.479725796Z [inf]  414:C 14 Jan 2026 09:29:38.097 * DB saved on disk
2026-01-14T09:29:43.479730100Z [inf]  414:C 14 Jan 2026 09:29:38.098 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 0 MB
2026-01-14T09:29:43.479734342Z [inf]  1:M 14 Jan 2026 09:29:38.165 * Background saving terminated with success
2026-01-14T09:30:43.486605844Z [inf]  1:M 14 Jan 2026 09:30:39.019 * 1 changes in 60 seconds. Saving...
2026-01-14T09:30:43.486614789Z [inf]  1:M 14 Jan 2026 09:30:39.022 * Background saving started by pid 415
2026-01-14T09:30:43.486621430Z [inf]  415:C 14 Jan 2026 09:30:39.036 * DB saved on disk
2026-01-14T09:30:43.486626580Z [inf]  415:C 14 Jan 2026 09:30:39.038 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T09:30:43.486631310Z [inf]  1:M 14 Jan 2026 09:30:39.123 * Background saving terminated with success
2026-01-14T11:25:00.380690544Z [inf]  1:M 14 Jan 2026 11:24:54.529 * 1 changes in 60 seconds. Saving...
2026-01-14T11:25:00.380704366Z [inf]  1:M 14 Jan 2026 11:24:54.532 * Background saving started by pid 417
2026-01-14T11:25:00.380713224Z [inf]  417:C 14 Jan 2026 11:24:54.563 * DB saved on disk
2026-01-14T11:25:00.380720154Z [inf]  417:C 14 Jan 2026 11:24:54.565 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T11:25:00.380726701Z [inf]  1:M 14 Jan 2026 11:24:54.633 * Background saving terminated with success
2026-01-14T11:26:00.381998875Z [inf]  1:M 14 Jan 2026 11:25:55.051 * 1 changes in 60 seconds. Saving...
2026-01-14T11:26:00.382006234Z [inf]  1:M 14 Jan 2026 11:25:55.054 * Background saving started by pid 418
2026-01-14T11:26:00.382012380Z [inf]  418:C 14 Jan 2026 11:25:55.077 * DB saved on disk
2026-01-14T11:26:00.382018978Z [inf]  418:C 14 Jan 2026 11:25:55.079 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T11:26:00.382024857Z [inf]  1:M 14 Jan 2026 11:25:55.154 * Background saving terminated with success
2026-01-14T13:16:39.650083057Z [inf]  1:M 14 Jan 2026 13:16:33.763 * 1 changes in 60 seconds. Saving...
2026-01-14T13:16:39.650090096Z [inf]  1:M 14 Jan 2026 13:16:33.766 * Background saving started by pid 419
2026-01-14T13:16:39.650095242Z [inf]  419:C 14 Jan 2026 13:16:33.784 * DB saved on disk
2026-01-14T13:16:39.650110104Z [inf]  419:C 14 Jan 2026 13:16:33.786 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T13:16:39.650116341Z [inf]  1:M 14 Jan 2026 13:16:33.867 * Background saving terminated with success
2026-01-14T13:17:39.689319153Z [inf]  1:M 14 Jan 2026 13:17:34.074 * 1 changes in 60 seconds. Saving...
2026-01-14T13:17:39.689325989Z [inf]  1:M 14 Jan 2026 13:17:34.078 * Background saving started by pid 420
2026-01-14T13:17:39.689330848Z [inf]  420:C 14 Jan 2026 13:17:34.103 * DB saved on disk
2026-01-14T13:17:39.689335282Z [inf]  420:C 14 Jan 2026 13:17:34.105 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T13:17:39.689339927Z [inf]  1:M 14 Jan 2026 13:17:34.178 * Background saving terminated with success
2026-01-14T13:21:30.146917713Z [inf]  1:M 14 Jan 2026 13:21:26.240 * 1 changes in 60 seconds. Saving...
2026-01-14T13:21:30.146928156Z [inf]  1:M 14 Jan 2026 13:21:26.243 * Background saving started by pid 421
2026-01-14T13:21:30.146933917Z [inf]  421:C 14 Jan 2026 13:21:26.267 * DB saved on disk
2026-01-14T13:21:30.146939684Z [inf]  421:C 14 Jan 2026 13:21:26.269 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T13:21:30.146945026Z [inf]  1:M 14 Jan 2026 13:21:26.343 * Background saving terminated with success
2026-01-14T13:22:30.278009289Z [inf]  1:M 14 Jan 2026 13:22:27.058 * 1 changes in 60 seconds. Saving...
2026-01-14T13:22:30.278024506Z [inf]  1:M 14 Jan 2026 13:22:27.062 * Background saving started by pid 422
2026-01-14T13:22:30.278031431Z [inf]  422:C 14 Jan 2026 13:22:27.077 * DB saved on disk
2026-01-14T13:22:30.278037472Z [inf]  422:C 14 Jan 2026 13:22:27.079 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T13:22:30.278043803Z [inf]  1:M 14 Jan 2026 13:22:27.163 * Background saving terminated with success
2026-01-14T13:25:20.222301324Z [inf]  1:M 14 Jan 2026 13:25:12.192 * 1 changes in 60 seconds. Saving...
2026-01-14T13:25:20.222310482Z [inf]  1:M 14 Jan 2026 13:25:12.194 * Background saving started by pid 423
2026-01-14T13:25:20.222317314Z [inf]  423:C 14 Jan 2026 13:25:12.219 * DB saved on disk
2026-01-14T13:25:20.222329760Z [inf]  423:C 14 Jan 2026 13:25:12.222 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T13:25:20.222337629Z [inf]  1:M 14 Jan 2026 13:25:12.295 * Background saving terminated with success
2026-01-14T13:26:20.227757066Z [inf]  1:M 14 Jan 2026 13:26:13.101 * 1 changes in 60 seconds. Saving...
2026-01-14T13:26:20.227763286Z [inf]  1:M 14 Jan 2026 13:26:13.104 * Background saving started by pid 424
2026-01-14T13:26:20.227768301Z [inf]  424:C 14 Jan 2026 13:26:13.147 * DB saved on disk
2026-01-14T13:26:20.227773245Z [inf]  424:C 14 Jan 2026 13:26:13.149 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T13:26:20.227778114Z [inf]  1:M 14 Jan 2026 13:26:13.205 * Background saving terminated with success
2026-01-14T13:43:22.008913123Z [inf]  1:M 14 Jan 2026 13:43:20.563 * Background saving terminated with success
2026-01-14T13:43:22.008988747Z [inf]  1:M 14 Jan 2026 13:43:20.457 * 1 changes in 60 seconds. Saving...
2026-01-14T13:43:22.008993793Z [inf]  1:M 14 Jan 2026 13:43:20.460 * Background saving started by pid 425
2026-01-14T13:43:22.008999282Z [inf]  425:C 14 Jan 2026 13:43:20.475 * DB saved on disk
2026-01-14T13:43:22.009003783Z [inf]  425:C 14 Jan 2026 13:43:20.477 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T13:44:21.940271729Z [inf]  1:M 14 Jan 2026 13:44:21.057 * 1 changes in 60 seconds. Saving...
2026-01-14T13:44:21.940276850Z [inf]  1:M 14 Jan 2026 13:44:21.059 * Background saving started by pid 426
2026-01-14T13:44:21.940282558Z [inf]  426:C 14 Jan 2026 13:44:21.423 * DB saved on disk
2026-01-14T13:44:21.940288269Z [inf]  426:C 14 Jan 2026 13:44:21.425 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 1 MB
2026-01-14T13:44:21.940296150Z [inf]  1:M 14 Jan 2026 13:44:21.462 * Background saving terminated with success
2026-01-14T14:19:44.346881403Z [inf]  1:M 14 Jan 2026 14:19:36.910 * 1 changes in 60 seconds. Saving...
2026-01-14T14:19:44.346888271Z [inf]  1:M 14 Jan 2026 14:19:36.912 * Background saving started by pid 427
2026-01-14T14:19:44.346893115Z [inf]  427:C 14 Jan 2026 14:19:36.964 * DB saved on disk
2026-01-14T14:19:44.346900959Z [inf]  427:C 14 Jan 2026 14:19:36.966 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T14:19:44.346906816Z [inf]  1:M 14 Jan 2026 14:19:37.014 * Background saving terminated with success
2026-01-14T14:20:44.438139943Z [inf]  1:M 14 Jan 2026 14:20:38.030 * 1 changes in 60 seconds. Saving...
2026-01-14T14:20:44.438148520Z [inf]  1:M 14 Jan 2026 14:20:38.032 * Background saving started by pid 428
2026-01-14T14:20:44.438156261Z [inf]  428:C 14 Jan 2026 14:20:38.057 * DB saved on disk
2026-01-14T14:20:44.438162344Z [inf]  428:C 14 Jan 2026 14:20:38.059 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T14:20:44.438168238Z [inf]  1:M 14 Jan 2026 14:20:38.133 * Background saving terminated with success
2026-01-14T14:25:14.959645460Z [inf]  1:M 14 Jan 2026 14:25:09.485 * 1 changes in 60 seconds. Saving...
2026-01-14T14:25:14.959651955Z [inf]  1:M 14 Jan 2026 14:25:09.488 * Background saving started by pid 429
2026-01-14T14:25:14.959656888Z [inf]  429:C 14 Jan 2026 14:25:09.510 * DB saved on disk
2026-01-14T14:25:14.959661926Z [inf]  429:C 14 Jan 2026 14:25:09.511 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T14:25:14.959665894Z [inf]  1:M 14 Jan 2026 14:25:09.589 * Background saving terminated with success
2026-01-14T14:26:14.972023134Z [inf]  1:M 14 Jan 2026 14:26:10.015 * 1 changes in 60 seconds. Saving...
2026-01-14T14:26:14.972031658Z [inf]  1:M 14 Jan 2026 14:26:10.019 * Background saving started by pid 430
2026-01-14T14:26:14.972037230Z [inf]  430:C 14 Jan 2026 14:26:10.051 * DB saved on disk
2026-01-14T14:26:14.972041826Z [inf]  430:C 14 Jan 2026 14:26:10.052 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T14:26:14.972047004Z [inf]  1:M 14 Jan 2026 14:26:10.120 * Background saving terminated with success
2026-01-14T15:12:07.717813581Z [inf]  1:M 14 Jan 2026 15:12:03.114 * 1 changes in 60 seconds. Saving...
2026-01-14T15:12:07.717824148Z [inf]  1:M 14 Jan 2026 15:12:03.118 * Background saving started by pid 431
2026-01-14T15:12:07.717829395Z [inf]  431:C 14 Jan 2026 15:12:03.168 * DB saved on disk
2026-01-14T15:12:07.717834348Z [inf]  431:C 14 Jan 2026 15:12:03.170 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T15:12:07.717839906Z [inf]  1:M 14 Jan 2026 15:12:03.218 * Background saving terminated with success
2026-01-14T15:13:07.652799011Z [inf]  1:M 14 Jan 2026 15:13:04.042 * 1 changes in 60 seconds. Saving...
2026-01-14T15:13:07.652805650Z [inf]  1:M 14 Jan 2026 15:13:04.045 * Background saving started by pid 432
2026-01-14T15:13:07.652812799Z [inf]  432:C 14 Jan 2026 15:13:04.066 * DB saved on disk
2026-01-14T15:13:07.652818774Z [inf]  432:C 14 Jan 2026 15:13:04.068 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T15:13:07.652824914Z [inf]  1:M 14 Jan 2026 15:13:04.146 * Background saving terminated with success
2026-01-14T15:19:57.832263531Z [inf]  1:M 14 Jan 2026 15:19:51.001 * 1 changes in 60 seconds. Saving...
2026-01-14T15:19:57.832273592Z [inf]  1:M 14 Jan 2026 15:19:51.003 * Background saving started by pid 433
2026-01-14T15:19:57.832282009Z [inf]  433:C 14 Jan 2026 15:19:51.137 * DB saved on disk
2026-01-14T15:19:57.832290772Z [inf]  433:C 14 Jan 2026 15:19:51.139 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 1 MB
2026-01-14T15:19:57.832296071Z [inf]  1:M 14 Jan 2026 15:19:51.205 * Background saving terminated with success
2026-01-14T15:20:57.839441658Z [inf]  1:M 14 Jan 2026 15:20:52.074 * 1 changes in 60 seconds. Saving...
2026-01-14T15:20:57.839450082Z [inf]  1:M 14 Jan 2026 15:20:52.078 * Background saving started by pid 434
2026-01-14T15:20:57.839456990Z [inf]  434:C 14 Jan 2026 15:20:53.152 * DB saved on disk
2026-01-14T15:20:57.839463110Z [inf]  434:C 14 Jan 2026 15:20:53.154 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 1 MB
2026-01-14T15:20:57.839468589Z [inf]  1:M 14 Jan 2026 15:20:53.185 * Background saving terminated with success
2026-01-14T15:25:07.892735656Z [inf]  1:M 14 Jan 2026 15:24:58.820 * 1 changes in 60 seconds. Saving...
2026-01-14T15:25:07.892743635Z [inf]  1:M 14 Jan 2026 15:24:58.824 * Background saving started by pid 435
2026-01-14T15:25:07.892749672Z [inf]  435:C 14 Jan 2026 15:24:59.748 * DB saved on disk
2026-01-14T15:25:07.892756709Z [inf]  435:C 14 Jan 2026 15:24:59.750 * Fork CoW for RDB: current 2 MB, peak 2 MB, average 1 MB
2026-01-14T15:25:07.892762033Z [inf]  1:M 14 Jan 2026 15:24:59.832 * Background saving terminated with success
2026-01-14T15:26:07.942968616Z [inf]  1:M 14 Jan 2026 15:26:00.047 * 1 changes in 60 seconds. Saving...
2026-01-14T15:26:07.942977282Z [inf]  1:M 14 Jan 2026 15:26:00.050 * Background saving started by pid 436
2026-01-14T15:26:07.942983302Z [inf]  436:C 14 Jan 2026 15:26:00.064 * DB saved on disk
2026-01-14T15:26:07.942987460Z [inf]  436:C 14 Jan 2026 15:26:00.066 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T15:26:07.942992332Z [inf]  1:M 14 Jan 2026 15:26:00.150 * Background saving terminated with success
2026-01-14T16:44:35.278890934Z [inf]  1:M 14 Jan 2026 16:44:25.901 * 1 changes in 60 seconds. Saving...
2026-01-14T16:44:35.278906807Z [inf]  1:M 14 Jan 2026 16:44:25.903 * Background saving started by pid 437
2026-01-14T16:44:35.278914973Z [inf]  437:C 14 Jan 2026 16:44:25.925 * DB saved on disk
2026-01-14T16:44:35.278921820Z [inf]  437:C 14 Jan 2026 16:44:25.926 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T16:44:35.278928359Z [inf]  1:M 14 Jan 2026 16:44:26.005 * Background saving terminated with success
2026-01-14T16:45:35.195040166Z [inf]  1:M 14 Jan 2026 16:45:26.020 * 1 changes in 60 seconds. Saving...
2026-01-14T16:45:35.195046170Z [inf]  1:M 14 Jan 2026 16:45:26.023 * Background saving started by pid 438
2026-01-14T16:45:35.195051135Z [inf]  438:C 14 Jan 2026 16:45:26.036 * DB saved on disk
2026-01-14T16:45:35.195055262Z [inf]  438:C 14 Jan 2026 16:45:26.038 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T16:45:35.195060935Z [inf]  1:M 14 Jan 2026 16:45:26.124 * Background saving terminated with success
2026-01-14T17:43:29.271625852Z [inf]  1:M 14 Jan 2026 17:43:23.637 * 1 changes in 60 seconds. Saving...
2026-01-14T17:43:29.271637370Z [inf]  1:M 14 Jan 2026 17:43:23.640 * Background saving started by pid 439
2026-01-14T17:43:29.271645149Z [inf]  439:C 14 Jan 2026 17:43:23.655 * DB saved on disk
2026-01-14T17:43:29.271654683Z [inf]  439:C 14 Jan 2026 17:43:23.656 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T17:43:29.271663651Z [inf]  1:M 14 Jan 2026 17:43:23.741 * Background saving terminated with success
2026-01-14T17:44:29.277186839Z [inf]  1:M 14 Jan 2026 17:44:24.042 * 1 changes in 60 seconds. Saving...
2026-01-14T17:44:29.277194281Z [inf]  1:M 14 Jan 2026 17:44:24.045 * Background saving started by pid 440
2026-01-14T17:44:29.277200233Z [inf]  440:C 14 Jan 2026 17:44:24.059 * DB saved on disk
2026-01-14T17:44:29.277206464Z [inf]  440:C 14 Jan 2026 17:44:24.060 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T17:44:29.277212196Z [inf]  1:M 14 Jan 2026 17:44:24.147 * Background saving terminated with success
2026-01-14T18:47:34.364788618Z [inf]  1:M 14 Jan 2026 18:47:30.277 * 1 changes in 60 seconds. Saving...
2026-01-14T18:47:34.364797268Z [inf]  1:M 14 Jan 2026 18:47:30.280 * Background saving started by pid 441
2026-01-14T18:47:34.364805359Z [inf]  441:C 14 Jan 2026 18:47:30.296 * DB saved on disk
2026-01-14T18:47:34.364811915Z [inf]  441:C 14 Jan 2026 18:47:30.298 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T18:47:34.364818774Z [inf]  1:M 14 Jan 2026 18:47:30.381 * Background saving terminated with success
2026-01-14T18:48:34.375810566Z [inf]  1:M 14 Jan 2026 18:48:31.069 * 1 changes in 60 seconds. Saving...
2026-01-14T18:48:34.375818956Z [inf]  1:M 14 Jan 2026 18:48:31.072 * Background saving started by pid 442
2026-01-14T18:48:34.375824670Z [inf]  442:C 14 Jan 2026 18:48:31.153 * DB saved on disk
2026-01-14T18:48:34.375829466Z [inf]  442:C 14 Jan 2026 18:48:31.155 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T18:48:34.375834623Z [inf]  1:M 14 Jan 2026 18:48:31.173 * Background saving terminated with success
2026-01-14T19:09:46.117220497Z [inf]  1:M 14 Jan 2026 19:09:40.044 * 1 changes in 60 seconds. Saving...
2026-01-14T19:09:46.117229468Z [inf]  1:M 14 Jan 2026 19:09:40.047 * Background saving started by pid 443
2026-01-14T19:09:46.117237806Z [inf]  443:C 14 Jan 2026 19:09:40.060 * DB saved on disk
2026-01-14T19:09:46.117243892Z [inf]  443:C 14 Jan 2026 19:09:40.061 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T19:09:46.117250642Z [inf]  1:M 14 Jan 2026 19:09:40.147 * Background saving terminated with success
2026-01-14T19:10:46.106319872Z [inf]  1:M 14 Jan 2026 19:10:41.039 * 1 changes in 60 seconds. Saving...
2026-01-14T19:10:46.106327334Z [inf]  1:M 14 Jan 2026 19:10:41.042 * Background saving started by pid 444
2026-01-14T19:10:46.106331968Z [inf]  444:C 14 Jan 2026 19:10:41.101 * DB saved on disk
2026-01-14T19:10:46.106336621Z [inf]  444:C 14 Jan 2026 19:10:41.103 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T19:10:46.106341533Z [inf]  1:M 14 Jan 2026 19:10:41.143 * Background saving terminated with success
2026-01-14T19:19:16.454551815Z [inf]  1:M 14 Jan 2026 19:19:12.118 * 1 changes in 60 seconds. Saving...
2026-01-14T19:19:16.454569409Z [inf]  1:M 14 Jan 2026 19:19:12.121 * Background saving started by pid 445
2026-01-14T19:19:16.454577807Z [inf]  445:C 14 Jan 2026 19:19:12.136 * DB saved on disk
2026-01-14T19:19:16.454585551Z [inf]  445:C 14 Jan 2026 19:19:12.138 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T19:19:16.454592918Z [inf]  1:M 14 Jan 2026 19:19:12.222 * Background saving terminated with success
2026-01-14T19:20:16.370893084Z [inf]  1:M 14 Jan 2026 19:20:13.050 * 1 changes in 60 seconds. Saving...
2026-01-14T19:20:16.370902190Z [inf]  1:M 14 Jan 2026 19:20:13.055 * Background saving started by pid 446
2026-01-14T19:20:16.370909831Z [inf]  446:C 14 Jan 2026 19:20:13.087 * DB saved on disk
2026-01-14T19:20:16.370915898Z [inf]  446:C 14 Jan 2026 19:20:13.089 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T19:20:16.370921813Z [inf]  1:M 14 Jan 2026 19:20:13.156 * Background saving terminated with success
2026-01-14T20:00:29.989715759Z [inf]  1:M 14 Jan 2026 20:00:29.162 * 1 changes in 60 seconds. Saving...
2026-01-14T20:00:29.989727107Z [inf]  1:M 14 Jan 2026 20:00:29.166 * Background saving started by pid 447
2026-01-14T20:00:29.989738889Z [inf]  447:C 14 Jan 2026 20:00:29.185 * DB saved on disk
2026-01-14T20:00:29.989747821Z [inf]  447:C 14 Jan 2026 20:00:29.187 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T20:00:29.989759581Z [inf]  1:M 14 Jan 2026 20:00:29.267 * Background saving terminated with success
2026-01-14T20:01:39.860596997Z [inf]  1:M 14 Jan 2026 20:01:30.032 * 1 changes in 60 seconds. Saving...
2026-01-14T20:01:39.860605709Z [inf]  1:M 14 Jan 2026 20:01:30.035 * Background saving started by pid 448
2026-01-14T20:01:39.860612375Z [inf]  448:C 14 Jan 2026 20:01:30.048 * DB saved on disk
2026-01-14T20:01:39.860618856Z [inf]  448:C 14 Jan 2026 20:01:30.050 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T20:01:39.860626654Z [inf]  1:M 14 Jan 2026 20:01:30.137 * Background saving terminated with success
2026-01-14T20:02:39.868553773Z [inf]  1:M 14 Jan 2026 20:02:31.052 * 1 changes in 60 seconds. Saving...
2026-01-14T20:02:39.868562932Z [inf]  1:M 14 Jan 2026 20:02:31.055 * Background saving started by pid 449
2026-01-14T20:02:39.868570161Z [inf]  449:C 14 Jan 2026 20:02:31.091 * DB saved on disk
2026-01-14T20:02:39.868576162Z [inf]  449:C 14 Jan 2026 20:02:31.092 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-14T20:02:39.868583227Z [inf]  1:M 14 Jan 2026 20:02:31.156 * Background saving terminated with success
2026-01-15T04:09:47.675031127Z [inf]  1:M 15 Jan 2026 04:09:40.232 * 1 changes in 60 seconds. Saving...
2026-01-15T04:09:47.675043689Z [inf]  1:M 15 Jan 2026 04:09:40.235 * Background saving started by pid 450
2026-01-15T04:09:47.675050387Z [inf]  450:C 15 Jan 2026 04:09:40.255 * DB saved on disk
2026-01-15T04:09:47.675056203Z [inf]  450:C 15 Jan 2026 04:09:40.256 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T04:09:47.675061620Z [inf]  1:M 15 Jan 2026 04:09:40.336 * Background saving terminated with success
2026-01-15T04:10:47.804407530Z [inf]  1:M 15 Jan 2026 04:10:41.061 * 1 changes in 60 seconds. Saving...
2026-01-15T04:10:47.804415452Z [inf]  1:M 15 Jan 2026 04:10:41.064 * Background saving started by pid 451
2026-01-15T04:10:47.804423383Z [inf]  451:C 15 Jan 2026 04:10:41.096 * DB saved on disk
2026-01-15T04:10:47.804430441Z [inf]  451:C 15 Jan 2026 04:10:41.098 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T04:10:47.804437976Z [inf]  1:M 15 Jan 2026 04:10:41.164 * Background saving terminated with success
2026-01-15T05:46:44.763629857Z [inf]  1:M 15 Jan 2026 05:46:36.908 * 1 changes in 60 seconds. Saving...
2026-01-15T05:46:44.763641292Z [inf]  1:M 15 Jan 2026 05:46:36.911 * Background saving started by pid 452
2026-01-15T05:46:44.763647647Z [inf]  452:C 15 Jan 2026 05:46:36.933 * DB saved on disk
2026-01-15T05:46:44.763653332Z [inf]  452:C 15 Jan 2026 05:46:36.935 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T05:46:44.763658867Z [inf]  1:M 15 Jan 2026 05:46:37.012 * Background saving terminated with success
2026-01-15T05:47:44.764759134Z [inf]  1:M 15 Jan 2026 05:47:38.100 * 1 changes in 60 seconds. Saving...
2026-01-15T05:47:44.764767241Z [inf]  1:M 15 Jan 2026 05:47:38.102 * Background saving started by pid 453
2026-01-15T05:47:44.764773319Z [inf]  453:C 15 Jan 2026 05:47:38.117 * DB saved on disk
2026-01-15T05:47:44.764779214Z [inf]  453:C 15 Jan 2026 05:47:38.118 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T05:47:44.764784666Z [inf]  1:M 15 Jan 2026 05:47:38.203 * Background saving terminated with success
2026-01-15T06:23:26.758150279Z [inf]  1:M 15 Jan 2026 06:23:17.535 * 1 changes in 60 seconds. Saving...
2026-01-15T06:23:26.758158907Z [inf]  1:M 15 Jan 2026 06:23:17.538 * Background saving started by pid 454
2026-01-15T06:23:26.758165467Z [inf]  454:C 15 Jan 2026 06:23:17.551 * DB saved on disk
2026-01-15T06:23:26.758169804Z [inf]  454:C 15 Jan 2026 06:23:17.553 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T06:23:26.758173920Z [inf]  1:M 15 Jan 2026 06:23:17.639 * Background saving terminated with success
2026-01-15T06:24:26.860731417Z [inf]  1:M 15 Jan 2026 06:24:18.046 * 1 changes in 60 seconds. Saving...
2026-01-15T06:24:26.860739071Z [inf]  1:M 15 Jan 2026 06:24:18.049 * Background saving started by pid 455
2026-01-15T06:24:26.860743862Z [inf]  455:C 15 Jan 2026 06:24:18.071 * DB saved on disk
2026-01-15T06:24:26.860748031Z [inf]  455:C 15 Jan 2026 06:24:18.073 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T06:24:26.860751891Z [inf]  1:M 15 Jan 2026 06:24:18.150 * Background saving terminated with success
2026-01-15T06:50:38.583326146Z [inf]  1:M 15 Jan 2026 06:50:38.132 * 1 changes in 60 seconds. Saving...
2026-01-15T06:50:38.583333858Z [inf]  1:M 15 Jan 2026 06:50:38.135 * Background saving started by pid 456
2026-01-15T06:50:38.583344744Z [inf]  456:C 15 Jan 2026 06:50:38.156 * DB saved on disk
2026-01-15T06:50:38.583353152Z [inf]  456:C 15 Jan 2026 06:50:38.157 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T06:50:38.583362608Z [inf]  1:M 15 Jan 2026 06:50:38.236 * Background saving terminated with success
2026-01-15T06:51:48.508425269Z [inf]  1:M 15 Jan 2026 06:51:39.029 * 1 changes in 60 seconds. Saving...
2026-01-15T06:51:48.508435772Z [inf]  1:M 15 Jan 2026 06:51:39.032 * Background saving started by pid 457
2026-01-15T06:51:48.508441760Z [inf]  457:C 15 Jan 2026 06:51:39.047 * DB saved on disk
2026-01-15T06:51:48.508447347Z [inf]  457:C 15 Jan 2026 06:51:39.049 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T06:51:48.508452718Z [inf]  1:M 15 Jan 2026 06:51:39.132 * Background saving terminated with success
2026-01-15T07:05:09.456415686Z [inf]  1:M 15 Jan 2026 07:05:02.129 * 1 changes in 60 seconds. Saving...
2026-01-15T07:05:09.456426364Z [inf]  1:M 15 Jan 2026 07:05:02.132 * Background saving started by pid 458
2026-01-15T07:05:09.456434832Z [inf]  458:C 15 Jan 2026 07:05:02.764 * DB saved on disk
2026-01-15T07:05:09.456441506Z [inf]  458:C 15 Jan 2026 07:05:02.765 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 1 MB
2026-01-15T07:05:09.456448121Z [inf]  1:M 15 Jan 2026 07:05:02.836 * Background saving terminated with success
2026-01-15T07:06:09.350674401Z [inf]  1:M 15 Jan 2026 07:06:03.022 * 1 changes in 60 seconds. Saving...
2026-01-15T07:06:09.350680773Z [inf]  1:M 15 Jan 2026 07:06:03.025 * Background saving started by pid 459
2026-01-15T07:06:09.350687015Z [inf]  459:C 15 Jan 2026 07:06:03.037 * DB saved on disk
2026-01-15T07:06:09.350693035Z [inf]  459:C 15 Jan 2026 07:06:03.038 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:06:09.350700081Z [inf]  1:M 15 Jan 2026 07:06:03.126 * Background saving terminated with success
2026-01-15T07:16:00.043163940Z [inf]  1:M 15 Jan 2026 07:15:52.494 * 1 changes in 60 seconds. Saving...
2026-01-15T07:16:00.043176607Z [inf]  1:M 15 Jan 2026 07:15:52.496 * Background saving started by pid 460
2026-01-15T07:16:00.043184777Z [inf]  460:C 15 Jan 2026 07:15:52.570 * DB saved on disk
2026-01-15T07:16:00.043191231Z [inf]  460:C 15 Jan 2026 07:15:52.571 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:16:00.043197893Z [inf]  1:M 15 Jan 2026 07:15:52.597 * Background saving terminated with success
2026-01-15T07:16:59.952770662Z [inf]  1:M 15 Jan 2026 07:16:53.093 * 1 changes in 60 seconds. Saving...
2026-01-15T07:16:59.952777781Z [inf]  1:M 15 Jan 2026 07:16:53.096 * Background saving started by pid 461
2026-01-15T07:16:59.952782315Z [inf]  461:C 15 Jan 2026 07:16:53.112 * DB saved on disk
2026-01-15T07:16:59.952786439Z [inf]  461:C 15 Jan 2026 07:16:53.113 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:16:59.952791077Z [inf]  1:M 15 Jan 2026 07:16:53.196 * Background saving terminated with success
2026-01-15T07:19:19.969365555Z [inf]  1:M 15 Jan 2026 07:19:10.813 * 1 changes in 60 seconds. Saving...
2026-01-15T07:19:19.969371522Z [inf]  1:M 15 Jan 2026 07:19:10.815 * Background saving started by pid 462
2026-01-15T07:19:19.969375726Z [inf]  462:C 15 Jan 2026 07:19:10.837 * DB saved on disk
2026-01-15T07:19:19.969379435Z [inf]  462:C 15 Jan 2026 07:19:10.839 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:19:19.969383070Z [inf]  1:M 15 Jan 2026 07:19:10.916 * Background saving terminated with success
2026-01-15T07:20:19.975844930Z [inf]  1:M 15 Jan 2026 07:20:11.028 * 1 changes in 60 seconds. Saving...
2026-01-15T07:20:19.975853577Z [inf]  1:M 15 Jan 2026 07:20:11.031 * Background saving started by pid 463
2026-01-15T07:20:19.975858431Z [inf]  463:C 15 Jan 2026 07:20:11.046 * DB saved on disk
2026-01-15T07:20:19.975862879Z [inf]  463:C 15 Jan 2026 07:20:11.049 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:20:19.975866977Z [inf]  1:M 15 Jan 2026 07:20:11.131 * Background saving terminated with success
2026-01-15T07:26:30.288712239Z [inf]  1:M 15 Jan 2026 07:26:25.954 * 1 changes in 60 seconds. Saving...
2026-01-15T07:26:30.288719953Z [inf]  1:M 15 Jan 2026 07:26:25.956 * Background saving started by pid 464
2026-01-15T07:26:30.288725902Z [inf]  464:C 15 Jan 2026 07:26:25.980 * DB saved on disk
2026-01-15T07:26:30.288730540Z [inf]  464:C 15 Jan 2026 07:26:25.981 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:26:30.288735043Z [inf]  1:M 15 Jan 2026 07:26:26.057 * Background saving terminated with success
2026-01-15T07:27:30.290170989Z [inf]  1:M 15 Jan 2026 07:27:27.072 * 1 changes in 60 seconds. Saving...
2026-01-15T07:27:30.290181425Z [inf]  1:M 15 Jan 2026 07:27:27.075 * Background saving started by pid 465
2026-01-15T07:27:30.290189344Z [inf]  465:C 15 Jan 2026 07:27:27.089 * DB saved on disk
2026-01-15T07:27:30.290195147Z [inf]  465:C 15 Jan 2026 07:27:27.091 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:27:30.290199938Z [inf]  1:M 15 Jan 2026 07:27:27.175 * Background saving terminated with success
2026-01-15T07:29:10.303702444Z [inf]  1:M 15 Jan 2026 07:29:07.796 * 1 changes in 60 seconds. Saving...
2026-01-15T07:29:10.303709531Z [inf]  1:M 15 Jan 2026 07:29:07.798 * Background saving started by pid 466
2026-01-15T07:29:10.303713873Z [inf]  466:C 15 Jan 2026 07:29:07.827 * DB saved on disk
2026-01-15T07:29:10.303717982Z [inf]  466:C 15 Jan 2026 07:29:07.829 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:29:10.303721830Z [inf]  1:M 15 Jan 2026 07:29:07.899 * Background saving terminated with success
2026-01-15T07:30:10.304917731Z [inf]  1:M 15 Jan 2026 07:30:08.095 * 1 changes in 60 seconds. Saving...
2026-01-15T07:30:10.304924203Z [inf]  1:M 15 Jan 2026 07:30:08.098 * Background saving started by pid 467
2026-01-15T07:30:10.304929057Z [inf]  467:C 15 Jan 2026 07:30:08.113 * DB saved on disk
2026-01-15T07:30:10.304933283Z [inf]  467:C 15 Jan 2026 07:30:08.114 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:30:10.304937830Z [inf]  1:M 15 Jan 2026 07:30:08.198 * Background saving terminated with success
2026-01-15T07:42:00.746517866Z [inf]  1:M 15 Jan 2026 07:41:51.764 * 1 changes in 60 seconds. Saving...
2026-01-15T07:42:00.746525449Z [inf]  1:M 15 Jan 2026 07:41:51.767 * Background saving started by pid 468
2026-01-15T07:42:00.746531341Z [inf]  468:C 15 Jan 2026 07:41:51.779 * DB saved on disk
2026-01-15T07:42:00.746536251Z [inf]  468:C 15 Jan 2026 07:41:51.781 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:42:00.746540775Z [inf]  1:M 15 Jan 2026 07:41:51.868 * Background saving terminated with success
2026-01-15T07:43:00.752142715Z [inf]  1:M 15 Jan 2026 07:42:52.055 * 1 changes in 60 seconds. Saving...
2026-01-15T07:43:00.752154638Z [inf]  1:M 15 Jan 2026 07:42:52.058 * Background saving started by pid 469
2026-01-15T07:43:00.752162680Z [inf]  469:C 15 Jan 2026 07:42:52.076 * DB saved on disk
2026-01-15T07:43:00.752170004Z [inf]  469:C 15 Jan 2026 07:42:52.078 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:43:00.752176516Z [inf]  1:M 15 Jan 2026 07:42:52.159 * Background saving terminated with success
2026-01-15T07:47:40.790765472Z [inf]  1:M 15 Jan 2026 07:47:31.882 * 1 changes in 60 seconds. Saving...
2026-01-15T07:47:40.790775966Z [inf]  1:M 15 Jan 2026 07:47:31.886 * Background saving started by pid 470
2026-01-15T07:47:40.790783167Z [inf]  470:C 15 Jan 2026 07:47:31.897 * DB saved on disk
2026-01-15T07:47:40.790789745Z [inf]  470:C 15 Jan 2026 07:47:31.899 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:47:40.790796522Z [inf]  1:M 15 Jan 2026 07:47:31.986 * Background saving terminated with success
2026-01-15T07:48:40.795843610Z [inf]  1:M 15 Jan 2026 07:48:32.082 * 1 changes in 60 seconds. Saving...
2026-01-15T07:48:40.795850830Z [inf]  1:M 15 Jan 2026 07:48:32.086 * Background saving started by pid 471
2026-01-15T07:48:40.795856768Z [inf]  471:C 15 Jan 2026 07:48:32.215 * DB saved on disk
2026-01-15T07:48:40.795862727Z [inf]  471:C 15 Jan 2026 07:48:32.217 * Fork CoW for RDB: current 3 MB, peak 3 MB, average 2 MB
2026-01-15T07:48:40.795868911Z [inf]  1:M 15 Jan 2026 07:48:32.288 * Background saving terminated with success
2026-01-15T07:49:40.812537683Z [inf]  1:M 15 Jan 2026 07:49:33.095 * 1 changes in 60 seconds. Saving...
2026-01-15T07:49:40.812549398Z [inf]  1:M 15 Jan 2026 07:49:33.098 * Background saving started by pid 472
2026-01-15T07:49:40.812557254Z [inf]  472:C 15 Jan 2026 07:49:33.208 * DB saved on disk
2026-01-15T07:49:40.812575138Z [inf]  472:C 15 Jan 2026 07:49:33.210 * Fork CoW for RDB: current 4 MB, peak 4 MB, average 2 MB
2026-01-15T07:49:40.812581170Z [inf]  1:M 15 Jan 2026 07:49:33.301 * Background saving terminated with success
2026-01-15T07:50:40.823748206Z [inf]  1:M 15 Jan 2026 07:50:34.014 * 1 changes in 60 seconds. Saving...
2026-01-15T07:50:40.823757956Z [inf]  1:M 15 Jan 2026 07:50:34.017 * Background saving started by pid 473
2026-01-15T07:50:40.823763687Z [inf]  473:C 15 Jan 2026 07:50:34.028 * DB saved on disk
2026-01-15T07:50:40.823769371Z [inf]  473:C 15 Jan 2026 07:50:34.030 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T07:50:40.823774931Z [inf]  1:M 15 Jan 2026 07:50:34.117 * Background saving terminated with success
2026-01-15T08:07:01.475375585Z [inf]  1:M 15 Jan 2026 08:06:59.758 * 1 changes in 60 seconds. Saving...
2026-01-15T08:07:01.475382542Z [inf]  1:M 15 Jan 2026 08:06:59.761 * Background saving started by pid 474
2026-01-15T08:07:01.475388058Z [inf]  474:C 15 Jan 2026 08:06:59.772 * DB saved on disk
2026-01-15T08:07:01.475393099Z [inf]  474:C 15 Jan 2026 08:06:59.774 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T08:07:01.475397904Z [inf]  1:M 15 Jan 2026 08:06:59.862 * Background saving terminated with success
2026-01-15T08:08:01.480873763Z [inf]  1:M 15 Jan 2026 08:08:00.053 * 1 changes in 60 seconds. Saving...
2026-01-15T08:08:01.480882955Z [inf]  1:M 15 Jan 2026 08:08:00.056 * Background saving started by pid 475
2026-01-15T08:08:01.480889413Z [inf]  475:C 15 Jan 2026 08:08:00.077 * DB saved on disk
2026-01-15T08:08:01.480899688Z [inf]  475:C 15 Jan 2026 08:08:00.079 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T08:08:01.480911953Z [inf]  1:M 15 Jan 2026 08:08:00.157 * Background saving terminated with success
2026-01-15T08:33:54.293120821Z [inf]  1:M 15 Jan 2026 08:33:52.137 * 1 changes in 60 seconds. Saving...
2026-01-15T08:33:54.293130544Z [inf]  1:M 15 Jan 2026 08:33:52.140 * Background saving started by pid 476
2026-01-15T08:33:54.293136157Z [inf]  476:C 15 Jan 2026 08:33:52.172 * DB saved on disk
2026-01-15T08:33:54.293140466Z [inf]  476:C 15 Jan 2026 08:33:52.174 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T08:33:54.293145965Z [inf]  1:M 15 Jan 2026 08:33:52.240 * Background saving terminated with success
2026-01-15T08:34:54.407553846Z [inf]  1:M 15 Jan 2026 08:34:53.053 * 1 changes in 60 seconds. Saving...
2026-01-15T08:34:54.407563967Z [inf]  1:M 15 Jan 2026 08:34:53.056 * Background saving started by pid 477
2026-01-15T08:34:54.407575194Z [inf]  477:C 15 Jan 2026 08:34:53.072 * DB saved on disk
2026-01-15T08:34:54.407581832Z [inf]  477:C 15 Jan 2026 08:34:53.074 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T08:34:54.407588023Z [inf]  1:M 15 Jan 2026 08:34:53.157 * Background saving terminated with success
2026-01-15T08:38:44.357502244Z [inf]  1:M 15 Jan 2026 08:38:38.307 * 1 changes in 60 seconds. Saving...
2026-01-15T08:38:44.357512043Z [inf]  1:M 15 Jan 2026 08:38:38.309 * Background saving started by pid 478
2026-01-15T08:38:44.357518295Z [inf]  478:C 15 Jan 2026 08:38:38.325 * DB saved on disk
2026-01-15T08:38:44.357523911Z [inf]  478:C 15 Jan 2026 08:38:38.327 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T08:38:44.357529314Z [inf]  1:M 15 Jan 2026 08:38:38.410 * Background saving terminated with success
2026-01-15T08:39:44.365095849Z [inf]  1:M 15 Jan 2026 08:39:39.000 * 1 changes in 60 seconds. Saving...
2026-01-15T08:39:44.365105372Z [inf]  1:M 15 Jan 2026 08:39:39.003 * Background saving started by pid 479
2026-01-15T08:39:44.365111637Z [inf]  479:C 15 Jan 2026 08:39:39.029 * DB saved on disk
2026-01-15T08:39:44.365117018Z [inf]  479:C 15 Jan 2026 08:39:39.031 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T08:39:44.365150929Z [inf]  1:M 15 Jan 2026 08:39:39.104 * Background saving terminated with success
2026-01-15T08:46:34.495629595Z [inf]  1:M 15 Jan 2026 08:46:32.034 * 1 changes in 60 seconds. Saving...
2026-01-15T08:46:34.495638917Z [inf]  1:M 15 Jan 2026 08:46:32.036 * Background saving started by pid 480
2026-01-15T08:46:34.495648595Z [inf]  480:C 15 Jan 2026 08:46:32.060 * DB saved on disk
2026-01-15T08:46:34.495654184Z [inf]  480:C 15 Jan 2026 08:46:32.062 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T08:46:34.495659755Z [inf]  1:M 15 Jan 2026 08:46:32.137 * Background saving terminated with success
2026-01-15T08:47:34.424633704Z [inf]  1:M 15 Jan 2026 08:47:33.026 * 1 changes in 60 seconds. Saving...
2026-01-15T08:47:34.424643884Z [inf]  1:M 15 Jan 2026 08:47:33.028 * Background saving started by pid 481
2026-01-15T08:47:34.424650123Z [inf]  481:C 15 Jan 2026 08:47:33.041 * DB saved on disk
2026-01-15T08:47:34.424655482Z [inf]  481:C 15 Jan 2026 08:47:33.043 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T08:47:34.424660162Z [inf]  1:M 15 Jan 2026 08:47:33.130 * Background saving terminated with success
2026-01-15T09:01:25.555424411Z [inf]  1:M 15 Jan 2026 09:01:21.152 * 1 changes in 60 seconds. Saving...
2026-01-15T09:01:25.555434741Z [inf]  1:M 15 Jan 2026 09:01:21.155 * Background saving started by pid 482
2026-01-15T09:01:25.555440104Z [inf]  482:C 15 Jan 2026 09:01:21.192 * DB saved on disk
2026-01-15T09:01:25.555444737Z [inf]  482:C 15 Jan 2026 09:01:21.194 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:01:25.555449687Z [inf]  1:M 15 Jan 2026 09:01:21.256 * Background saving terminated with success
2026-01-15T09:02:25.563022326Z [inf]  1:M 15 Jan 2026 09:02:22.070 * 1 changes in 60 seconds. Saving...
2026-01-15T09:02:25.563027738Z [inf]  1:M 15 Jan 2026 09:02:22.072 * Background saving started by pid 483
2026-01-15T09:02:25.563032229Z [inf]  483:C 15 Jan 2026 09:02:22.090 * DB saved on disk
2026-01-15T09:02:25.563094179Z [inf]  483:C 15 Jan 2026 09:02:22.092 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:02:25.563102349Z [inf]  1:M 15 Jan 2026 09:02:22.173 * Background saving terminated with success
2026-01-15T09:16:46.788982352Z [inf]  1:M 15 Jan 2026 09:16:38.168 * 1 changes in 60 seconds. Saving...
2026-01-15T09:16:46.788988208Z [inf]  1:M 15 Jan 2026 09:16:38.170 * Background saving started by pid 484
2026-01-15T09:16:46.788993285Z [inf]  484:C 15 Jan 2026 09:16:38.217 * DB saved on disk
2026-01-15T09:16:46.788997772Z [inf]  484:C 15 Jan 2026 09:16:38.218 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:16:46.789001651Z [inf]  1:M 15 Jan 2026 09:16:38.271 * Background saving terminated with success
2026-01-15T09:17:46.823980800Z [inf]  1:M 15 Jan 2026 09:17:39.087 * 1 changes in 60 seconds. Saving...
2026-01-15T09:17:46.823989625Z [inf]  1:M 15 Jan 2026 09:17:39.090 * Background saving started by pid 485
2026-01-15T09:17:46.823995126Z [inf]  485:C 15 Jan 2026 09:17:39.105 * DB saved on disk
2026-01-15T09:17:46.824000302Z [inf]  485:C 15 Jan 2026 09:17:39.107 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:17:46.824010334Z [inf]  1:M 15 Jan 2026 09:17:39.191 * Background saving terminated with success
2026-01-15T09:21:27.205351153Z [inf]  1:M 15 Jan 2026 09:21:26.145 * 1 changes in 60 seconds. Saving...
2026-01-15T09:21:27.205357600Z [inf]  1:M 15 Jan 2026 09:21:26.148 * Background saving started by pid 486
2026-01-15T09:21:27.205363910Z [inf]  486:C 15 Jan 2026 09:21:26.187 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:21:27.205365055Z [inf]  486:C 15 Jan 2026 09:21:26.185 * DB saved on disk
2026-01-15T09:21:27.205371994Z [inf]  1:M 15 Jan 2026 09:21:26.249 * Background saving terminated with success
2026-01-15T09:22:27.143066836Z [inf]  1:M 15 Jan 2026 09:22:27.064 * 1 changes in 60 seconds. Saving...
2026-01-15T09:22:27.143075795Z [inf]  1:M 15 Jan 2026 09:22:27.067 * Background saving started by pid 487
2026-01-15T09:22:27.143083028Z [inf]  487:C 15 Jan 2026 09:22:27.082 * DB saved on disk
2026-01-15T09:22:27.143089981Z [inf]  487:C 15 Jan 2026 09:22:27.083 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:22:27.172064114Z [inf]  1:M 15 Jan 2026 09:22:27.168 * Background saving terminated with success
2026-01-15T09:49:38.216258871Z [inf]  1:M 15 Jan 2026 09:49:33.469 * 1 changes in 60 seconds. Saving...
2026-01-15T09:49:38.216265849Z [inf]  1:M 15 Jan 2026 09:49:33.472 * Background saving started by pid 488
2026-01-15T09:49:38.216270779Z [inf]  488:C 15 Jan 2026 09:49:33.492 * DB saved on disk
2026-01-15T09:49:38.216274701Z [inf]  488:C 15 Jan 2026 09:49:33.493 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:49:38.216278545Z [inf]  1:M 15 Jan 2026 09:49:33.573 * Background saving terminated with success
2026-01-15T09:50:38.300082954Z [inf]  1:M 15 Jan 2026 09:50:34.083 * 1 changes in 60 seconds. Saving...
2026-01-15T09:50:38.300089340Z [inf]  1:M 15 Jan 2026 09:50:34.086 * Background saving started by pid 489
2026-01-15T09:50:38.300096223Z [inf]  489:C 15 Jan 2026 09:50:34.102 * DB saved on disk
2026-01-15T09:50:38.300101886Z [inf]  489:C 15 Jan 2026 09:50:34.103 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:50:38.300109270Z [inf]  1:M 15 Jan 2026 09:50:34.186 * Background saving terminated with success
2026-01-15T09:58:58.602951931Z [inf]  1:M 15 Jan 2026 09:58:52.130 * 1 changes in 60 seconds. Saving...
2026-01-15T09:58:58.602959639Z [inf]  1:M 15 Jan 2026 09:58:52.134 * Background saving started by pid 490
2026-01-15T09:58:58.602964907Z [inf]  490:C 15 Jan 2026 09:58:52.163 * DB saved on disk
2026-01-15T09:58:58.602970175Z [inf]  490:C 15 Jan 2026 09:58:52.166 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:58:58.602974934Z [inf]  1:M 15 Jan 2026 09:58:52.235 * Background saving terminated with success
2026-01-15T09:59:58.523488002Z [inf]  1:M 15 Jan 2026 09:59:53.026 * 1 changes in 60 seconds. Saving...
2026-01-15T09:59:58.523501709Z [inf]  1:M 15 Jan 2026 09:59:53.029 * Background saving started by pid 491
2026-01-15T09:59:58.523509556Z [inf]  491:C 15 Jan 2026 09:59:53.072 * DB saved on disk
2026-01-15T09:59:58.523516192Z [inf]  491:C 15 Jan 2026 09:59:53.073 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T09:59:58.523522795Z [inf]  1:M 15 Jan 2026 09:59:53.130 * Background saving terminated with success
2026-01-15T10:09:38.707570427Z [inf]  1:M 15 Jan 2026 10:09:35.878 * 1 changes in 60 seconds. Saving...
2026-01-15T10:09:38.707580833Z [inf]  1:M 15 Jan 2026 10:09:35.881 * Background saving started by pid 492
2026-01-15T10:09:38.707587183Z [inf]  492:C 15 Jan 2026 10:09:35.892 * DB saved on disk
2026-01-15T10:09:38.707592989Z [inf]  492:C 15 Jan 2026 10:09:35.894 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T10:09:38.707598590Z [inf]  1:M 15 Jan 2026 10:09:35.981 * Background saving terminated with success
2026-01-15T10:10:38.711324345Z [inf]  1:M 15 Jan 2026 10:10:36.061 * 1 changes in 60 seconds. Saving...
2026-01-15T10:10:38.711331607Z [inf]  1:M 15 Jan 2026 10:10:36.063 * Background saving started by pid 493
2026-01-15T10:10:38.711336301Z [inf]  493:C 15 Jan 2026 10:10:36.076 * DB saved on disk
2026-01-15T10:10:38.711340631Z [inf]  493:C 15 Jan 2026 10:10:36.078 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T10:10:38.711344305Z [inf]  1:M 15 Jan 2026 10:10:36.164 * Background saving terminated with success
2026-01-15T18:25:31.312817601Z [inf]  1:M 15 Jan 2026 18:25:29.277 * 1 changes in 60 seconds. Saving...
2026-01-15T18:25:31.312826429Z [inf]  1:M 15 Jan 2026 18:25:29.280 * Background saving started by pid 494
2026-01-15T18:25:31.312832843Z [inf]  494:C 15 Jan 2026 18:25:29.295 * DB saved on disk
2026-01-15T18:25:31.312838005Z [inf]  494:C 15 Jan 2026 18:25:29.297 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T18:25:31.312847403Z [inf]  1:M 15 Jan 2026 18:25:29.382 * Background saving terminated with success
2026-01-15T18:26:31.321879371Z [inf]  1:M 15 Jan 2026 18:26:30.089 * 1 changes in 60 seconds. Saving...
2026-01-15T18:26:31.321888203Z [inf]  1:M 15 Jan 2026 18:26:30.092 * Background saving started by pid 495
2026-01-15T18:26:31.321893669Z [inf]  495:C 15 Jan 2026 18:26:30.113 * DB saved on disk
2026-01-15T18:26:31.321898268Z [inf]  495:C 15 Jan 2026 18:26:30.115 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T18:26:31.321903992Z [inf]  1:M 15 Jan 2026 18:26:30.193 * Background saving terminated with success
2026-01-15T19:29:36.702880427Z [inf]  1:M 15 Jan 2026 19:29:27.564 * 1 changes in 60 seconds. Saving...
2026-01-15T19:29:36.702895529Z [inf]  1:M 15 Jan 2026 19:29:27.567 * Background saving started by pid 496
2026-01-15T19:29:36.702906018Z [inf]  496:C 15 Jan 2026 19:29:27.583 * DB saved on disk
2026-01-15T19:29:36.702915436Z [inf]  496:C 15 Jan 2026 19:29:27.585 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T19:29:36.702922910Z [inf]  1:M 15 Jan 2026 19:29:27.668 * Background saving terminated with success
2026-01-15T19:30:36.645108090Z [inf]  1:M 15 Jan 2026 19:30:28.010 * 1 changes in 60 seconds. Saving...
2026-01-15T19:30:36.645115369Z [inf]  1:M 15 Jan 2026 19:30:28.013 * Background saving started by pid 497
2026-01-15T19:30:36.645120353Z [inf]  497:C 15 Jan 2026 19:30:28.044 * DB saved on disk
2026-01-15T19:30:36.645124756Z [inf]  497:C 15 Jan 2026 19:30:28.046 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T19:30:36.645129314Z [inf]  1:M 15 Jan 2026 19:30:28.114 * Background saving terminated with success
2026-01-15T20:27:49.895858814Z [inf]  1:M 15 Jan 2026 20:27:42.217 * 1 changes in 60 seconds. Saving...
2026-01-15T20:27:49.895868456Z [inf]  1:M 15 Jan 2026 20:27:42.222 * Background saving started by pid 498
2026-01-15T20:27:49.895875024Z [inf]  498:C 15 Jan 2026 20:27:42.255 * DB saved on disk
2026-01-15T20:27:49.895882123Z [inf]  498:C 15 Jan 2026 20:27:42.257 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T20:27:49.895888494Z [inf]  1:M 15 Jan 2026 20:27:42.323 * Background saving terminated with success
2026-01-15T20:28:49.792287912Z [inf]  1:M 15 Jan 2026 20:28:43.063 * 1 changes in 60 seconds. Saving...
2026-01-15T20:28:49.792294090Z [inf]  1:M 15 Jan 2026 20:28:43.066 * Background saving started by pid 499
2026-01-15T20:28:49.792300243Z [inf]  499:C 15 Jan 2026 20:28:43.083 * DB saved on disk
2026-01-15T20:28:49.792308080Z [inf]  499:C 15 Jan 2026 20:28:43.085 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T20:28:49.792314465Z [inf]  1:M 15 Jan 2026 20:28:43.167 * Background saving terminated with success
2026-01-15T20:49:41.480609942Z [inf]  1:M 15 Jan 2026 20:49:36.906 * 1 changes in 60 seconds. Saving...
2026-01-15T20:49:41.480621210Z [inf]  1:M 15 Jan 2026 20:49:36.909 * Background saving started by pid 500
2026-01-15T20:49:41.480628412Z [inf]  500:C 15 Jan 2026 20:49:36.932 * DB saved on disk
2026-01-15T20:49:41.480634782Z [inf]  500:C 15 Jan 2026 20:49:36.933 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T20:49:41.480640394Z [inf]  1:M 15 Jan 2026 20:49:37.010 * Background saving terminated with success
2026-01-15T20:50:41.493870331Z [inf]  1:M 15 Jan 2026 20:50:38.026 * 1 changes in 60 seconds. Saving...
2026-01-15T20:50:41.493877851Z [inf]  1:M 15 Jan 2026 20:50:38.030 * Background saving started by pid 501
2026-01-15T20:50:41.493882640Z [inf]  501:C 15 Jan 2026 20:50:38.187 * DB saved on disk
2026-01-15T20:50:41.493887174Z [inf]  501:C 15 Jan 2026 20:50:38.189 * Fork CoW for RDB: current 1 MB, peak 1 MB, average 1 MB
2026-01-15T20:50:41.493892056Z [inf]  1:M 15 Jan 2026 20:50:38.233 * Background saving terminated with success
2026-01-15T21:17:04.414163496Z [inf]  1:M 15 Jan 2026 21:17:02.235 * 1 changes in 60 seconds. Saving...
2026-01-15T21:17:04.414168695Z [inf]  1:M 15 Jan 2026 21:17:02.238 * Background saving started by pid 502
2026-01-15T21:17:04.414174807Z [inf]  502:C 15 Jan 2026 21:17:02.266 * DB saved on disk
2026-01-15T21:17:04.414179615Z [inf]  502:C 15 Jan 2026 21:17:02.269 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T21:17:04.414184158Z [inf]  1:M 15 Jan 2026 21:17:02.339 * Background saving terminated with success
2026-01-15T21:18:04.411845549Z [inf]  1:M 15 Jan 2026 21:18:03.072 * 1 changes in 60 seconds. Saving...
2026-01-15T21:18:04.411863145Z [inf]  1:M 15 Jan 2026 21:18:03.076 * Background saving started by pid 503
2026-01-15T21:18:04.411874910Z [inf]  503:C 15 Jan 2026 21:18:03.135 * DB saved on disk
2026-01-15T21:18:04.411880833Z [inf]  503:C 15 Jan 2026 21:18:03.137 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-15T21:18:04.411886175Z [inf]  1:M 15 Jan 2026 21:18:03.176 * Background saving terminated with success
2026-01-16T07:44:00.117392981Z [inf]  1:M 16 Jan 2026 07:43:57.545 * 1 changes in 60 seconds. Saving...
2026-01-16T07:44:00.117399873Z [inf]  1:M 16 Jan 2026 07:43:57.548 * Background saving started by pid 504
2026-01-16T07:44:00.117404878Z [inf]  504:C 16 Jan 2026 07:43:57.580 * DB saved on disk
2026-01-16T07:44:00.117409588Z [inf]  504:C 16 Jan 2026 07:43:57.582 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T07:44:00.117414147Z [inf]  1:M 16 Jan 2026 07:43:57.649 * Background saving terminated with success
2026-01-16T07:45:00.132684327Z [inf]  1:M 16 Jan 2026 07:44:58.043 * 1 changes in 60 seconds. Saving...
2026-01-16T07:45:00.132696433Z [inf]  1:M 16 Jan 2026 07:44:58.046 * Background saving started by pid 505
2026-01-16T07:45:00.132706726Z [inf]  505:C 16 Jan 2026 07:44:58.061 * DB saved on disk
2026-01-16T07:45:00.132712873Z [inf]  505:C 16 Jan 2026 07:44:58.063 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T07:45:00.132721365Z [inf]  1:M 16 Jan 2026 07:44:58.147 * Background saving terminated with success
2026-01-16T07:48:30.421015212Z [inf]  1:M 16 Jan 2026 07:48:26.486 * 1 changes in 60 seconds. Saving...
2026-01-16T07:48:30.421022754Z [inf]  1:M 16 Jan 2026 07:48:26.488 * Background saving started by pid 506
2026-01-16T07:48:30.421028236Z [inf]  506:C 16 Jan 2026 07:48:26.539 * DB saved on disk
2026-01-16T07:48:30.421033631Z [inf]  506:C 16 Jan 2026 07:48:26.542 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T07:48:30.421039202Z [inf]  1:M 16 Jan 2026 07:48:26.589 * Background saving terminated with success
2026-01-16T07:49:30.496828822Z [inf]  1:M 16 Jan 2026 07:49:27.019 * 1 changes in 60 seconds. Saving...
2026-01-16T07:49:30.496835757Z [inf]  1:M 16 Jan 2026 07:49:27.021 * Background saving started by pid 507
2026-01-16T07:49:30.496843215Z [inf]  507:C 16 Jan 2026 07:49:27.035 * DB saved on disk
2026-01-16T07:49:30.496848682Z [inf]  507:C 16 Jan 2026 07:49:27.037 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T07:49:30.496853629Z [inf]  1:M 16 Jan 2026 07:49:27.122 * Background saving terminated with success
2026-01-16T10:49:32.337604502Z [inf]  1:M 16 Jan 2026 10:49:22.832 * Background saving started by pid 508
2026-01-16T10:49:32.337614726Z [inf]  508:C 16 Jan 2026 10:49:22.846 * DB saved on disk
2026-01-16T10:49:32.337620021Z [inf]  508:C 16 Jan 2026 10:49:22.848 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T10:49:32.337625214Z [inf]  1:M 16 Jan 2026 10:49:22.933 * Background saving terminated with success
2026-01-16T10:49:32.337735643Z [inf]  1:M 16 Jan 2026 10:49:22.829 * 1 changes in 60 seconds. Saving...
2026-01-16T10:50:32.334451622Z [inf]  509:C 16 Jan 2026 10:50:23.059 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T10:50:32.334459175Z [inf]  1:M 16 Jan 2026 10:50:23.134 * Background saving terminated with success
2026-01-16T10:50:32.334511411Z [inf]  1:M 16 Jan 2026 10:50:23.031 * 1 changes in 60 seconds. Saving...
2026-01-16T10:50:32.334517824Z [inf]  1:M 16 Jan 2026 10:50:23.033 * Background saving started by pid 509
2026-01-16T10:50:32.334523622Z [inf]  509:C 16 Jan 2026 10:50:23.058 * DB saved on disk
2026-01-16T11:54:26.241729495Z [inf]  1:M 16 Jan 2026 11:54:25.190 * 1 changes in 60 seconds. Saving...
2026-01-16T11:54:26.241740255Z [inf]  1:M 16 Jan 2026 11:54:25.193 * Background saving started by pid 510
2026-01-16T11:54:26.241747492Z [inf]  510:C 16 Jan 2026 11:54:25.210 * DB saved on disk
2026-01-16T11:54:26.241754882Z [inf]  510:C 16 Jan 2026 11:54:25.212 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T11:54:26.241761570Z [inf]  1:M 16 Jan 2026 11:54:25.294 * Background saving terminated with success
2026-01-16T11:55:26.159145276Z [inf]  1:M 16 Jan 2026 11:55:26.016 * 1 changes in 60 seconds. Saving...
2026-01-16T11:55:26.159151533Z [inf]  1:M 16 Jan 2026 11:55:26.020 * Background saving started by pid 511
2026-01-16T11:55:26.159155692Z [inf]  511:C 16 Jan 2026 11:55:26.033 * DB saved on disk
2026-01-16T11:55:26.159160753Z [inf]  511:C 16 Jan 2026 11:55:26.034 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T11:55:26.159165380Z [inf]  1:M 16 Jan 2026 11:55:26.122 * Background saving terminated with success
2026-01-16T12:51:39.741574767Z [inf]  1:M 16 Jan 2026 12:51:38.273 * 1 changes in 60 seconds. Saving...
2026-01-16T12:51:39.741582882Z [inf]  1:M 16 Jan 2026 12:51:38.276 * Background saving started by pid 512
2026-01-16T12:51:39.741587922Z [inf]  512:C 16 Jan 2026 12:51:38.290 * DB saved on disk
2026-01-16T12:51:39.741592593Z [inf]  512:C 16 Jan 2026 12:51:38.292 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T12:51:39.741598479Z [inf]  1:M 16 Jan 2026 12:51:38.377 * Background saving terminated with success
2026-01-16T12:52:39.742097288Z [inf]  1:M 16 Jan 2026 12:52:39.077 * 1 changes in 60 seconds. Saving...
2026-01-16T12:52:39.742117595Z [inf]  1:M 16 Jan 2026 12:52:39.080 * Background saving started by pid 513
2026-01-16T12:52:39.742126889Z [inf]  513:C 16 Jan 2026 12:52:39.108 * DB saved on disk
2026-01-16T12:52:39.742134259Z [inf]  513:C 16 Jan 2026 12:52:39.109 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T12:52:39.742141459Z [inf]  1:M 16 Jan 2026 12:52:39.181 * Background saving terminated with success
2026-01-16T13:46:44.231541701Z [inf]  1:M 16 Jan 2026 13:46:40.075 * 1 changes in 60 seconds. Saving...
2026-01-16T13:46:44.231548638Z [inf]  1:M 16 Jan 2026 13:46:40.077 * Background saving started by pid 514
2026-01-16T13:46:44.231553851Z [inf]  514:C 16 Jan 2026 13:46:40.149 * DB saved on disk
2026-01-16T13:46:44.231558331Z [inf]  514:C 16 Jan 2026 13:46:40.151 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T13:46:44.231562798Z [inf]  1:M 16 Jan 2026 13:46:40.178 * Background saving terminated with success
2026-01-16T13:47:44.169000975Z [inf]  1:M 16 Jan 2026 13:47:41.076 * 1 changes in 60 seconds. Saving...
2026-01-16T13:47:44.169007748Z [inf]  1:M 16 Jan 2026 13:47:41.079 * Background saving started by pid 515
2026-01-16T13:47:44.169012903Z [inf]  515:C 16 Jan 2026 13:47:41.102 * DB saved on disk
2026-01-16T13:47:44.169017648Z [inf]  515:C 16 Jan 2026 13:47:41.104 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T13:47:44.169022011Z [inf]  1:M 16 Jan 2026 13:47:41.182 * Background saving terminated with success
2026-01-16T13:49:44.177194444Z [inf]  1:M 16 Jan 2026 13:49:38.352 * 1 changes in 60 seconds. Saving...
2026-01-16T13:49:44.177206430Z [inf]  1:M 16 Jan 2026 13:49:38.354 * Background saving started by pid 516
2026-01-16T13:49:44.177214665Z [inf]  516:C 16 Jan 2026 13:49:38.419 * DB saved on disk
2026-01-16T13:49:44.177224028Z [inf]  516:C 16 Jan 2026 13:49:38.421 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T13:49:44.177230561Z [inf]  1:M 16 Jan 2026 13:49:38.455 * Background saving terminated with success
2026-01-16T13:50:44.214817879Z [inf]  1:M 16 Jan 2026 13:50:39.066 * 1 changes in 60 seconds. Saving...
2026-01-16T13:50:44.214826919Z [inf]  1:M 16 Jan 2026 13:50:39.069 * Background saving started by pid 517
2026-01-16T13:50:44.214833500Z [inf]  517:C 16 Jan 2026 13:50:39.094 * DB saved on disk
2026-01-16T13:50:44.214840230Z [inf]  517:C 16 Jan 2026 13:50:39.095 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T13:50:44.214846089Z [inf]  1:M 16 Jan 2026 13:50:39.170 * Background saving terminated with success
2026-01-16T15:36:43.515404102Z [inf]  1:M 16 Jan 2026 15:36:38.606 * 1 changes in 60 seconds. Saving...
2026-01-16T15:36:43.515410528Z [inf]  1:M 16 Jan 2026 15:36:38.608 * Background saving started by pid 518
2026-01-16T15:36:43.515416183Z [inf]  518:C 16 Jan 2026 15:36:38.647 * DB saved on disk
2026-01-16T15:36:43.515421371Z [inf]  518:C 16 Jan 2026 15:36:38.649 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T15:36:43.515426809Z [inf]  1:M 16 Jan 2026 15:36:38.709 * Background saving terminated with success
2026-01-16T15:37:43.536646487Z [inf]  1:M 16 Jan 2026 15:37:39.012 * 1 changes in 60 seconds. Saving...
2026-01-16T15:37:43.536661463Z [inf]  1:M 16 Jan 2026 15:37:39.015 * Background saving started by pid 519
2026-01-16T15:37:43.536669892Z [inf]  519:C 16 Jan 2026 15:37:39.033 * DB saved on disk
2026-01-16T15:37:43.536675965Z [inf]  519:C 16 Jan 2026 15:37:39.035 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T15:37:43.536682170Z [inf]  1:M 16 Jan 2026 15:37:39.115 * Background saving terminated with success
2026-01-16T15:56:25.025974447Z [inf]  1:M 16 Jan 2026 15:56:20.044 * 1 changes in 60 seconds. Saving...
2026-01-16T15:56:25.025982499Z [inf]  1:M 16 Jan 2026 15:56:20.047 * Background saving started by pid 520
2026-01-16T15:56:25.025990706Z [inf]  520:C 16 Jan 2026 15:56:20.065 * DB saved on disk
2026-01-16T15:56:25.025994902Z [inf]  520:C 16 Jan 2026 15:56:20.068 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T15:56:25.025998977Z [inf]  1:M 16 Jan 2026 15:56:20.148 * Background saving terminated with success
2026-01-16T15:57:24.916875509Z [inf]  1:M 16 Jan 2026 15:57:21.069 * 1 changes in 60 seconds. Saving...
2026-01-16T15:57:24.916880686Z [inf]  1:M 16 Jan 2026 15:57:21.072 * Background saving started by pid 521
2026-01-16T15:57:24.916885008Z [inf]  521:C 16 Jan 2026 15:57:21.092 * DB saved on disk
2026-01-16T15:57:24.916889342Z [inf]  521:C 16 Jan 2026 15:57:21.094 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T15:57:24.916893544Z [inf]  1:M 16 Jan 2026 15:57:21.174 * Background saving terminated with success
2026-01-16T16:33:27.748940224Z [inf]  1:M 16 Jan 2026 16:33:27.167 * 1 changes in 60 seconds. Saving...
2026-01-16T16:33:27.748947945Z [inf]  1:M 16 Jan 2026 16:33:27.170 * Background saving started by pid 522
2026-01-16T16:33:27.748953006Z [inf]  522:C 16 Jan 2026 16:33:27.187 * DB saved on disk
2026-01-16T16:33:27.748960352Z [inf]  522:C 16 Jan 2026 16:33:27.188 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T16:33:27.748965135Z [inf]  1:M 16 Jan 2026 16:33:27.271 * Background saving terminated with success
2026-01-16T16:34:37.759278866Z [inf]  1:M 16 Jan 2026 16:34:28.073 * 1 changes in 60 seconds. Saving...
2026-01-16T16:34:37.759285358Z [inf]  1:M 16 Jan 2026 16:34:28.077 * Background saving started by pid 523
2026-01-16T16:34:37.759289674Z [inf]  523:C 16 Jan 2026 16:34:28.125 * DB saved on disk
2026-01-16T16:34:37.759293783Z [inf]  523:C 16 Jan 2026 16:34:28.127 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T16:34:37.759297774Z [inf]  1:M 16 Jan 2026 16:34:28.177 * Background saving terminated with success
2026-01-16T17:13:31.553807247Z [inf]  1:M 16 Jan 2026 17:13:24.942 # Possible SECURITY ATTACK detected. It looks like somebody is sending POST or Host: commands to Redis. This is likely due to an attacker attempting to use Cross Protocol Scripting to compromise your Redis instance. Connection from 100.64.0.14:56706 aborted.
2026-01-16T17:18:01.559651560Z [inf]  1:M 16 Jan 2026 17:17:56.080 * 1 changes in 60 seconds. Saving...
2026-01-16T17:18:01.559659473Z [inf]  1:M 16 Jan 2026 17:17:56.083 * Background saving started by pid 524
2026-01-16T17:18:01.559665450Z [inf]  524:C 16 Jan 2026 17:17:56.096 * DB saved on disk
2026-01-16T17:18:01.559670664Z [inf]  524:C 16 Jan 2026 17:17:56.098 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T17:18:01.559679216Z [inf]  1:M 16 Jan 2026 17:17:56.184 * Background saving terminated with success
2026-01-16T17:19:01.621075954Z [inf]  1:M 16 Jan 2026 17:18:57.093 * 1 changes in 60 seconds. Saving...
2026-01-16T17:19:01.621091521Z [inf]  1:M 16 Jan 2026 17:18:57.096 * Background saving started by pid 525
2026-01-16T17:19:01.621098064Z [inf]  525:C 16 Jan 2026 17:18:57.133 * DB saved on disk
2026-01-16T17:19:01.621104254Z [inf]  525:C 16 Jan 2026 17:18:57.135 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T17:19:01.621111083Z [inf]  1:M 16 Jan 2026 17:18:57.197 * Background saving terminated with success
2026-01-16T18:36:47.613769949Z [inf]  1:M 16 Jan 2026 18:36:41.544 * 1 changes in 60 seconds. Saving...
2026-01-16T18:36:47.613780148Z [inf]  1:M 16 Jan 2026 18:36:41.547 * Background saving started by pid 526
2026-01-16T18:36:47.613791142Z [inf]  526:C 16 Jan 2026 18:36:41.599 * DB saved on disk
2026-01-16T18:36:47.613798548Z [inf]  526:C 16 Jan 2026 18:36:41.600 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T18:36:47.613803438Z [inf]  1:M 16 Jan 2026 18:36:41.648 * Background saving terminated with success
2026-01-16T18:37:47.470785457Z [inf]  1:M 16 Jan 2026 18:37:42.049 * 1 changes in 60 seconds. Saving...
2026-01-16T18:37:47.470822901Z [inf]  1:M 16 Jan 2026 18:37:42.052 * Background saving started by pid 527
2026-01-16T18:37:47.470829509Z [inf]  527:C 16 Jan 2026 18:37:42.069 * DB saved on disk
2026-01-16T18:37:47.470834518Z [inf]  527:C 16 Jan 2026 18:37:42.070 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T18:37:47.470838987Z [inf]  1:M 16 Jan 2026 18:37:42.153 * Background saving terminated with success
2026-01-16T21:28:54.597328730Z [inf]  1:M 16 Jan 2026 21:28:50.436 * 1 changes in 60 seconds. Saving...
2026-01-16T21:28:54.597336491Z [inf]  1:M 16 Jan 2026 21:28:50.439 * Background saving started by pid 528
2026-01-16T21:28:54.597341746Z [inf]  528:C 16 Jan 2026 21:28:50.458 * DB saved on disk
2026-01-16T21:28:54.597346305Z [inf]  528:C 16 Jan 2026 21:28:50.460 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T21:28:54.597350955Z [inf]  1:M 16 Jan 2026 21:28:50.539 * Background saving terminated with success
2026-01-16T21:29:54.518139984Z [inf]  1:M 16 Jan 2026 21:29:51.062 * 1 changes in 60 seconds. Saving...
2026-01-16T21:29:54.518146270Z [inf]  1:M 16 Jan 2026 21:29:51.065 * Background saving started by pid 529
2026-01-16T21:29:54.518150926Z [inf]  529:C 16 Jan 2026 21:29:51.092 * DB saved on disk
2026-01-16T21:29:54.518155488Z [inf]  529:C 16 Jan 2026 21:29:51.093 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T21:29:54.518160034Z [inf]  1:M 16 Jan 2026 21:29:51.166 * Background saving terminated with success
2026-01-16T21:32:34.546676071Z [inf]  1:M 16 Jan 2026 21:32:29.631 * 1 changes in 60 seconds. Saving...
2026-01-16T21:32:34.546686030Z [inf]  1:M 16 Jan 2026 21:32:29.636 * Background saving started by pid 530
2026-01-16T21:32:34.546692256Z [inf]  530:C 16 Jan 2026 21:32:29.672 * DB saved on disk
2026-01-16T21:32:34.546697374Z [inf]  530:C 16 Jan 2026 21:32:29.674 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T21:32:34.546702301Z [inf]  1:M 16 Jan 2026 21:32:29.737 * Background saving terminated with success
2026-01-16T21:33:34.559280893Z [inf]  1:M 16 Jan 2026 21:33:30.079 * 1 changes in 60 seconds. Saving...
2026-01-16T21:33:34.559288312Z [inf]  1:M 16 Jan 2026 21:33:30.083 * Background saving started by pid 531
2026-01-16T21:33:34.559293285Z [inf]  531:C 16 Jan 2026 21:33:30.115 * DB saved on disk
2026-01-16T21:33:34.559298032Z [inf]  531:C 16 Jan 2026 21:33:30.117 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T21:33:34.559302280Z [inf]  1:M 16 Jan 2026 21:33:30.184 * Background saving terminated with success
2026-01-16T21:37:04.773541995Z [inf]  1:M 16 Jan 2026 21:36:57.147 * 1 changes in 60 seconds. Saving...
2026-01-16T21:37:04.773572537Z [inf]  1:M 16 Jan 2026 21:36:57.150 * Background saving started by pid 532
2026-01-16T21:37:04.773580406Z [inf]  532:C 16 Jan 2026 21:36:57.174 * DB saved on disk
2026-01-16T21:37:04.773585759Z [inf]  532:C 16 Jan 2026 21:36:57.176 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T21:37:04.773590195Z [inf]  1:M 16 Jan 2026 21:36:57.251 * Background saving terminated with success
2026-01-16T21:38:04.911335719Z [inf]  1:M 16 Jan 2026 21:37:58.085 * 1 changes in 60 seconds. Saving...
2026-01-16T21:38:04.911341319Z [inf]  1:M 16 Jan 2026 21:37:58.088 * Background saving started by pid 533
2026-01-16T21:38:04.911347563Z [inf]  533:C 16 Jan 2026 21:37:58.111 * DB saved on disk
2026-01-16T21:38:04.911354142Z [inf]  533:C 16 Jan 2026 21:37:58.113 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T21:38:04.911360301Z [inf]  1:M 16 Jan 2026 21:37:58.189 * Background saving terminated with success
2026-01-16T21:41:44.819977730Z [inf]  1:M 16 Jan 2026 21:41:37.371 * 1 changes in 60 seconds. Saving...
2026-01-16T21:41:44.819990499Z [inf]  1:M 16 Jan 2026 21:41:37.374 * Background saving started by pid 534
2026-01-16T21:41:44.819997428Z [inf]  534:C 16 Jan 2026 21:41:37.427 * DB saved on disk
2026-01-16T21:41:44.820007341Z [inf]  534:C 16 Jan 2026 21:41:37.428 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T21:41:44.820013667Z [inf]  1:M 16 Jan 2026 21:41:37.475 * Background saving terminated with success
2026-01-16T21:42:44.833483436Z [inf]  1:M 16 Jan 2026 21:42:38.098 * 1 changes in 60 seconds. Saving...
2026-01-16T21:42:44.833490922Z [inf]  1:M 16 Jan 2026 21:42:38.101 * Background saving started by pid 535
2026-01-16T21:42:44.833496524Z [inf]  535:C 16 Jan 2026 21:42:38.116 * DB saved on disk
2026-01-16T21:42:44.833502169Z [inf]  535:C 16 Jan 2026 21:42:38.118 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T21:42:44.833508004Z [inf]  1:M 16 Jan 2026 21:42:38.202 * Background saving terminated with success
2026-01-16T22:07:56.749283392Z [inf]  1:M 16 Jan 2026 22:07:47.892 * 1 changes in 60 seconds. Saving...
2026-01-16T22:07:56.749297982Z [inf]  1:M 16 Jan 2026 22:07:47.895 * Background saving started by pid 536
2026-01-16T22:07:56.749306476Z [inf]  536:C 16 Jan 2026 22:07:47.921 * DB saved on disk
2026-01-16T22:07:56.749314943Z [inf]  536:C 16 Jan 2026 22:07:47.923 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T22:07:56.749320781Z [inf]  1:M 16 Jan 2026 22:07:47.996 * Background saving terminated with success
2026-01-16T22:08:56.835470877Z [inf]  1:M 16 Jan 2026 22:08:48.017 * 1 changes in 60 seconds. Saving...
2026-01-16T22:08:56.835479110Z [inf]  1:M 16 Jan 2026 22:08:48.021 * Background saving started by pid 537
2026-01-16T22:08:56.835492662Z [inf]  537:C 16 Jan 2026 22:08:48.037 * DB saved on disk
2026-01-16T22:08:56.835499856Z [inf]  537:C 16 Jan 2026 22:08:48.039 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T22:08:56.835505947Z [inf]  1:M 16 Jan 2026 22:08:48.121 * Background saving terminated with success
2026-01-16T22:38:48.586268043Z [inf]  1:M 16 Jan 2026 22:38:40.304 * 1 changes in 60 seconds. Saving...
2026-01-16T22:38:48.586274206Z [inf]  1:M 16 Jan 2026 22:38:40.306 * Background saving started by pid 538
2026-01-16T22:38:48.586280435Z [inf]  538:C 16 Jan 2026 22:38:40.323 * DB saved on disk
2026-01-16T22:38:48.586286259Z [inf]  538:C 16 Jan 2026 22:38:40.325 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T22:38:48.586291801Z [inf]  1:M 16 Jan 2026 22:38:40.407 * Background saving terminated with success
2026-01-16T22:39:48.668635025Z [inf]  1:M 16 Jan 2026 22:39:41.008 * 1 changes in 60 seconds. Saving...
2026-01-16T22:39:48.668642470Z [inf]  1:M 16 Jan 2026 22:39:41.011 * Background saving started by pid 539
2026-01-16T22:39:48.668646863Z [inf]  539:C 16 Jan 2026 22:39:41.026 * DB saved on disk
2026-01-16T22:39:48.668651076Z [inf]  539:C 16 Jan 2026 22:39:41.027 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T22:39:48.668654931Z [inf]  1:M 16 Jan 2026 22:39:41.111 * Background saving terminated with success
2026-01-16T23:00:59.528862510Z [inf]  1:M 16 Jan 2026 23:00:54.510 * 1 changes in 60 seconds. Saving...
2026-01-16T23:00:59.528874982Z [inf]  1:M 16 Jan 2026 23:00:54.514 * Background saving started by pid 540
2026-01-16T23:00:59.528882434Z [inf]  540:C 16 Jan 2026 23:00:54.581 * DB saved on disk
2026-01-16T23:00:59.528889431Z [inf]  540:C 16 Jan 2026 23:00:54.583 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T23:00:59.528895548Z [inf]  1:M 16 Jan 2026 23:00:54.615 * Background saving terminated with success
2026-01-16T23:01:59.524668757Z [inf]  1:M 16 Jan 2026 23:01:55.023 * 1 changes in 60 seconds. Saving...
2026-01-16T23:01:59.524675954Z [inf]  1:M 16 Jan 2026 23:01:55.027 * Background saving started by pid 541
2026-01-16T23:01:59.524681760Z [inf]  541:C 16 Jan 2026 23:01:55.048 * DB saved on disk
2026-01-16T23:01:59.524688007Z [inf]  541:C 16 Jan 2026 23:01:55.050 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T23:01:59.524694320Z [inf]  1:M 16 Jan 2026 23:01:55.129 * Background saving terminated with success
2026-01-16T23:14:30.136398531Z [inf]  1:M 16 Jan 2026 23:14:24.116 * 1 changes in 60 seconds. Saving...
2026-01-16T23:14:30.136405080Z [inf]  1:M 16 Jan 2026 23:14:24.119 * Background saving started by pid 542
2026-01-16T23:14:30.136409290Z [inf]  542:C 16 Jan 2026 23:14:24.136 * DB saved on disk
2026-01-16T23:14:30.136413485Z [inf]  542:C 16 Jan 2026 23:14:24.138 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T23:14:30.136418268Z [inf]  1:M 16 Jan 2026 23:14:24.220 * Background saving terminated with success
2026-01-16T23:15:30.149269638Z [inf]  1:M 16 Jan 2026 23:15:25.018 * 1 changes in 60 seconds. Saving...
2026-01-16T23:15:30.149275188Z [inf]  1:M 16 Jan 2026 23:15:25.021 * Background saving started by pid 543
2026-01-16T23:15:30.149280947Z [inf]  543:C 16 Jan 2026 23:15:25.064 * DB saved on disk
2026-01-16T23:15:30.149288792Z [inf]  543:C 16 Jan 2026 23:15:25.066 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T23:15:30.149294827Z [inf]  1:M 16 Jan 2026 23:15:25.121 * Background saving terminated with success
2026-01-16T23:43:02.870078998Z [inf]  1:M 16 Jan 2026 23:42:53.021 * 1 changes in 60 seconds. Saving...
2026-01-16T23:43:02.870089854Z [inf]  1:M 16 Jan 2026 23:42:53.024 * Background saving started by pid 544
2026-01-16T23:43:02.870097171Z [inf]  544:C 16 Jan 2026 23:42:53.050 * DB saved on disk
2026-01-16T23:43:02.870103544Z [inf]  544:C 16 Jan 2026 23:42:53.051 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T23:43:02.870111651Z [inf]  1:M 16 Jan 2026 23:42:53.125 * Background saving terminated with success
2026-01-16T23:44:02.884278780Z [inf]  1:M 16 Jan 2026 23:43:54.034 * 1 changes in 60 seconds. Saving...
2026-01-16T23:44:02.884289025Z [inf]  1:M 16 Jan 2026 23:43:54.036 * Background saving started by pid 545
2026-01-16T23:44:02.884295687Z [inf]  545:C 16 Jan 2026 23:43:54.052 * DB saved on disk
2026-01-16T23:44:02.884302396Z [inf]  545:C 16 Jan 2026 23:43:54.054 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
2026-01-16T23:44:02.884309165Z [inf]  1:M 16 Jan 2026 23:43:54.137 * Background saving terminated with success