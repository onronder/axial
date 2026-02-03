🚨 [SyncJob] Auth failure for provider google_drive. User interaction required.
Events (total)
Users (30d)
Level: Fatal
/api/v1/integrations/{integration_id}/sync
4
0
Regressed

Resolve


Archive




Priority
High
Assignee

Unassigned

All Envs

Since First Seen
Filter events…


Events
4

Users
0
transaction
75%
(empty)
url
75%
(empty)
release
75%
local
environment
75%
test
View all tags and feature flags

Events
in this issue
First
Latest
Recommended
ID: 6612eca6
2 minutes ago
|
JSON
|

Copy as Markdown
Jump to:
Highlights
Breadcrumbs
Logs
Trace
Tags
Context

Chrome
144

CPython
3.11.14

macOS
47a80db9dcc6
production

Highlights

Edit
handled
handled
--
level
level
fatal
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/9f3c247a-a2b5-4678-9909-c1e425dbeaaa/sync
Trace: Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Message
🚨 [SyncJob] Auth failure for provider google_drive. User interaction required.

Breadcrumbs



Copy
Message - This event
fatal
Feb 3, 7:52:22.080 PM UTC
🚨 [SyncJob] Auth failure for provider google_drive. User interaction required.
api.v1.integrations
error
Feb 3, 7:52:22.078 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:22,078
}
connectors.drive
error
Feb 3, 7:52:22.076 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:22,076
}
services.oauth_token_manager
error
Feb 3, 7:52:22.073 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:22,073
}
Httplib
warning
Feb 3, 7:52:22.073 PM UTC
[Filtered]

{
7 items
}

View 36 more

Logs
info

Feb 3, 7:52:32.315 PM
100.64.0.10:45834 - "GET /api/v1/integrations/web/crawl/active HTTP/1.1" 200
info

Feb 3, 7:52:32.315 PM
✅ [13f83f24] GET /api/v1/integrations/web/crawl/active → 200 (146.9ms)
info

Feb 3, 7:52:32.314 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/web_crawl_configs?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=in.%28pending%2Cdiscovering%2Cprocessing%29&order=created_at.desc&limit=1 "HTTP/2 200 OK"
info

Feb 3, 7:52:32.281 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
info

Feb 3, 7:52:32.223 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"

View more

Trace Preview
View Full Trace
0.00ms10.00s20.00s30.00s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s
87 hidden spans

3

http.server
—
/api/v1/integrations/available
546.32ms

5

http.server
—
/api/v1/integrations/{provider}/ingested-files
546.83ms

3

http.server
—
/api/v1/integrations/web/crawl/active
115.43ms

20

http.server
—
/api/v1/integrations/{integration_id}/sync
1.03s

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
33.28ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
43.68ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
40.03ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
52.60ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations
47.76ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
97.56ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
63.60ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs
94.17ms
35 hidden spans

HTTP Request


