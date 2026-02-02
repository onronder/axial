100

Critical

langchain-community

Affected by 5 CVEs: last detected 3 minutes ago

New
Dependency
TL;DR

langchain-community is affected by 5 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "Potential server-side request forgery (SSRF)", "Unsafe deserialization can lead to remote code execution" and "Accidental exposure of sensitive info possible".

How do I fix it?

In order to fix all of these vulnerabilities, update langchain-community in axial to 0.3.27. In order to solve only the critical issues, update to 0.0.28 or upgrade one at a time below.

5 unique known vulnerabilities found

CVE-2025-2828
Critical

This is what the package maintainer tells us about this finding

A Server-Side Request Forgery (SSRF) vulnerability exists in the RequestsToolkit component of the langchain-community package (specifically, langchain_community.agent_toolkits.openapi.toolkit.RequestsToolkit) in langchain-ai/langchain version 0.0.27. This vulnerability occurs because the toolkit does not enforce restrictions on requests to remote internet addresses, allowing it to also access local addresses. As a result, an attacker could exploit this flaw to perform port scans, access local services, retrieve instance metadata from cloud environments (e.g., Azure, AWS), and interact with servers on the local network. This issue has been fixed in version 0.0.28.

External links with more info
Official NVD advisory
CVE-2024-5998
High

This is what the package maintainer tells us about this finding

A vulnerability in the FAISS.deserialize_from_bytes function of langchain-ai/langchain allows for pickle deserialization of untrusted data. This can lead to the execution of arbitrary commands via the os.system function. The issue affects the latest version of the product.

External links with more info
Official NVD advisory
CVE-2024-3095
High

This is what the package maintainer tells us about this finding

A Server-Side Request Forgery (SSRF) vulnerability exists in the Web Research Retriever component of langchain-ai/langchain version 0.1.5. The vulnerability arises because the Web Research Retriever does not restrict requests to remote internet addresses, allowing it to reach local addresses. This flaw enables attackers to execute port scans, access local services, and in some scenarios, read instance metadata from cloud environments. The vulnerability is particularly concerning as it can be exploited to abuse the Web Explorer server as a proxy for web attacks on third parties and interact with servers in the local network, including reading their response data. This could potentially lead to arbitrary code execution, depending on the nature of the local services. The vulnerability is limited to GET requests, as POST requests are not possible, but the impact on confidentiality, integrity, and availability is significant due to the potential for stolen credentials and state-changing interactions with internal APIs.

External links with more info
Official NVD advisory
CVE-2025-6984
High

This is what the package maintainer tells us about this finding

The langchain-ai/langchain project, specifically the EverNoteLoader component, is vulnerable to XML External Entity (XXE) attacks due to insecure XML parsing. The affected version is 0.3.63. The vulnerability arises from the use of etree.iterparse() without disabling external entity references, which can lead to sensitive information disclosure. An attacker could exploit this by crafting a malicious XML payload that references local files, potentially exposing sensitive data such as /etc/passwd.

External links with more info
Official NVD advisory
CVE-2024-2965
Medium

This is what the package maintainer tells us about this finding

A Denial-of-Service (DoS) vulnerability exists in the SitemapLoader class of the langchain-ai/langchain repository, affecting all versions. The parse_sitemap method, responsible for parsing sitemaps and extracting URLs, lacks a mechanism to prevent infinite recursion when a sitemap URL refers to the current sitemap itself. This oversight allows for the possibility of an infinite loop, leading to a crash by exceeding the maximum recursion depth in Python. This vulnerability can be exploited to occupy server socket/port resources and crash the Python process, impacting the availability of services relying on this functionality.

External links with more info
Official NVD advisory
Education

Watch video on Server-Side Request Forgery (SSRF) and more

Subissues

5
Subissue
Fix
backend
axial
CVE-2025-2828

Critical
requirements.txt

View reachability analysis
Upgraded: Exploit available on Github

0.0.9 => 0.0.28

CVE-2024-5998

High
requirements.txt

View reachability analysis
0.0.9 => 0.2.4

CVE-2024-3095

High
requirements.txt

View reachability analysis
0.0.9 => 0.2.9

CVE-2025-6984

High
requirements.txt

View reachability analysis
0.0.9 => 0.3.27

CVE-2024-2965

Medium
requirements.txt

View reachability analysis
0.0.9 => 0.2.5




langchain
2 open subissues

99

Critical

langchain

Affected by 2 CVEs: last detected 3 minutes ago

New
Dependency
TL;DR

langchain is affected by 2 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "SQL injection attack possible", "Attacker can inject extra unwanted content or code" and "DoS possible due to infinite loop".

How do I fix it?

In order to fix all of these vulnerabilities, update langchain in axial to 0.2.5. In order to solve only the critical issues, update to 0.2.0 or upgrade one at a time below.

2 unique known vulnerabilities found

CVE-2024-8309
Critical

This is what the package maintainer tells us about this finding

A vulnerability in the GraphCypherQAChain class of langchain-ai/langchain version 0.2.5 allows for SQL injection through prompt injection. This vulnerability can lead to unauthorized data manipulation, data exfiltration, denial of service (DoS) by deleting all data, breaches in multi-tenant security environments, and data integrity issues. Attackers can create, update, or delete nodes and relationships without proper authorization, extract sensitive data, disrupt services, access data across different tenants, and compromise the integrity of the database.

External links with more info
Official NVD advisory
CVE-2024-2965
Medium

This is what the package maintainer tells us about this finding

A Denial-of-Service (DoS) vulnerability exists in the SitemapLoader class of the langchain-ai/langchain repository, affecting all versions. The parse_sitemap method, responsible for parsing sitemaps and extracting URLs, lacks a mechanism to prevent infinite recursion when a sitemap URL refers to the current sitemap itself. This oversight allows for the possibility of an infinite loop, leading to a crash by exceeding the maximum recursion depth in Python. This vulnerability can be exploited to occupy server socket/port resources and crash the Python process, impacting the availability of services relying on this functionality.

