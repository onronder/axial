# Privacy Policy
*Effective Date: December 25, 2025 · Data Controller: FITTECHS YAZILIM ANONIM ŞİRKETİ*

## 1. Introduction & Scope
Welcome to Axio Hub. We are committed to protecting your personal data. This Privacy Policy explains how we collect, use, and safeguard your information in compliance with:
* **GDPR** (General Data Protection Regulation - EU)
* **KVKK** (Personal Data Protection Law No. 6698 - Turkey)
* **CCPA** (California Consumer Privacy Act - USA)

## 2. Processing & Storage Model
**Critical: We do not permanently store original files**
Axio Hub processes your content to create searchable embeddings and text chunks. Originals remain in your source platform, and any direct uploads are temporary.
* **Temporary Staging for Uploads:** If you upload a file directly, it is stored in our private staging bucket only for ingestion and is automatically deleted after processing.
* **Connected Sources:** For Drive/Notion/Slack/etc., we access the content to compute embeddings; the originals remain in your source system.
* **Stored Data:** We retain vector embeddings, extracted text chunks, and metadata (file names, URLs, IDs) to power search and chat.

## 3. Data We Collect
* **Identity Data:** Name, email address, profile picture (via OAuth).
* **Technical Data:** IP address, browser type, device information.
* **Usage Data:** Search queries, chat history, and interaction logs.
* **Vector Data:** Encrypted mathematical representations of your knowledge base content.
* **Extracted Text Chunks:** Parsed text snippets used to enable search and retrieval.

## 4. How We Use Your Data
* To provide the AI Search and Chat service.
* To synchronize your "Vector Index" with your source platforms (Notion, Drive).
* To improve our AI models (only aggregate, anonymized usage data; never your private content).
* To comply with legal obligations (KVKK/GDPR).

## 5. Data Sharing & Sub-processors
We share data only with trusted third-party service providers (Sub-processors) necessary to run the service:
* **Supabase:** Database and Vector Storage (Encryption at Rest).
* **OpenAI / LLM Providers:** For generating answers. **Note:** We have "Zero-Data Retention" agreements with our AI providers. They do not train on your data.
* **AWS:** Cloud Infrastructure.

## 6. Your Rights (GDPR, KVKK, CCPA)
You have the right to:
* **Access:** Request a copy of the data we hold about you.
* **Rectification:** Correct inaccurate data.
* **Erasure (Right to be Forgotten):** Request deletion of your account and all associated Vector Indices.
* **Portability:** Receive your data in a structured format.
* **KVKK Article 11:** Residents of Turkey have specific rights to inquire about data processing status.

## 7. Security Measures
* **Row-Level Security (RLS):** Ensures you can only access your own vectors.
* **Encryption:** All data is encrypted in transit (TLS 1.2+) and at rest (AES-256).
* **OAuth Tokens:** We store access tokens in an encrypted vault and never see your passwords.

## 8. Contact Us
For any privacy concerns or to exercise your rights:
* **Company:** FITTECHS YAZILIM ANONIM ŞİRKETİ
* **Email:** support@fittechs.com
* **Address:** Gayrettepe Mahallesi Yildiz Posta Caddesi Akin Sitesi 8/34 Besiktas İstanbul Türkiye