POST
… a2b5-4678-9909-c1e425dbeaaa/sync
axial-production-1503.up.railway.app
Headers
Accept
application/json, text/plain, */*
Accept-Encoding
gzip, deflate, br, zstd
Accept-Language
tr
Authorization
[Filtered]
Baggage
sentry-environment=vercel-production,sentry-release=47a80db9dcc60aafc577bbcbc453e677a56d5f4e,sentry-public_key=18f4a279a98e4442868e3cd724ead3a2,sentry-trace_id=fdf2c2e4ecb74d9eb922dacd4976f6b1,sentry-org_id=[Filtered],sentry-sampled=true,sentry-sample_rand=0.5865472643346693,sentry-sample_rate=1
Show more...

Tags





browser
browser
Chrome 144
browser.name
name
Chrome
client_os
client_os
macOS
client_os.name
name
macOS
device
device
Mac
device.family
family
Mac
environment
environment
production
level
level
fatal
logger
logger
api.v1.integrations
release
release
47a80db9dcc6
runtime
runtime
CPython 3.11.14
runtime.name
name
CPython
server_name
server_name
6c5bcc99ac81
transaction
transaction
/api/v1/integrations/{integration_id}/sync
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/9f3c247a-a2b5-4678-9909-c1e425dbeaaa/sync

Contexts
User
Geography
Washington, United States (US)
Browser

Name
Chrome
Version
144
Runtime

Build
3.11.14 (main, Feb 3 2026, 03:11:33) [GCC 14.2.0]
Name
CPython
Version
3.11.14
Client Operating System

Name
macOS
Device

Brand
Apple
Family
Mac
Model
Mac
Trace Details
Client Sample Rate
1
Data

{
3 items
}
Operation Name
http.server
Origin
auto.http.starlette
Parent Span ID
acd3e763be645e19
Span ID
947f5560ac68af34
Status
ok
Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Additional Data


asctime	
2026-02-03 19:52:22,080
sys.argv	

[
6 items
]

Packages

SDK

Event Grouping Information

❌ [SyncJob] Failed 46cdbded-22c4-4f44-8d8a-72e9749c59ae: Integration requires reconnection (Token Expired/Revoked)
Events (total)
Users (30d)
Level: Error
/api/v1/integrations/{integration_id}/sync
1
0
New

Resolve


Archive




Priority
High
Assignee

Unassigned

All Envs

Since First Seen
Filter events…


Event
1

Users
0
transaction
100%
/api/v1/integrations/{integration_id}/sync
url
100%
http://axial-production-1503.up.railway.app/api/v1/integrations/9f3c247a-a2b5-4678-9909-c1e425dbeaaa/sync
release
100%
47a80db9dcc6
environment
100%
production
View all tags and feature flags

Events
in this issue
First
Latest
Recommended
ID: c6362bcc
2 minutes ago
|
JSON
|

Copy as Markdown
Jump to:
Highlights
Breadcrumbs
Logs
Trace
Tags
Context

Chrome
144

CPython
3.11.14

macOS
47a80db9dcc6
production

Highlights

Edit
handled
handled
--
level
level
error
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/9f3c247a-a2b5-4678-9909-c1e425dbeaaa/sync
Trace: Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Message
❌ [SyncJob] Failed 46cdbded-22c4-4f44-8d8a-72e9749c59ae: Integration requires reconnection (Token Expired/Revoked)

Breadcrumbs



Copy
Message - This event
error
Feb 3, 7:52:22.078 PM UTC
❌ [SyncJob] Failed 46cdbded-22c4-4f44-8d8a-72e9749c59ae: Integration requires reconnection (Token Expired/Revoked)
connectors.drive
error
Feb 3, 7:52:22.076 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:22,076
}
services.oauth_token_manager
error
Feb 3, 7:52:22.073 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:22,073
}
Httplib
warning
Feb 3, 7:52:22.073 PM UTC
[Filtered]

{
7 items
}
services.oauth_token_manager
info
Feb 3, 7:52:22.029 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:22,029
}

View 35 more

Logs
info

Feb 3, 7:52:32.315 PM
100.64.0.10:45834 - "GET /api/v1/integrations/web/crawl/active HTTP/1.1" 200
info

Feb 3, 7:52:32.315 PM
✅ [13f83f24] GET /api/v1/integrations/web/crawl/active → 200 (146.9ms)
info

Feb 3, 7:52:32.314 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/web_crawl_configs?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=in.%28pending%2Cdiscovering%2Cprocessing%29&order=created_at.desc&limit=1 "HTTP/2 200 OK"
info

Feb 3, 7:52:32.281 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
info

Feb 3, 7:52:32.223 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"

View more

Trace Preview
View Full Trace
0.00ms10.00s20.00s30.00s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s
87 hidden spans

3

http.server
—
/api/v1/integrations/available
546.32ms

5

http.server
—
/api/v1/integrations/{provider}/ingested-files
546.83ms

3

http.server
—
/api/v1/integrations/web/crawl/active
115.43ms

20

http.server
—
/api/v1/integrations/{integration_id}/sync
1.03s

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
33.28ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
43.68ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
40.03ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
52.60ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations
47.76ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
97.56ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
63.60ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/ingestion_jobs
94.17ms
35 hidden spans

HTTP Request


POST
… a2b5-4678-9909-c1e425dbeaaa/sync
axial-production-1503.up.railway.app
Headers
Accept
application/json, text/plain, */*
Accept-Encoding
gzip, deflate, br, zstd
Accept-Language
tr
Authorization
[Filtered]
Baggage
sentry-environment=vercel-production,sentry-release=47a80db9dcc60aafc577bbcbc453e677a56d5f4e,sentry-public_key=18f4a279a98e4442868e3cd724ead3a2,sentry-trace_id=fdf2c2e4ecb74d9eb922dacd4976f6b1,sentry-org_id=[Filtered],sentry-sampled=true,sentry-sample_rand=0.5865472643346693,sentry-sample_rate=1
Show more...