External links with more info
Official NVD advisory
Education

Watch video on Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')

Subissues

2
Subissue
Fix
backend
axial
CVE-2024-8309

Critical
requirements.txt

View reachability analysis
Upgraded: Exploit available on Github

0.1.0 => 0.2.0

CVE-2024-2965

Medium
requirements.txt

View reachability analysis
0.1.0 => 0.2.5



Potential SQL injection via string-based query concatenation
2 open subissues

95

Critical

Potential SQL injection via string-based query concatenation

We found 2 issues: last detected 26 seconds ago

New
SAST
TL;DR

SQL injection might be possible in these locations, especially if the strings being concatenated are controlled via user input. 

How do I fix it?

If possible, rebuild the query to use prepared statements or an ORM. If that is not possible, make sure the user input is verified or sanitized. As an added layer of protection, we also recommend installing a WAF that blocks SQL injection attacks.
More information

Education

Watch video on Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')

Subissues

2
Subissue
backend
axial
backend/services/usage.py

Critical
Line 170 in usage.py

WHERE user_id = '{str(user_id)}'
View code analysis
Upgraded: AI assessed finding as easily exploitable

backend/worker/tasks.py

Critical
Line 842 in tasks.py

context=f"replace doc_id={existing_doc_id}",
View code analysis
Upgraded: AI assessed finding as easily exploitable


pillow
3 open subissues

94

Critical

pillow

Affected by 3 CVEs: last detected 4 minutes ago

New
Dependency
TL;DR

pillow is affected by 3 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "Attacker can trigger memory corruption leading to crash or RCE" and "Attacker can inject own code to run".

How do I fix it?

In order to fix all of these vulnerabilities, update pillow in axial to 10.3.0 or upgrade one at a time below.

3 unique known vulnerabilities found

CVE-2023-4863
Critical

This is what the package maintainer tells us about this finding

Heap buffer overflow in libwebp in Google Chrome prior to 116.0.5845.187 and libwebp 1.3.2 allowed a remote attacker to perform an out of bounds memory write via a crafted HTML page. (Chromium security severity: Critical)

External links with more info
Official NVD advisory
CVE-2023-50447
High

This is what the package maintainer tells us about this finding

Pillow through 10.1.0 allows PIL.ImageMath.eval Arbitrary Code Execution via the environment parameter, a different vulnerability than CVE-2022-22817 (which was about the expression parameter).

External links with more info
Official NVD advisory
CVE-2024-28219
Medium

This is what the package maintainer tells us about this finding

In _imagingcms.c in Pillow before 10.3.0, a buffer overflow exists because strcpy is used instead of strncpy.

External links with more info
Official NVD advisory
Education

Watch video on Out-of-bounds Write and more

Subissues

3
Subissue
Fix
backend
axial
CVE-2023-4863

Critical
backend/requirements.txt

View reachability analysis
Upgraded: Exploit available on Github

10.0.0 => 10.0.1

CVE-2023-50447

High
backend/requirements.txt

View reachability analysis
10.0.0 => 10.2.0

CVE-2024-28219

Medium
backend/requirements.txt

View reachability analysis
10.0.0 => 10.3.0


unstructured
6 open subissues

87

High Risk

unstructured

Affected by 5 CVEs: last detected 4 minutes ago

New
Dependency
TL;DR

unstructured is affected by 5 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "XXE attack may allow sensitive info exposure", "Package gives access to restricted resources" and "Sensitive information exposed in error messages".

How do I fix it?

In order to fix all of these vulnerabilities, update unstructured in axial to 0.16.20 or upgrade one at a time below.

5 unique known vulnerabilities found

AIKIDO-2024-10110
High

Aikido TLDR

Affected versions of the package are vulnerable to XML external entity injection (XXE). The vulnerable function parses XML and resolves any external entities within the document.

Does this affect me?

You are affected if you are using a version that falls within the vulnerable range and you use the `get_leaf_elements(...)`, `partition_xml(...)`, or `partition(...)` functions in your application.

Aikido recommends

Upgrade `unstructured` to the patch version.

AIKIDO-2025-10078
Medium

Aikido TLDR

Affected versions of this package may expose resources to an unintended scope. Specifically, when processing files that support an `include` functionality, such as `rst` and `org` files, an attacker may be able to partition arbitrary local files, incorporating their contents into the processed output. This could lead to unauthorized disclosure of sensitive information or unintended file exposure.

Does this affect me?

You are affected if you are using a version that falls within the vulnerable range.

Aikido recommends

Upgrade the `unstructured` library to the patch version.

CVE-2024-46455
Medium

This is what the package maintainer tells us about this finding

unstructured v.0.14.2 and before is vulnerable to XML External Entity (XXE) via the XMLParser.

External links with more info
Official NVD advisory
AIKIDO-2024-10150
Medium

Aikido TLDR

Affected versions of `unstructured` do not mark some sensitive fields, which means they may end up in logging systems.

Does this affect me?

You are affected if you use a vulnerable version of `unstructured`.

Aikido recommends

Upgrade `unstructured` to a patch version.

AIKIDO-2024-10127
Medium

Aikido TLDR

Affected versions of the `unstructured` package do not remove the root handlers in the ingest logger, which may lead to secrets being exposed when `unstructured` is used in a Google Colab notebook.

Does this affect me?

You are affected if you use a vulnerable version of `unstructured`.

Aikido recommends

Upgrade `unstructured` to a patch version.

Education

Watch video on Improper Restriction of XML External Entity Reference and more

Subissues

6
Subissue
Fix
backend
axial
AIKIDO-2024-10110 | CVE-2024-46455

High
backend/requirements.txt

View reachability analysis
0.11.0 => 0.14.3

