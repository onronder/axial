AttributeError
Events (total)
Users (30d)
Level: Error
'NoneType' object has no attribute 'data'
3
0
Unhandled
|
New
|
/api/v1/consent/organization

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
100%
/api/v1/consent/organization
url
100%
http://axial-production-1503.up.railway.app/api/v1/consent/organization
release
100%
bdd9a66b6c31
environment
100%
production
View all tags and feature flags

Events
in this issue
First
Latest
Recommended
ID: 89740467
a minute ago
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
bdd9a66b6c31
production

Highlights

Edit
handled
handled
no
level
level
error
url
url
http://axial-production-1503.up.railway.app/api/v1/consent/organization
Trace: Trace ID
ed56ad230ef94b7baa13f9adab5b6e8b

Stack Trace




Newest

AttributeError
'NoneType' object has no attribute 'data'
mechanism
starlette
handled
false
/app/api/v1/consent.py in get_org_consent at line 143


Set up Code Mapping
In App

        .select("*")\
        .eq("organization_id", organization_id)\
        .maybe_single()\
        .execute()
    if not result.data:
        # Return defaults
        return OrgConsentResponse(
            organization_id=organization_id,
            allow_ai_learning=False,
            allow_external_agents=False,
get_supabase	
<function get_supabase at 0x7fc61eb409a0>
organization_id	
"3cbf4dbe-c5a4-4253-b72b-6b89a15859ab"
request	

{
10 items
}
result	
None
supabase	
<supabase._sync.client.Client object at 0x7fc615c57a50>
user_id	
"94e02b27-3523-42ff-a0c2-858dd8e77f85"

Show More
Called from: slowapi/extension.py in async_wrapper

Show 16 more frames

/app/core/tracing.py in dispatch at line 54
In App

Called from: starlette/middleware/base.py in __call__

Show 9 more frames


Breadcrumbs



Exception - This event
error
Feb 3, 12:28:07.596 PM UTC
AttributeError: 'NoneType' object has no attribute 'data'
uvicorn.access
info
Feb 3, 12:28:07.561 PM UTC
100.64.0.2:25606 - "GET /api/v1/consent/organization HTTP/1.1" 500
core.tracing
error
Feb 3, 12:28:07.550 PM UTC
❌ [ef8afc83] GET /api/v1/consent/organization FAILED after 202.4ms: 'NoneType' object has no attribute 'data'

{
asctime: 2026-02-03 12:28:07,550
}
Httplib
warning
Feb 3, 12:28:07.550 PM UTC
https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/organization_consents

{
7 items
}
httpx
info
Feb 3, 12:28:07.548 PM UTC
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/organization_consents?select=%2A&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 406 Not Acceptable"

{
asctime: 2026-02-03 12:28:07,548
}

View 9 more

Logs
info

Feb 3, 12:28:32.555 PM
100.64.0.2:15554 - "GET /api/v1/consent/organization HTTP/1.1" 200
info

Feb 3, 12:28:32.555 PM
100.64.0.4:35678 - "GET /api/v1/consent/report HTTP/1.1" 200
info

Feb 3, 12:28:32.554 PM
✅ [d52b9279] GET /api/v1/consent/organization → 200 (662.7ms)
info

Feb 3, 12:28:32.553 PM
✅ [83c4fdfe] GET /api/v1/consent/report → 200 (663.0ms)
info

Feb 3, 12:28:32.551 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/organization_consents?select=%2A&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"

View more

Trace Preview
View Full Trace
One other issue appears in the same trace.

❌ [ef8afc83] GET /api/v1/consent/organization FAILED after 202.4ms: 'NoneType' object has no attribute 'data'
/api/v1/consent/organization
0.00ms1.00s2.00s3.00s4.00s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s
1 hidden span, 6 hidden issues

Error
—
❌ [55ba930b] GET /api/v1/consent/organization FAILED after 172.5ms: 'NoneType' object has no attribute 'data'

Error
—
'NoneType' object has no attribute 'data' AttributeError /app/api/v1/consent.py get_org_consent /api/v1/consent/organization

Error
—
❌ [ef8afc83] GET /api/v1/consent/organization FAILED after 202.4ms: 'NoneType' object has no attribute 'data'

Error
—
'NoneType' object has no attribute 'data' AttributeError /app/api/v1/consent.py get_org_consent /api/v1/consent/organization

HTTP Request


GET
/api/v1/consent/organization
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
sentry-environment=vercel-production,sentry-release=bdd9a66b6c31d8ee927e3f112a0714593796b1b2,sentry-public_key=18f4a279a98e4442868e3cd724ead3a2,sentry-trace_id=ed56ad230ef94b7baa13f9adab5b6e8b,sentry-org_id=[Filtered],sentry-sampled=true,sentry-sample_rand=0.171815840514279,sentry-sample_rate=1
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
no
level
level
error
mechanism
mechanism
starlette
release
release
bdd9a66b6c31
runtime
runtime
CPython 3.11.14
runtime.name
name
CPython
server_name
server_name
8ba3ae0a2f13
transaction
transaction
/api/v1/consent/organization
url
url
http://axial-production-1503.up.railway.app/api/v1/consent/organization

Contexts
User
Geography
Ashburn, United States (US)
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
a54b7002ddd699c5
Span ID
bfa499735ebc7691
Status
internal_error
Trace ID
ed56ad230ef94b7baa13f9adab5b6e8b

Additional Data


sys.argv	

[
6 items
]

Packages

SDK

Event Grouping Information

❌ [ef8afc83] GET /api/v1/consent/organization FAILED after 202.4ms: 'NoneType' object has no attribute 'data'
Events (total)
Users (30d)
Level: Error
/api/v1/consent/organization
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
100%
/api/v1/consent/organization
url
100%
http://axial-production-1503.up.railway.app/api/v1/consent/organization
release
100%
bdd9a66b6c31
environment
100%
production
View all tags and feature flags

Events
in this issue
First
Latest
Recommended
ID: 2e83c3c0
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
bdd9a66b6c31
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
http://axial-production-1503.up.railway.app/api/v1/consent/organization
Trace: Trace ID
ed56ad230ef94b7baa13f9adab5b6e8b

Message
❌ [ef8afc83] GET /api/v1/consent/organization FAILED after 202.4ms: 'NoneType' object has no attribute 'data'

Breadcrumbs



Message - This event
error
Feb 3, 12:28:07.551 PM UTC
❌ [ef8afc83] GET /api/v1/consent/organization FAILED after 202.4ms: 'NoneType' object has no attribute 'data'
Httplib
warning
Feb 3, 12:28:07.550 PM UTC
https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/organization_consents

{
7 items
}
httpx
info
Feb 3, 12:28:07.548 PM UTC
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/organization_consents?select=%2A&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 406 Not Acceptable"

{
asctime: 2026-02-03 12:28:07,548
}
Httplib
info
Feb 3, 12:28:07.504 PM UTC
https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams

{
7 items
}
httpx
info
Feb 3, 12:28:07.502 PM UTC
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams?select=id%2Cname%2Cslug%2Cowner_id%2Ccreated_at%2Cplan&id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"

{
asctime: 2026-02-03 12:28:07,502
}

View 7 more

Logs
info

Feb 3, 12:28:32.555 PM
100.64.0.2:15554 - "GET /api/v1/consent/organization HTTP/1.1" 200
info

Feb 3, 12:28:32.555 PM
100.64.0.4:35678 - "GET /api/v1/consent/report HTTP/1.1" 200
info

Feb 3, 12:28:32.554 PM
✅ [d52b9279] GET /api/v1/consent/organization → 200 (662.7ms)
info

Feb 3, 12:28:32.553 PM
✅ [83c4fdfe] GET /api/v1/consent/report → 200 (663.0ms)
info

Feb 3, 12:28:32.551 PM
HTTP Request: GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/organization_consents?select=%2A&organization_id=eq.3cbf4dbe-c5a4-4253-b72b-6b89a15859ab "HTTP/2 200 OK"

View more

Trace Preview
View Full Trace
One other issue appears in the same trace.

AttributeError/api/v1/consent/organization
'NoneType' object has no attribute 'data'
0.00ms5.00s10.00s15.00s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s0s
82 hidden spans

12

navigation
—
/dashboard/settings/consent
2.46s

5

http.server
—
/api/v1/consent/organization
714.66ms

5

http.server
—
/api/v1/consent/organization
225.13ms

5

http.server
—
/api/v1/consent/organization
265.26ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
30.99ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
35.55ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/team_members
41.53ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/teams
34.11ms

http.client
—
GET https://jxvcxmqqxwnracluelwq.supabase.co/rest/v1/organization_consents
42.13ms

7

http.server
—
/api/v1/consent/organization
298.12ms

5

http.server
—
/api/v1/consent/organization
180.74ms

http.server
—
http://*/api/v1/scopes
5.34ms
35 hidden spans

HTTP Request


GET
/api/v1/consent/organization
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
sentry-environment=vercel-production,sentry-release=bdd9a66b6c31d8ee927e3f112a0714593796b1b2,sentry-public_key=18f4a279a98e4442868e3cd724ead3a2,sentry-trace_id=ed56ad230ef94b7baa13f9adab5b6e8b,sentry-org_id=[Filtered],sentry-sampled=true,sentry-sample_rand=0.171815840514279,sentry-sample_rate=1
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
core.tracing
release
release
bdd9a66b6c31
runtime
runtime
CPython 3.11.14
runtime.name
name
CPython
server_name
server_name
8ba3ae0a2f13
transaction
transaction
/api/v1/consent/organization
url
url
http://axial-production-1503.up.railway.app/api/v1/consent/organization

Contexts
User
Geography
Ashburn, United States (US)
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
a54b7002ddd699c5
Span ID
bfa499735ebc7691
Status
unknown
Trace ID
ed56ad230ef94b7baa13f9adab5b6e8b

Additional Data


asctime	
2026-02-03 12:28:07,550
sys.argv	

[
6 items
]

Packages

SDK

Event Grouping Information


/api/py/consent/organization:1  Failed to load resource: the server responded with a status of 500 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 500 /consent/organization: Request failed with status code 500
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
/api/py/consent/organization:1  Failed to load resource: the server responded with a status of 500 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 500 /consent/organization: Request failed with status code 500
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
/api/py/consent/organization:1  Failed to load resource: the server responded with a status of 500 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 500 /consent/organization: Request failed with status code 500
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
/api/py/scopes:1  Failed to load resource: the server responded with a status of 404 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 404 /scopes: Request failed with status code 404
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
/api/py/scopes:1  Failed to load resource: the server responded with a status of 404 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 404 /scopes: Request failed with status code 404
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
/api/py/scopes:1  Failed to load resource: the server responded with a status of 404 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 404 /scopes: Request failed with status code 404
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
/api/py/scopes:1  Failed to load resource: the server responded with a status of 404 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 404 /scopes: Request failed with status code 404
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
23c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 Warning: Missing `Description` or `aria-describedby={undefined}` for {DialogContent}.
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this warning
/api/py/scopes:1  Failed to load resource: the server responded with a status of 404 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 404 /scopes: Request failed with status code 404
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
/api/py/scopes:1  Failed to load resource: the server responded with a status of 404 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 404 /scopes: Request failed with status code 404
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
/api/py/scopes:1  Failed to load resource: the server responded with a status of 404 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 404 /scopes: Request failed with status code 404
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
/api/py/scopes:1  Failed to load resource: the server responded with a status of 404 ()Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ 404 /scopes: Request failed with status code 404
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ ERR /documents: canceled
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 ❌ ERR /conversations: canceled
(anonymous) @ 3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10Understand this error
3c99b164b18a6af7.js?dpl=dpl_ArfwVp2pvrhW3BFQGx1amhCNMqi2:10 🔔 GlobalProgress: Realtime connected