Tags





browser
browser
Chrome 144
browser.name
name
Chrome
client_os
client_os
macOS
client_os.name
name
macOS
device
device
Mac
device.family
family
Mac
environment
environment
production
level
level
error
logger
logger
api.v1.integrations
release
release
47a80db9dcc6
runtime
runtime
CPython 3.11.14
runtime.name
name
CPython
server_name
server_name
6c5bcc99ac81
transaction
transaction
/api/v1/integrations/{integration_id}/sync
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/9f3c247a-a2b5-4678-9909-c1e425dbeaaa/sync

Contexts
User
Geography
Washington, United States (US)
Browser

Name
Chrome
Version
144
Runtime

Build
3.11.14 (main, Feb 3 2026, 03:11:33) [GCC 14.2.0]
Name
CPython
Version
3.11.14
Client Operating System

Name
macOS
Device

Brand
Apple
Family
Mac
Model
Mac
Trace Details
Client Sample Rate
1
Data

{
3 items
}
Operation Name
http.server
Origin
auto.http.starlette
Parent Span ID
acd3e763be645e19
Span ID
947f5560ac68af34
Status
ok
Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Additional Data


asctime	
2026-02-03 19:52:22,078
sys.argv	

[
6 items
]

Packages

SDK

Event Grouping Information


❌ Failed to refresh Google token: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})
Events (total)
Users (30d)
Level: Error
/api/v1/integrations/{provider}/items
3
0
New

Resolve


Archive




Priority
High
Assignee

Unassigned

All Envs

Since First Seen
Filter events…


Events
3

Users
0
transaction
67%
/api/v1/integrations/{provider}/items
url
67%
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items
release
100%
47a80db9dcc6
environment
100%
production
View all tags and feature flags

Events
in this issue
First
Latest
Recommended
ID: 3d2ead06
2 minutes ago
|
JSON
|

Copy as Markdown
Jump to:
Highlights
Breadcrumbs
Logs
Trace
Tags
Context

Chrome
144

CPython
3.11.14

macOS
47a80db9dcc6
production

Highlights

Edit
handled
handled
--
level
level
error
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items
Trace: Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Message
❌ Failed to refresh Google token: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})

Breadcrumbs



Copy
Message - This event
error
Feb 3, 7:52:27.970 PM UTC
❌ Failed to refresh Google token: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})
Httplib
warning
Feb 3, 7:52:27.970 PM UTC
[Filtered]

{
7 items
}
services.oauth_token_manager
info
Feb 3, 7:52:27.913 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:27,913
}
Httplib
info
Feb 3, 7:52:27.913 PM UTC
https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations

{
7 items
}
httpx
info
Feb 3, 7:52:27.912 PM UTC
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&connector_definition_id=eq.a1b2c3d4-1111-4000-8000-00000…

{
asctime: 2026-02-03 19:52:27,912
}

View 7 more

Logs
info

Feb 3, 7:52:32.315 PM
100.64.0.10:45834 - "GET /api/v1/integrations/web/crawl/active HTTP/1.1" 200
info