AIKIDO-2024-10110 | CVE-2024-46455

High
requirements.txt

View reachability analysis
0.11.0 => 0.14.3

AIKIDO-2025-10078

Medium
backend/requirements.txt

View reachability analysis
0.11.0 => 0.16.20

CVE-2024-46455

Medium
backend/requirements.txt

View reachability analysis
0.11.0 => 0.14.3

AIKIDO-2024-10150

Medium
backend/requirements.txt

View reachability analysis
0.11.0 => 0.14.8

AIKIDO-2024-10127

Medium
backend/requirements.txt

View reachability analysis
0.11.0 => 0.14.4

4 ignored items


langchain-core
2 open subissues

83

High Risk

langchain-core

Affected by 2 CVEs: last detected 5 minutes ago

New
Dependency
TL;DR

langchain-core is affected by 2 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "Unsafe deserialization can lead to remote code execution" and "Attacker can abuse improper element neutralization in templates".

How do I fix it?

In order to fix all of these vulnerabilities, update langchain-core in axial to 0.3.81 or upgrade one at a time below.

2 unique known vulnerabilities found

CVE-2025-68664
High

This is what the package maintainer tells us about this finding

LangChain is a framework for building agents and LLM-powered applications. Prior to versions 0.3.81 and 1.2.5, a serialization injection vulnerability exists in LangChain's dumps() and dumpd() functions. The functions do not escape dictionaries with 'lc' keys when serializing free-form dictionaries. The 'lc' key is used internally by LangChain to mark serialized objects. When user-controlled data contains this key structure, it is treated as a legitimate LangChain object during deserialization rather than plain user data. This issue has been patched in versions 0.3.81 and 1.2.5.

External links with more info
Official GitHub advisory
Official NVD advisory
CVE-2025-65106
High

This is what the package maintainer tells us about this finding

LangChain is a framework for building agents and LLM-powered applications. From versions 0.3.79 and prior and 1.0.0 to 1.0.6, a template injection vulnerability exists in LangChain's prompt template system that allows attackers to access Python object internals through template syntax. This vulnerability affects applications that accept untrusted template strings (not just template variables) in ChatPromptTemplate and related prompt template classes. This issue has been patched in versions 0.3.80 and 1.0.7.

External links with more info
Official GitHub advisory
Official NVD advisory
Education

Watch video on Deserialization of Untrusted Data

Subissues

2
Subissue
Fix
backend
axial
CVE-2025-68664

High
requirements.txt

View reachability analysis
Upgraded: Exploit available on Github

0.1.53 => 0.3.81

CVE-2025-65106

High
requirements.txt

View reachability analysis
0.1.53 => 0.3.80



Secret leaked in frontend-new/test-results/.playwright-artifacts-1/traces/resources/2632e2fb34dcbb6ba5622b128ddf6552d5a04678.json
7 open subissues

80

High Risk

13 exposed secrets

We found 7 issues: first detected 3 minutes ago

New
Secrets
TL;DR

We detected some exposed secrets in the git history of axial. The secrets were found in logs2.har, frontend-new/test-results/.playwright-artifacts-1/traces/fdb1eaf298e0e81df62d-ded51752b22b8dd19921-retry1.network, frontend-new/test-results/.playwright-artifacts-1/traces/fdb1eaf298e0e81df62d-ded51752b22b8dd19921-retry1-pwnetcopy-1.network and frontend-new/test-results/.playwright-artifacts-1/traces/resources/2632e2fb34dcbb6ba5622b128ddf6552d5a04678.json

Show more
How do I fix it?

If this API key is harmless, you can ignore this issue. If not, we would advise to move the secret out of the git repository by either injecting it via the environment or even better, by using a tool such as AWS Secrets Manager to inject the secrets at run-time. After that, it should be possible to invalidate the current secret and regenerate a new one.

Note: Exposed secrets need to be marked as resolved manually. Even after removal it will still be available in the git history of your repository. That means it could still leak if someone has access to your source code.

Subissues

7
Subissue
Author
backend
axial
***************(...)***************p2-c

High
Line 31802 in logs2.har

View commit
onronder

********9yZC

High
Line 48342 in logs2.har

View commit
onronder

********9yZC

Medium
Line 133 in frontend-new/test-results/.playwright-artifacts-1/traces/fdb1eaf298e0e81df62d-ded51752b22b8dd19921-retry1.network

View commit
Downgraded: Secret located in deleted file

onronder

***************(...)***************p2-c

Medium
Line 70 in frontend-new/test-results/.playwright-artifacts-1/traces/fdb1eaf298e0e81df62d-ded51752b22b8dd19921-retry1.network

View commit
Downgraded: Secret located in deleted file

onronder

***************(...)***************p2-c

Medium
Line 70 in frontend-new/test-results/.playwright-artifacts-1/traces/fdb1eaf298e0e81df62d-ded51752b22b8dd19921-retry1-pwnetcopy-1.network

View commit
Downgraded: Secret located in deleted file

onronder

********9yZC

Medium
Line 133 in frontend-new/test-results/.playwright-artifacts-1/traces/fdb1eaf298e0e81df62d-ded51752b22b8dd19921-retry1-pwnetcopy-1.network

View commit
Downgraded: Secret located in deleted file

onronder

********9yZC

Medium
Line 1 in frontend-new/test-results/.playwright-artifacts-1/traces/resources/2632e2fb34dcbb6ba5622b128ddf6552d5a04678.json

View commit
Downgraded: Secret located in deleted file

onronder

6 ignored items


Next.js
4 open subissues

75

High Risk

Next.js

Affected by 4 CVEs: last detected 6 minutes ago

New
Dependency
TL;DR

Next.js is affected by 4 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "Attacker can trigger DOS-attack" and "Unsafe deserialization can lead to remote code execution".

Does this affect me?

We might be able to determine if this CVE is unable to affect you if you answer the below questions. This questionnaire is generated based on AIKIDO-2026-10095

We use React Server Components with the App Router

Yes
No
Not sure
How do I fix it?

In order to fix all of these vulnerabilities, update Next.js in axial to 16.1.5 or upgrade one at a time below.

4 unique known vulnerabilities found

GHSA-h25m-26qc-wcjf
High

This is what the package maintainer tells us about this finding

A vulnerability affects certain React Server Components packages for versions 19.0.x, 19.1.x, and 19.2.x and frameworks that use the affected packages, including Next.js 13.x, 14.x, 15.x, and 16.x using the App Router. The issue is tracked upstream as CVE-2026-23864.

A specially crafted HTTP request can be sent to any App Router Server Function endpoint that, when deserialized, may trigger excessive CPU usage, out-of-memory exceptions, or server crashes. This can result in denial of service in unpatched environments.

External links with more info
Official GitHub advisory
Official GitHub advisory
Official NVD advisory
AIKIDO-2026-10095
Low

Aikido TLDR

Affected versions of the `react-server-dom-webpack`, `react-server-dom-parcel`, and `react-server-dom-turbopack` packages and frameworks that use the affected packages, including `Next.js` 13.x, 14.x, 15.x, and 16.x using the App Router are vulnerable to multiple denial of service (DoS) issues. The previously applied DoS mitigations were incomplete, allowing specially crafted HTTP requests to Server Function endpoints to trigger server crashes, out-of-memory conditions, or excessive CPU usage, depending on the code path and application configuration. Applications that do not use React Server Components or server-side React functionality are not affected.

Does this affect me?

You are affected only if you are using a version within the vulnerable range and your application uses React Server Components. Applications that do not run React code on the server, or that do not use a framework, bundler, or bundler plugin supporting React Server Components, are not affected.

Aikido recommends

Upgrade the `next` library to the patch version.

CVE-2025-59472
Low

This is what the package maintainer tells us about this finding

A denial of service vulnerability exists in Next.js versions with Partial Prerendering (PPR) enabled when running in minimal mode. The PPR resume endpoint accepts unauthenticated POST requests with the Next-Resume: 1 header and processes attacker-controlled postponed state data. Two closely related vulnerabilities allow an attacker to crash the server process through memory exhaustion:

Unbounded request body buffering: The server buffers the entire POST request body into memory using Buffer.concat() without enforcing any size limit, allowing arbitrarily large payloads to exhaust available memory.

Unbounded decompression (zipbomb): The resume data cache is decompressed using inflateSync() without limiting the decompressed output size. A small compressed payload can expand to hundreds of megabytes or gigabytes, causing memory exhaustion.

Both attack vectors result in a fatal V8 out-of-memory error (FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory) causing the Node.js process to terminate. The zipbomb variant is particularly dangerous as it can bypass reverse proxy request size limits while still causing large memory allocation on the server.

To be affected you must have an application running with experimental.ppr: true or cacheComponents: true configured along with the NEXT_PRIVATE_MINIMAL_MODE=1 environment variable.

Strongly consider upgrading to 15.6.0-canary.61 or 16.1.5 to reduce risk and prevent availability issues in Next applications.

External links with more info
Official GitHub advisory
Official NVD advisory
CVE-2025-59471
Low

This is what the package maintainer tells us about this finding

A denial of service vulnerability exists in self-hosted Next.js applications that have remotePatterns configured for the Image Optimizer. The image optimization endpoint (/_next/image) loads external images entirely into memory without enforcing a maximum size limit, allowing an attacker to cause out-of-memory conditions by requesting optimization of arbitrarily large images. This vulnerability requires that remotePatterns is configured to allow image optimization from external domains and that the attacker can serve or control a large image on an allowed domain.

Strongly consider upgrading to 15.5.10 or 16.1.5 to reduce risk and prevent availability issues in Next applications.

External links with more info
Official GitHub advisory
Official NVD advisory
Education

Watch video on Deserialization of Untrusted Data

Subissues

4
Subissue
Fix
backend
axial
GHSA-h25m-26qc-wcjf

High
frontend-new/package-lock.json

View reachability analysis
16.0.10 => 16.0.11

AIKIDO-2026-10095 | CVE-2026-23864

Low
frontend-new/package-lock.json

View reachability analysis
Downgraded: Only impacts performance, not security

16.0.10 => 16.0.11

CVE-2025-59472

Low
frontend-new/package-lock.json

View reachability analysis
Downgraded: Only impacts performance, not security

16.0.10 => 16.1.5

CVE-2025-59471

Low
frontend-new/package-lock.json

View reachability analysis
Downgraded: Only impacts performance, not security

16.0.10 => 16.1.5



starlette
4 open subissues

75

High Risk

starlette

Affected by 2 CVEs: last detected 6 minutes ago

New
Dependency
TL;DR

starlette is affected by 2 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "Attacker can trigger DOS-attack".

How do I fix it?

In order to fix all of these vulnerabilities, update starlette in axial to 0.47.2 or upgrade one at a time below.

2 unique known vulnerabilities found

CVE-2024-47874
High

This is what the package maintainer tells us about this finding

Starlette is an Asynchronous Server Gateway Interface (ASGI) framework/toolkit. Prior to version 0.40.0, Starlette treats multipart/form-data parts without a filename as text form fields and buffers those in byte strings with no size limit. This allows an attacker to upload arbitrary large form fields and cause Starlette to both slow down significantly due to excessive memory allocations and copy operations, and also consume more and more memory until the server starts swapping and grinds to a halt, or the OS terminates the server process with an OOM error. Uploading multiple such requests in parallel may be enough to render a service practically unusable, even if reasonable request size limits are enforced by a reverse proxy in front of Starlette. This Denial of service (DoS) vulnerability affects all applications built with Starlette (or FastAPI) accepting form requests. Verison 0.40.0 fixes this issue.