Feb 3, 7:52:32.315 PM
✅ [13f83f24] GET /api/v1/integrations/web/crawl/active → 200 (146.9ms)
info

Feb 3, 7:52:32.314 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/web_crawl_configs?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=in.%28pending%2Cdiscovering%2Cprocessing%29&order=created_at.desc&limit=1 "HTTP/2 200 OK"
info

Feb 3, 7:52:32.281 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
info

Feb 3, 7:52:32.223 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"

View more

Trace Preview
View Full Trace
0.00ms10.00s20.00s30.00s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s
87 hidden spans

3

http.server
—
/api/v1/integrations/status
562.18ms

5

http.server
—
/api/v1/integrations/{provider}/ingested-files
414.99ms

3

http.server
—
/api/v1/integrations/available
415.41ms

5

http.server
—
/api/v1/integrations/{provider}/items
547.98ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
31.17ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
43.19ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/connector_definitions
31.06ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations
31.62ms

http.client
—
POST https://oauth2.googleapis.com/token
46.67ms

3

http.server
—
/api/v1/integrations/web/crawl/active
147.99ms

HTTP Request


GET
… /integrations/google_drive/items
axial-production-1503.up.railway.app
Query String
parent_id
root
Headers
Accept
application/json, text/plain, */*
Accept-Encoding
gzip, deflate, br, zstd
Accept-Language
tr
Authorization
[Filtered]
Baggage
sentry-environment=vercel-production,sentry-release=47a80db9dcc60aafc577bbcbc453e677a56d5f4e,sentry-public_key=18f4a279a98e4442868e3cd724ead3a2,sentry-trace_id=fdf2c2e4ecb74d9eb922dacd4976f6b1,sentry-org_id=[Filtered],sentry-sampled=true,sentry-sample_rand=0.5865472643346693,sentry-sample_rate=1
Show more...

Tags





browser
browser
Chrome 144
browser.name
name
Chrome
client_os
client_os
macOS
client_os.name
name
macOS
device
device
Mac
device.family
family
Mac
environment
environment
production
level
level
error
logger
logger
services.oauth_token_manager
release
release
47a80db9dcc6
runtime
runtime
CPython 3.11.14
runtime.name
name
CPython
server_name
server_name
6c5bcc99ac81
transaction
transaction
/api/v1/integrations/{provider}/items
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items

Contexts
User
Geography
Washington, United States (US)
Browser

Name
Chrome
Version
144
Runtime

Build
3.11.14 (main, Feb 3 2026, 03:11:33) [GCC 14.2.0]
Name
CPython
Version
3.11.14
Client Operating System

Name
macOS
Device

Brand
Apple
Family
Mac
Model
Mac
Trace Details
Client Sample Rate
1
Data

{
2 items
}
Operation Name
http.server
Origin
auto.http.starlette
Parent Span ID
86c54c30b8ab763f
Span ID
89baf5bfaf102aa7
Status
unknown
Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Additional Data


asctime	
2026-02-03 19:52:27,970
sys.argv	

[
6 items
]

Packages

SDK

Event Grouping Information


❌ Token refresh failed: Token refresh failed: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})
Events (total)
Users (30d)
Level: Error
/api/v1/integrations/{integration_id}/sync
3
0
New

Resolve


Archive




Priority
High
Assignee

Unassigned

All Envs

Since First Seen
Filter events…


Events
3

Users
0
transaction
67%
/api/v1/integrations/{provider}/items
url
67%
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items
release
100%
47a80db9dcc6
environment
100%
production
View all tags and feature flags

Events
in this issue
First
Latest
Recommended
ID: 4b34dada
3 minutes ago
|
JSON
|

Copy as Markdown
Jump to:
Highlights
Breadcrumbs
Logs
Trace
Tags
Context

Chrome
144

CPython
3.11.14

macOS
47a80db9dcc6
production

Highlights

Edit
handled
handled
--
level
level
error
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items
Trace: Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Message
❌ Token refresh failed: Token refresh failed: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})

Breadcrumbs



Copy
Message - This event
error
Feb 3, 7:52:27.972 PM UTC
❌ Token refresh failed: Token refresh failed: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})
services.oauth_token_manager
error
Feb 3, 7:52:27.970 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:27,970
}
Httplib
warning
Feb 3, 7:52:27.970 PM UTC
[Filtered]

{
7 items
}
services.oauth_token_manager
info
Feb 3, 7:52:27.913 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:27,913
}
Httplib
info
Feb 3, 7:52:27.913 PM UTC
https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations

{
7 items
}

View 8 more

Logs
info

Feb 3, 7:52:32.315 PM
100.64.0.10:45834 - "GET /api/v1/integrations/web/crawl/active HTTP/1.1" 200
info

Feb 3, 7:52:32.315 PM
✅ [13f83f24] GET /api/v1/integrations/web/crawl/active → 200 (146.9ms)
info

Feb 3, 7:52:32.314 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/web_crawl_configs?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=in.%28pending%2Cdiscovering%2Cprocessing%29&order=created_at.desc&limit=1 "HTTP/2 200 OK"
info

Feb 3, 7:52:32.281 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
info

Feb 3, 7:52:32.223 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"

View more

Trace Preview
View Full Trace
0.00ms10.00s20.00s30.00s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s
87 hidden spans

3

http.server
—
/api/v1/integrations/status
562.18ms

5

http.server
—
/api/v1/integrations/{provider}/ingested-files
414.99ms

3

http.server
—
/api/v1/integrations/available
415.41ms

5

http.server
—
/api/v1/integrations/{provider}/items
547.98ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
31.17ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
43.19ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/connector_definitions
31.06ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations
31.62ms

http.client
—
POST https://oauth2.googleapis.com/token
46.67ms

3

http.server
—
/api/v1/integrations/web/crawl/active
147.99ms

HTTP Request


GET
… /integrations/google_drive/items
axial-production-1503.up.railway.app
Query String
parent_id
root
Headers
Accept
application/json, text/plain, */*
Accept-Encoding
gzip, deflate, br, zstd
Accept-Language
tr
Authorization
[Filtered]
Baggage
sentry-environment=vercel-production,sentry-release=47a80db9dcc60aafc577bbcbc453e677a56d5f4e,sentry-public_key=18f4a279a98e4442868e3cd724ead3a2,sentry-trace_id=fdf2c2e4ecb74d9eb922dacd4976f6b1,sentry-org_id=[Filtered],sentry-sampled=true,sentry-sample_rand=0.5865472643346693,sentry-sample_rate=1
Show more...