External links with more info
Official GitHub advisory
Official NVD advisory
CVE-2025-54121
Medium

This is what the package maintainer tells us about this finding

Starlette is a lightweight ASGI (Asynchronous Server Gateway Interface) framework/toolkit, designed for building async web services in Python. In versions 0.47.1 and below, when parsing a multi-part form with large files (greater than the default max spool size) starlette will block the main thread to roll the file over to disk. This blocks the event thread which means the application can't accept new connections. The UploadFile code has a minor bug where instead of just checking for self._in_memory, the logic should also check if the additional bytes will cause a rollover. The vulnerability is fixed in version 0.47.2.

External links with more info
Official GitHub advisory
Official NVD advisory
Education

Watch video on Allocation of Resources Without Limits or Throttling

Subissues

4
Subissue
Fix
backend
axial
CVE-2024-47874

High
backend/requirements.txt

View reachability analysis
0.36.3 => 0.40.0

CVE-2024-47874

High
requirements.txt

View reachability analysis
0.36.3 => 0.40.0

CVE-2025-54121

Medium
backend/requirements.txt

View reachability analysis
0.36.3 => 0.47.2

CVE-2025-54121

Medium
requirements.txt

View reachability analysis
0.36.3 => 0.47.2



pypdf
16 open subissues

75

High Risk

pypdf

Affected by 8 CVEs: last detected 7 minutes ago

New
Dependency
TL;DR

pypdf is affected by 8 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "Attacker can trigger DOS-attack", "Attacker can trigger DOS via infinite loop" and "Attacker can trigger DOS-attack via regex".

How do I fix it?

In order to fix all of these vulnerabilities, update pypdf in axial to 6.6.2 or upgrade one at a time below.

8 unique known vulnerabilities found

CVE-2025-62708
High

This is what the package maintainer tells us about this finding

pypdf is a free and open-source pure-python PDF library. Prior to version 6.1.3, an attacker who uses this vulnerability can craft a PDF which leads to large memory usage. This requires parsing the content stream of a page using the LZWDecode filter. This has been fixed in pypdf version 6.1.3.

External links with more info
Official GitHub advisory
Official NVD advisory
CVE-2025-62707
High

This is what the package maintainer tells us about this finding

pypdf is a free and open-source pure-python PDF library. Prior to version 6.1.3, an attacker who uses this vulnerability can craft a PDF which leads to an infinite loop. This requires parsing the content stream of a page which has an inline image using the DCTDecode filter. This has been fixed in pypdf version 6.1.3.

External links with more info
Official GitHub advisory
Official NVD advisory
CVE-2025-55197
High

This is what the package maintainer tells us about this finding

pypdf is a free and open-source pure-python PDF library. Prior to version 6.0.0, an attacker can craft a PDF which leads to the RAM being exhausted. This requires just reading the file if a series of FlateDecode filters is used on a malicious cross-reference stream. Other content streams are affected on explicit access. This issue has been fixed in 6.0.0. If an update is not possible, a workaround involves including the fixed code from pypdf.filters.decompress into the existing filters file.

External links with more info
Official GitHub advisory
Official NVD advisory
CVE-2026-24688
Medium

This is what the package maintainer tells us about this finding

pypdf is a free and open-source pure-python PDF library. An attacker who uses an infinite loop vulnerability that is present in versions prior to 6.6.2 can craft a PDF which leads to an infinite loop. This requires accessing the outlines/bookmarks. This has been fixed in pypdf 6.6.2. If projects cannot upgrade yet, consider applying the changes from PR #3610 manually.

External links with more info
Official GitHub advisory
Official NVD advisory
CVE-2026-22691
Medium

This is what the package maintainer tells us about this finding

pypdf is a free and open-source pure-python PDF library. Prior to version 6.6.0, pypdf has possible long runtimes for malformed startxref. An attacker who uses this vulnerability can craft a PDF which leads to possibly long runtimes for invalid startxref entries. When rebuilding the cross-reference table, PDF files with lots of whitespace characters become problematic. Only the non-strict reading mode is affected. Only the non-strict reading mode is affected. This issue has been patched in version 6.6.0.

External links with more info
Official GitHub advisory
Official NVD advisory
CVE-2025-66019
Medium

This is what the package maintainer tells us about this finding

pypdf is a free and open-source pure-python PDF library. Prior to version 6.4.0, an attacker who uses this vulnerability can craft a PDF which leads to a memory usage of up to 1 GB per stream. This requires parsing the content stream of a page using the LZWDecode filter. This issue has been patched in version 6.4.0.

External links with more info
Official GitHub advisory
Official GitHub advisory
Official NVD advisory
CVE-2026-22690
Low

This is what the package maintainer tells us about this finding

pypdf is a free and open-source pure-python PDF library. Prior to version 6.6.0, pypdf has possible long runtimes for missing /Root object with large /Size values. An attacker who uses this vulnerability can craft a PDF which leads to possibly long runtimes for actually invalid files. This can be achieved by omitting the /Root entry in the trailer, while using a rather large /Size value. Only the non-strict reading mode is affected. This issue has been patched in version 6.6.0.

External links with more info
Official GitHub advisory
Official NVD advisory
AIKIDO-2025-10548
Low

Aikido TLDR

Affected versions of this package are vulnerable to denial of service due to full decompression of nested `FlateDecode` streams, allowing a small malicious PDF to expand to over 1 PB and exhaust system resources.

Does this affect me?

You are affected if you are using a version that falls within the vulnerable range.

Aikido recommends

Upgrade the `pypdf` library to the patch version.

Education

Watch video on Allocation of Resources Without Limits or Throttling and more

Subissues

16
Subissue
Fix
backend
axial
CVE-2025-62708

High
backend/requirements.txt

View reachability analysis
3.17.0 => 6.1.3

CVE-2025-62707

High
backend/requirements.txt

View reachability analysis
3.17.0 => 6.1.3

CVE-2025-55197

High
backend/requirements.txt

View reachability analysis
3.17.0 => 6.0.0

CVE-2025-62708

High
requirements.txt

View reachability analysis
4.1.0 => 6.1.3

CVE-2025-62707

High
requirements.txt

View reachability analysis
4.1.0 => 6.1.3

CVE-2025-55197

High
requirements.txt

View reachability analysis
4.1.0 => 6.0.0

CVE-2026-24688

Medium
backend/requirements.txt

View reachability analysis
Upgraded: Exploit available on Github

3.17.0 => 6.6.2

CVE-2026-24688

Medium
requirements.txt

View reachability analysis
Upgraded: Exploit available on Github

4.1.0 => 6.6.2

CVE-2026-22691

Medium
backend/requirements.txt

View reachability analysis
3.17.0 => 6.6.0

CVE-2025-66019

Medium
backend/requirements.txt

View reachability analysis
3.17.0 => 6.4.0

CVE-2026-22691

Medium
requirements.txt

View reachability analysis
4.1.0 => 6.6.0

CVE-2025-66019

Medium
requirements.txt

View reachability analysis
4.1.0 => 6.4.0

CVE-2026-22690

Low
backend/requirements.txt

View reachability analysis
Downgraded: Only impacts performance, not security

3.17.0 => 6.6.0

CVE-2026-22690

Low
requirements.txt

View reachability analysis
Downgraded: Only impacts performance, not security

4.1.0 => 6.6.0

AIKIDO-2025-10548 | CVE-2025-55197

Low
requirements.txt

View reachability analysis
Downgraded: Only impacts performance, not security

4.1.0 => 6.0.0

AIKIDO-2025-10548 | CVE-2025-55197

Low
backend/requirements.txt

View reachability analysis
Downgraded: Only impacts performance, not security

3.17.0 => 6.0.0


Potential file inclusion attack via reading file
2 open subissues

70

High Risk

Potential file inclusion attack via reading file

We found 2 issues: last detected 4 minutes ago

New
SAST
TL;DR

If an attacker can control the input leading into the ReadFile function, they might be able to read sensitive files and launch further attacks with that information.

How do I fix it?

Ignore this issue only after you've verified or sanitized the input going into this function. This issue is only relevant in the backend, not in the frontend! 

Education

Watch video on Relative Path Traversal

Subissues

2
Subissue
backend
axial
frontend-new/lib/help.ts

High
Line 64 in help.ts

const fullPath = path.join(helpDirectory, `${slug}.md`);
View code analysis
frontend-new/lib/help.ts

High
Line 70 in help.ts

const fileContents = fs.readFileSync(fullPath, 'utf8');
View code analysis
3 ignored items


Potential user input in HTTP request may allow SSRF attack
8 open subissues

65

Medium Risk

Potential user input in HTTP request may allow SSRF attack

We found 8 issues: last detected 51 seconds ago

New
SAST
TL;DR

If an attacker can control the URL input leading into this HTTP request, the attack might be able to perform an SSRF attack. This kind of attack is even more dangerous if the application returns the response of the request to the user. It could allow them to retrieve information from higher privileged services within the network (such as the metadata service, which is commonly available in cloud services, and could allow them to retrieve credentials).

Show more
How do I fix it?

If possible, only allow requests to allowlisting domains. If not, consult the article linked above to learn about other mitigating techniques such as disabling redirects, blocking private IPs and making sure private services have internal authentication. If you return data coming from the request to the user, validate the data before returning it to make sure you don't return random data.
More information

Show more
Education

Watch video on Server-Side Request Forgery (SSRF)

Subissues

8
Subissue
backend
axial
backend/connectors/microsoft.py

Medium
Line 440 in microsoft.py

url,
View code analysis
Upgraded: AI assessed finding as likely exploitable

backend/connectors/web.py

Medium
Line 1187 in web.py

response = requests.get(robots_url, timeout=(10, 30), headers=self.DEFAULT_HEADERS)
View code analysis
Upgraded: AI assessed finding as likely exploitable

agent/main.py

Medium
Line 53 in main.py

put_res = requests.put(signed_url, data=f, headers=put_headers, timeout=300)
View code analysis
backend/connectors/box.py

Medium
Line 256 in box.py

url,
View code analysis
backend/connectors/github.py

Medium
Line 439 in github.py

url,
View code analysis
tenancy_smoke.py

Medium
Line 38 in tenancy_smoke.py

put_res = requests.put(signed_url, data=content, headers=put_headers, timeout=60)
View code analysis
backend/connectors/notion.py

Low
Line 110 in notion.py

url=url,
View code analysis
Downgraded: AI assessed finding as somewhat hard to exploit

backend/connectors/dropbox.py

Low
Line 318 in dropbox.py

url,
View code analysis
Downgraded: AI assessed finding as hard to exploit


PyMuPDF
4 open subissues

65

Medium Risk

PyMuPDF

Affected by 2 CVEs: last detected 8 minutes ago

New
Dependency
TL;DR

PyMuPDF is affected by 2 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "Path traversal attack possible" and "Attacker can trigger DOS-attack".

How do I fix it?

In order to fix all of these vulnerabilities, update PyMuPDF in axial to 1.26.7 or upgrade one at a time below.

2 unique known vulnerabilities found

AIKIDO-2025-10959
Medium

Aikido TLDR

Affected versions of this package are vulnerable to Path Traversal because the `embedded_get` functionality does not properly sanitize the user-controlled path parameter. This allows an attacker to craft a path containing directory traversal sequences, potentially causing files to be written outside the intended working directory or to overwrite existing files. The issue is mitigated by introducing stricter path validation: by default, the command now refuses to write to an existing file or to any location outside the current directory. Writing outside these constraints is only possible when explicitly allowed via the `-output` option or the newly introduced `-unsafe` flag, making the security impact opt-in and explicit.