Tags





browser
browser
Chrome 144
browser.name
name
Chrome
client_os
client_os
macOS
client_os.name
name
macOS
device
device
Mac
device.family
family
Mac
environment
environment
production
level
level
error
logger
logger
connectors.drive
release
release
47a80db9dcc6
runtime
runtime
CPython 3.11.14
runtime.name
name
CPython
server_name
server_name
6c5bcc99ac81
transaction
transaction
/api/v1/integrations/{provider}/items
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items

Contexts
User
Geography
Washington, United States (US)
Browser

Name
Chrome
Version
144
Runtime

Build
3.11.14 (main, Feb 3 2026, 03:11:33) [GCC 14.2.0]
Name
CPython
Version
3.11.14
Client Operating System

Name
macOS
Device

Brand
Apple
Family
Mac
Model
Mac
Trace Details
Client Sample Rate
1
Data

{
2 items
}
Operation Name
http.server
Origin
auto.http.starlette
Parent Span ID
86c54c30b8ab763f
Span ID
89baf5bfaf102aa7
Status
unknown
Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Additional Data


asctime	
2026-02-03 19:52:27,972
sys.argv	

[
6 items
]

Packages

SDK

Event Grouping Information


HTTPException
Events (total)
Users (30d)
Level: Error
{'error': 'CONNECTOR_FAILED', 'message': 'Failed to list items.', 'details': {'provider': 'google_drive', 'reason': 'Integration requires reconnection (Token Expired/Revoked)'}}
2
0
New
|
/api/v1/integrations/{provider}/items