Does this affect me?

You are affected if you are using a version that falls within the vulnerable range.

Aikido recommends

Upgrade the `PyMuPDF` library to the patch version.

AIKIDO-2025-10028
Low

Aikido TLDR

Affected versions of this package are vulnerable to a crash when `samples_mv` is used after the original `Pixmap` has been deallocated. This flaw can be exploited by malicious actors to trigger a Denial of Service (DoS).

Does this affect me?

You are affected if you are using a version that falls within the vulnerable range.

Aikido recommends

Upgrade the `PyMuPDF` library to the patch version.

Education

Watch video on Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')

Subissues

4
Subissue
Fix
backend
axial
AIKIDO-2025-10959

Medium
requirements.txt

View reachability analysis
1.24.0 => 1.26.7

AIKIDO-2025-10959

Medium
backend/requirements.txt

View reachability analysis
1.23.0 => 1.26.7

AIKIDO-2025-10028

Low
requirements.txt

View reachability analysis
Downgraded: Only impacts performance, not security

1.24.0 => 1.25.2

AIKIDO-2025-10028

Low
backend/requirements.txt

View reachability analysis
Downgraded: Only impacts performance, not security

1.23.0 => 1.25.2


Docker container runs as default root user
2 open subissues

65

Medium Risk

Docker container runs as default root user

We found 2 issues: last detected 8 minutes ago

New
SAST
TL;DR

By default, containers are run with root privileges and also run as the root user inside the container. Running the app as root gives a hacker who was able to hack the application instant root access to the Docker host, which could help them to escalate a hack.

How do I fix it?

Add 'USER username' to the end of your file.

Subissues

2
Subissue
backend
axial
docker/backend.Dockerfile

Medium
Line 1 - 46 in backend.Dockerfile

FROM python:3.11-slim

# Install system dependencies for Unstructured (OCR, PDF, Magic)
# and ClamAV for Ghost Protocol malware scanning
...
# For lightweight development without ClamAV:
#   docker run --entrypoint uvicorn ... main:app --host 0.0.0.0 --port 8000
# Or set env var SKIP_CLAMAV=true in the startup script
CMD ["/start-with-clamav.sh"]
View code analysis
docker/frontend.Dockerfile

Medium
Line 1 - 20 in frontend.Dockerfile

FROM python:3.11-slim

WORKDIR /app

...
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--browser.gatherUsageStats=false", \
    "--theme.base=dark"]
View code analysis


Secret leaked in backend/debug_auth_request.py
1 open subissue

60

Medium Risk

Uncovered a JSON Web Token, which may lead to unauthorized access to web applications and sensitive user data.

We found 1 issue: first detected 6 minutes ago

New
Secrets
TL;DR

We detected secret *****sw5c in the git history of the axial repository. The secret was found in backend/debug_auth_request.py@ this commit ->

How do I fix it?

If this API key is harmless, you can ignore this issue. If not, we would advise to move the secret out of the git repository by either injecting it via the environment or even better, by using a tool such as AWS Secrets Manager to inject the secrets at run-time. After that, it should be possible to invalidate the current secret and regenerate a new one.

Note: Exposed secrets need to be marked as resolved manually. This secret was not detected in the latest version of your app, but in the git history of your repository. That means it could still leak if someone has access to your source code.

Subissues

1
Subissue
Author
backend
axial
***************(...)***************sw5c

Medium
Line 26 in backend/debug_auth_request.py

View commit
Downgraded: Secret located in deleted file

onronder

requests
2 open subissues

56

Medium Risk

requests

Affected by 2 CVEs: last detected 9 minutes ago

New
Dependency
TL;DR

requests is affected by 2 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "Attacker could gain access to user accounts".

How do I fix it?

In order to fix all of these vulnerabilities, update requests in axial to 2.32.4 or upgrade one at a time below.

2 unique known vulnerabilities found

CVE-2024-35195
Medium

This is what the package maintainer tells us about this finding

Requests is a HTTP library. Prior to 2.32.0, when making requests through a Requests Session, if the first request is made with verify=False to disable cert verification, all subsequent requests to the same host will continue to ignore cert verification regardless of changes to the value of verify. This behavior will continue for the lifecycle of the connection in the connection pool. This vulnerability is fixed in 2.32.0.

External links with more info
Official GitHub advisory
Official NVD advisory
CVE-2024-47081
Medium

This is what the package maintainer tells us about this finding

Requests is a HTTP library. Due to a URL parsing issue, Requests releases prior to 2.32.4 may leak .netrc credentials to third parties for specific maliciously-crafted URLs. Users should upgrade to version 2.32.4 to receive a fix. For older versions of Requests, use of the .netrc file can be disabled with trust_env=False on one's Requests Session.

External links with more info
Official GitHub advisory
Official NVD advisory
Education

Watch video on Insufficiently Protected Credentials

Subissues

2



Potential file inclusion attack via reading file
7 open subissues

55

Medium Risk

Potential file inclusion attack via reading file

We found 7 issues: last detected 5 minutes ago

New
SAST
TL;DR

If an attacker can control the input leading into the open function, they might be able to read sensitive files and launch further attacks with that information.

How do I fix it?

Ignore this issue only after you've verified or sanitized the input going into this function.  

Education

Watch video on Relative Path Traversal

Subissues

7
Subissue
backend
axial
.claude/skills/ui-ux-pro-max/scripts/core.py

Medium
Line 164 in core.py

with open(filepath, 'r', encoding='utf-8') as f:
View code analysis
Upgraded: AI assessed finding as likely exploitable

agent/main.py

Medium
Line 51 in main.py