Resolve


Archive




Priority
High
Assignee

Unassigned

All Envs

Since First Seen
Filter events…


Events
2

Users
0
transaction
100%
/api/v1/integrations/{provider}/items
url
100%
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items
release
100%
47a80db9dcc6
environment
100%
production
View all tags and feature flags

Events
in this issue
First
Latest
Recommended
ID: e993ceae
3 minutes ago
|
JSON
|

Copy as Markdown
Jump to:
Highlights
Stack Trace
Breadcrumbs
Logs
Trace
Tags
Context

Chrome
144

CPython
3.11.14

macOS
47a80db9dcc6
production

Highlights

Edit
handled
handled
yes
level
level
error
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items
Trace: Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Stack Trace




Newest

There are 4 chained exceptions in this event.


HTTPException
{'error': 'CONNECTOR_FAILED', 'message': 'Failed to list items.', 'details': {'provider': 'google_drive', 'reason': 'Integration requires reconnection (Token Expired/Revoked)'}}
mechanism
starlette
handled
true
/app/api/v1/error_utils.py in raise_http_error at line 267


Set up Code Mapping
In App

        details: Optional additional details
    
    Raises:
        HTTPException with structured detail
    """
    raise HTTPException(
        status_code=status_code,
        detail=build_error_payload(code, message, details),
    )
code	
"CONNECTOR_FAILED"
details	

{
provider: "google_drive",
reason: [Filtered]
}
message	
"Failed to list items."
status_code	
500

Show More
/app/api/v1/integrations.py in list_provider_items at line 2000
In App

Called from: fastapi/routing.py in run_endpoint_function

Show 3 more frames


ValueError
Integration requires reconnection (Token Expired/Revoked)
mechanism
starlette
handled
true
connectors/drive.py in _get_credentials_by_integration at line 233
In App

connectors/drive.py in _get_credentials at line 256
In App

connectors/drive.py in _list_files_sync at line 266
In App

Called from: anyio/_backends/_asyncio.py in run

Show 3 more frames

connectors/drive.py in list_files at line 262
In App

/app/api/v1/integrations.py in list_provider_items at line 1923
In App


TokenRefreshError
Token refresh failed: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})
mechanism
starlette
handled
true
services/oauth_token_manager.py in refresh_google_token at line 136
In App

services/oauth_token_manager.py in get_valid_credentials at line 683
In App

connectors/drive.py in _get_credentials_by_integration at line 213
In App


RefreshError
Is this correct?


Suspect Commit
Unified List Fixes
onronder committed 7d0c727 23 days ago

Breadcrumbs



Copy
Exception - This event
error
Feb 3, 7:52:27.982 PM UTC
RefreshError: ('invalid_grant: Bad Request', {'error': 'invalid_grant', 'error_description': 'Bad Request'})
api.v1.integrations
error
Feb 3, 7:52:27.973 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:27,973
}
connectors.drive
error
Feb 3, 7:52:27.972 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:27,972
}
services.oauth_token_manager
error
Feb 3, 7:52:27.970 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:27,970
}
Httplib
warning
Feb 3, 7:52:27.970 PM UTC
[Filtered]

{
7 items
}

View 10 more

Logs
info

Feb 3, 7:52:32.315 PM
100.64.0.10:45834 - "GET /api/v1/integrations/web/crawl/active HTTP/1.1" 200
info

Feb 3, 7:52:32.315 PM
✅ [13f83f24] GET /api/v1/integrations/web/crawl/active → 200 (146.9ms)
info

Feb 3, 7:52:32.314 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/web_crawl_configs?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=in.%28pending%2Cdiscovering%2Cprocessing%29&order=created_at.desc&limit=1 "HTTP/2 200 OK"
info

Feb 3, 7:52:32.281 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
info

Feb 3, 7:52:32.223 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"

View more

Trace Preview
View Full Trace
0.00ms10.00s20.00s30.00s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s
87 hidden spans

3

http.server
—
/api/v1/integrations/status
562.18ms

5

http.server
—
/api/v1/integrations/{provider}/ingested-files
414.99ms

3

http.server
—
/api/v1/integrations/available
415.41ms

5

http.server
—
/api/v1/integrations/{provider}/items
547.98ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
31.17ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
43.19ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/connector_definitions
31.06ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations
31.62ms

http.client
—
POST https://oauth2.googleapis.com/token
46.67ms

3

http.server
—
/api/v1/integrations/web/crawl/active
147.99ms

HTTP Request


GET
… /integrations/google_drive/items
axial-production-1503.up.railway.app
Query String
parent_id
root
Headers
Accept
application/json, text/plain, */*
Accept-Encoding
gzip, deflate, br, zstd
Accept-Language
tr
Authorization
[Filtered]
Baggage
sentry-environment=vercel-production,sentry-release=47a80db9dcc60aafc577bbcbc453e677a56d5f4e,sentry-public_key=18f4a279a98e4442868e3cd724ead3a2,sentry-trace_id=fdf2c2e4ecb74d9eb922dacd4976f6b1,sentry-org_id=[Filtered],sentry-sampled=true,sentry-sample_rand=0.5865472643346693,sentry-sample_rate=1
Show more...

Tags





browser
browser
Chrome 144
browser.name
name
Chrome
client_os
client_os
macOS
client_os.name
name
macOS
device
device
Mac
device.family
family
Mac
environment
environment
production
handled
handled
yes
level
level
error
mechanism
mechanism
starlette
release
release
47a80db9dcc6
runtime
runtime
CPython 3.11.14
runtime.name
name
CPython
server_name
server_name
6c5bcc99ac81
transaction
transaction
/api/v1/integrations/{provider}/items
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items

Contexts
User
Geography
Washington, United States (US)
Browser

Name
Chrome
Version
144
Runtime

Build
3.11.14 (main, Feb 3 2026, 03:11:33) [GCC 14.2.0]
Name
CPython
Version
3.11.14
Client Operating System

Name
macOS
Device

Brand
Apple
Family
Mac
Model
Mac
Trace Details
Client Sample Rate
1
Data

{
2 items
}
Operation Name
http.server
Origin
auto.http.starlette
Parent Span ID
86c54c30b8ab763f
Span ID
89baf5bfaf102aa7
Status
unknown
Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Additional Data


sys.argv	

[
6 items
]

Packages

SDK

Event Grouping Information


❌ [ListItems] Failed to list items for google_drive: Integration requires reconnection (Token Expired/Revoked)
Events (total)
Users (30d)
Level: Error
/api/v1/integrations/{provider}/items
2
0
New

Resolve


Archive




Priority
High
Assignee

Unassigned

All Envs

Since First Seen
Filter events…


Events
2

Users
0
transaction
100%
/api/v1/integrations/{provider}/items
url
100%
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items
release
100%
47a80db9dcc6
environment
100%
production
View all tags and feature flags

Events
in this issue
First
Latest
Recommended
ID: 25b14109
3 minutes ago
|
JSON
|

Copy as Markdown
Jump to:
Highlights
Breadcrumbs
Logs
Trace
Tags
Context

Chrome
144

CPython
3.11.14

macOS
47a80db9dcc6
production

Highlights

Edit
handled
handled
--
level
level
error
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items
Trace: Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Message
❌ [ListItems] Failed to list items for google_drive: Integration requires reconnection (Token Expired/Revoked)

Breadcrumbs



Copy
Message - This event
error
Feb 3, 7:52:27.973 PM UTC
❌ [ListItems] Failed to list items for google_drive: Integration requires reconnection (Token Expired/Revoked)
connectors.drive
error
Feb 3, 7:52:27.972 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:27,972
}
services.oauth_token_manager
error
Feb 3, 7:52:27.970 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:27,970
}
Httplib
warning
Feb 3, 7:52:27.970 PM UTC
[Filtered]

{
7 items
}
services.oauth_token_manager
info
Feb 3, 7:52:27.913 PM UTC
[Filtered]

{
asctime: 2026-02-03 19:52:27,913
}

View 9 more

Logs
info

Feb 3, 7:52:32.315 PM
100.64.0.10:45834 - "GET /api/v1/integrations/web/crawl/active HTTP/1.1" 200
info

Feb 3, 7:52:32.315 PM
✅ [13f83f24] GET /api/v1/integrations/web/crawl/active → 200 (146.9ms)
info

Feb 3, 7:52:32.314 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/web_crawl_configs?select=%2A&user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=in.%28pending%2Cdiscovering%2Cprocessing%29&order=created_at.desc&limit=1 "HTTP/2 200 OK"
info

Feb 3, 7:52:32.281 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=owner_id&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"
info

Feb 3, 7:52:32.223 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members?select=team_id%2Crole&member_user_id=eq.94e02b27-3523-42ff-a0c2-858dd8e77f85&status=neq.removed&limit=1 "HTTP/2 200 OK"

View more

Trace Preview
View Full Trace
0.00ms10.00s20.00s30.00s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s
87 hidden spans

3

http.server
—
/api/v1/integrations/status
562.18ms

5

http.server
—
/api/v1/integrations/{provider}/ingested-files
414.99ms

3

http.server
—
/api/v1/integrations/available
415.41ms

5

http.server
—
/api/v1/integrations/{provider}/items
547.98ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
31.17ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
43.19ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/connector_definitions
31.06ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/user_integrations
31.62ms

http.client
—
POST https://oauth2.googleapis.com/token
46.67ms

3

http.server
—
/api/v1/integrations/web/crawl/active
147.99ms

HTTP Request


GET
… /integrations/google_drive/items
axial-production-1503.up.railway.app
Query String
parent_id
root
Headers
Accept
application/json, text/plain, */*
Accept-Encoding
gzip, deflate, br, zstd
Accept-Language
tr
Authorization
[Filtered]
Baggage
sentry-environment=vercel-production,sentry-release=47a80db9dcc60aafc577bbcbc453e677a56d5f4e,sentry-public_key=18f4a279a98e4442868e3cd724ead3a2,sentry-trace_id=fdf2c2e4ecb74d9eb922dacd4976f6b1,sentry-org_id=[Filtered],sentry-sampled=true,sentry-sample_rand=0.5865472643346693,sentry-sample_rate=1
Show more...

Tags





browser
browser
Chrome 144
browser.name
name
Chrome
client_os
client_os
macOS
client_os.name
name
macOS
device
device
Mac
device.family
family
Mac
environment
environment
production
level
level
error
logger
logger
api.v1.integrations
release
release
47a80db9dcc6
runtime
runtime
CPython 3.11.14
runtime.name
name
CPython
server_name
server_name
6c5bcc99ac81
transaction
transaction
/api/v1/integrations/{provider}/items
url
url
http://axial-production-1503.up.railway.app/api/v1/integrations/google_drive/items

Contexts
User
Geography
Washington, United States (US)
Browser

Name
Chrome
Version
144
Runtime

Build
3.11.14 (main, Feb 3 2026, 03:11:33) [GCC 14.2.0]
Name
CPython
Version
3.11.14
Client Operating System

Name
macOS
Device

Brand
Apple
Family
Mac
Model
Mac
Trace Details
Client Sample Rate
1
Data

{
2 items
}
Operation Name
http.server
Origin
auto.http.starlette
Parent Span ID
86c54c30b8ab763f
Span ID
89baf5bfaf102aa7
Status
unknown
Trace ID
fdf2c2e4ecb74d9eb922dacd4976f6b1

Additional Data


asctime	
2026-02-03 19:52:27,973
sys.argv	

[
6 items
]

Packages

SDK

Event Grouping Information