with open(filepath, "rb") as f:
View code analysis
Upgraded: AI assessed finding as likely exploitable

backend/core/hashing.py

Medium
Line 19 in hashing.py

with open(source, "rb") as fh:
View code analysis
Upgraded: AI assessed finding as likely exploitable

backend/scripts/dropbox_helper.py

Medium
Line 187 in dropbox_helper.py

with open(output, 'wb') as f:
View code analysis
Upgraded: AI assessed finding as likely exploitable

backend/services/parsers.py

Medium
Line 2138 in parsers.py

with open(file_path, "rb") as f:
View code analysis
Upgraded: AI assessed finding as likely exploitable

backend/services/secure_cleanup.py

Medium
Line 231 in secure_cleanup.py

with open(path, 'r+b') as f:
View code analysis
Upgraded: AI assessed finding as likely exploitable

backend/scripts/sftp_helper.py

Low
Line 33 in sftp_helper.py

with open(value, "r", encoding="utf-8") as handle:
View code analysis
Downgraded: AI assessed finding as somewhat hard to exploit

2 ignored items


gevent
2 open subissues

55

Medium Risk

gevent

Affected by 2 CVEs: last detected 10 minutes ago

New
Dependency
TL;DR

gevent is affected by 2 vulnerabilities. To learn more about each one, consult the table below.The worst case impact for these vulnerabilities can be "HTTP request smuggling attack possible" and "A race condition exists".

Does this affect me?

We might be able to determine if this CVE is unable to affect you if you answer the below questions. This questionnaire is generated based on AIKIDO-2024-10330

We use Windows systems in production

Yes
No
Not sure
How do I fix it?

In order to fix all of these vulnerabilities, update gevent in axial to 25.4.1 or upgrade one at a time below.

2 unique known vulnerabilities found

AIKIDO-2025-10247
Medium

Aikido TLDR

Affected versions are vulnerable to HTTP request smuggling when using the `gevent_wsgi` or `gevent_pywsgi` worker classes. The issue stems from gevent’s `PyWSGIHandler`, where the `EXPECT: 100-continue` header causes the server to retain extra bytes in the socket buffer. These bytes are then interpreted as a new HTTP request, even if forwarded as part of an earlier one. This allows attackers to smuggle unauthorized requests—such as accessing `/admin` while only `/api` is exposed via a reverse proxy. The vulnerability can lead to serious security issues such as cache poisoning, data exposure, session hijacking, SSRF, cross-site scripting, and other impacts typical of HTTP request smuggling attacks.

Does this affect me?

You are affected if you are using a version that falls within the vulnerable range.

Aikido recommends

Upgrade the `gevent` library to the patch version.

AIKIDO-2024-10330
Low

Aikido TLDR

Affected versions of the package are vulnerable to a race condition. The `socket` module provides a pure-Python fallback to the `socket.socketpair()` function for platforms that do not support AF_UNIX, such as Windows. This implementation uses AF_INET or AF_INET6 to create a local connected pair of sockets. However, the connection between the two sockets is not verified before returning them to the user, leaving the server socket vulnerable to a connection race from a malicious local peer.

Does this affect me?

You are affected if you are using a version which is within vulnerability ranges and if you are using Windows OS.

Aikido recommends

Upgrade the `gevent` library to the patch version.

Subissues

2
Subissue
Fix
backend
axial
AIKIDO-2025-10247

Medium
requirements.txt

View reachability analysis
23.9.1 => 25.4.1

AIKIDO-2024-10330 | CVE-2024-3219

Low
requirements.txt

View reachability analysis
23.9.1 => 24.10.1


python-multipart
2 open subissues

38

Low Risk

python-multipart

Affected by 1 CVE: last detected 10 minutes ago

New
Dependency
TL;DR

Affected versions of this package are vulnerable to Denial of Service (DoS) attacks when processing requests with maliciously crafted input. Specifically, if a request includes junk data after the boundary in a multipart request, the server fails to handle it correctly. This causes resource exhaustion, resulting in the server becoming unresponsive and unable to process further requests.The worst case impact for these vulnerabilities can be "Attacker can trigger DOS-attack".

Show more
How do I fix it?

In order to fix all of these vulnerabilities, update python-multipart in axial to 0.0.18 or upgrade one at a time below.

1 unique known vulnerability found

AIKIDO-2024-10493
Low

Aikido TLDR

Affected versions of this package are vulnerable to Denial of Service (DoS) attacks when processing requests with maliciously crafted input. Specifically, if a request includes junk data after the boundary in a multipart request, the server fails to handle it correctly. This causes resource exhaustion, resulting in the server becoming unresponsive and unable to process further requests.

Does this affect me?

You are affected if you are using a version that falls within the vulnerable range.

Aikido recommends

Upgrade the `python-multipart` library to the patch version.

Subissues

2
Subissue
Fix
backend
axial
AIKIDO-2024-10493 | CVE-2024-53981

Low
backend/requirements.txt

View reachability analysis
Downgraded: Only impacts performance, not security

0.0.9 => 0.0.18

AIKIDO-2024-10493 | CVE-2024-53981

Low
requirements.txt

View reachability analysis
Downgraded: Only impacts performance, not security

0.0.9 => 0.0.18


	
2 exposed secrets

in test_ghost_protocol_security.py

Low

1 hr

4 exposed secrets

in conftest.py

Low

1 hr

Identified a Private Key, which may compromise cryptographic security and sensitive data encryption.

in SftpConnectModal.test.tsx

Low

1 hr

2 exposed secrets

in test_ghost_protocol_config.py

Low

1 hr

PY
sentry-sdk

Accidental exposure of sensitive info possible

Low

30 min

2 exposed secrets

in 1.md and 2.md

Low

1 hr

PY
openai

Sensitive information is being inserted in the log files

Low

30 min

PY
python-jose

Sensitive information exposed in error messages

Low

1 hr

