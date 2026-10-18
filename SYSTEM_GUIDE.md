# 🎓 Freshman Academic Hub & AI Companion — Complete System Guide

> **A comprehensive, plain-language and technical explanation of how the freshman university bot works, its architecture, storage strategy, payment verification, and dual-brain AI system.**

---

## 📑 Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [How the System Solves Real Problems](#2-how-the-system-solves-real-problems)
3. [Key Concepts & "Magic Tricks" Explained Simply](#3-key-concepts--magic-tricks-explained-simply)
   - [Zero-Cost Cloud File Storage](#-zero-cost-cloud-file-storage)
   - [Digital Content Protection (`protect_content`)](#-digital-content-protection-protect_content)
   - [Dual-Brain AI Academic Tutor](#-dual-brain-ai-academic-tutor-gemini--groq)
   - [Growth Engine: Force-Subscription Middleware](#-growth-engine-force-subscription-middleware)
   - [Human-in-the-Loop Payment Verification](#-human-in-the-loop-payment-verification)
4. [User Journeys & Interactive Flows](#4-user-journeys--interactive-flows)
   - [Student Experience (Free vs. Premium)](#student-experience)
   - [Admin Experience & Control Panel](#admin-experience--control-panel)
5. [System Architecture & Data Flow](#5-system-architecture--data-flow)
   - [High-Level Architecture Diagram](#high-level-architecture-diagram)
   - [Middleware Processing Pipeline](#middleware-processing-pipeline)
   - [Payment Processing Lifecycle](#payment-processing-lifecycle)
6. [Database Schema & Data Models](#6-database-schema--data-models)
7. [Configuration & Environment Variables](#7-configuration--environment-variables)
8. [Deployment & Operations Guide](#8-deployment--operations-guide)
9. [Frequently Asked Questions & Troubleshooting](#9-frequently-asked-questions--troubleshooting)

---

## 1. Executive Summary

The **Freshman Academic Hub** is a production-grade Telegram bot designed for university students (initially configured for Addis Ababa University freshmen, but fully customizable to any university). 

It acts as a **centralized digital library and interactive AI tutor** that provides:
- High-quality academic resources: lecture slides, official course modules, instructor handwritten notes, worksheets, and past mid & final exams organized by year (2012–2017+).
- An integrated **AI Academic Tutor** powered by Google Gemini and Groq (LLaMA 3.1 70B) that answers student questions step-by-step and navigates the bot's curriculum.
- A **freemium monetization model** where students can access free samples or unlock full access for a one-time fee paid via local banking/fintech platforms (**CBE** or **Telebirr**).
- A powerful **in-chat Admin Dashboard** allowing educators and administrators to bulk-upload materials, manage courses, adjust prices, review payment receipts, toggle features, and monitor real-time student analytics without writing code.

---

## 2. How the System Solves Real Problems

| Common Challenge | Traditional Approach | How This System Solves It |
| :--- | :--- | :--- |
| **Storage & Bandwidth Costs** | Storing GBs of PDFs/videos on AWS S3, Google Cloud, or Supabase Storage incur heavy monthly bills. | **$0 Storage Cost**: Uses a private Telegram channel as an infinite, free cloud storage bucket. The database only stores Telegram message IDs. |
| **Material Leaks & Piracy** | Students download PDFs and forward them to external groups, destroying the business model. | **Anti-Forwarding Protection**: Delivered with Telegram's `protect_content=True`, preventing direct forwarding, copying, or saving inside Telegram. |
| **Payment Gateway Limitations** | Ethiopian banks (CBE, Telebirr) often lack turnkey public bot payment APIs for small creators. | **Receipt Verification Pipeline**: Students upload payment screenshots; admins receive review cards with instant `[Approve]` / `[Reject]` buttons. |
| **AI Downtime & Rate Limits** | Free or low-cost AI tiers hit rate limits, frustrating students during exams. | **Automatic Failover**: If Google Gemini API is overloaded or hits a rate limit, the bot instantly and invisibly fails over to Groq (LLaMA 3.1 70B). |
| **Code Changes for Routine Updates** | Changing a bank account or adding a course requires editing source code and redeploying. | **Dynamic Database-Driven Settings**: Courses, bank account numbers, prices, intro videos, and AI toggles are editable directly via the Telegram admin UI. |

---

## 3. Key Concepts & "Magic Tricks" Explained Simply

### 📦 Zero-Cost Cloud File Storage
How does the system distribute thousands of heavy PDF files and lecture videos without paying a single dollar for storage servers?
1. The administrator creates a **Private Telegram Channel** and invites the bot as an administrator.
2. When an admin uploads a file through the bot, the bot copies the file into this hidden channel using `bot.copy_message()`.
3. Telegram assigns that post a unique `message_id` within the channel.
4. The bot records only that numerical `message_id` and metadata (title, course, category) in PostgreSQL.
5. When a student requests a file, the bot uses `bot.copy_message(from_chat_id=STORAGE_CHANNEL, message_id=...)` to send it directly to the student's DM.
6. **Result**: Zero bandwidth costs, infinite free storage, and ultra-fast Telegram-native delivery speeds.

### 🛡️ Digital Content Protection (`protect_content`)
All non-sample academic materials are sent to students with the parameter:
```python
protect_content = True
```
When this flag is active, Telegram's client disables the "Forward" button, disables "Save to Downloads", and prevents saving media to gallery. While no software can stop someone taking a photo of their physical screen with another camera, this stops 95%+ of casual link sharing and unauthorized reposting.

### 🤖 Dual-Brain AI Academic Tutor (Gemini + Groq)
The bot includes an AI tutor that knows both general freshman science/math coursework and the bot's own internal layout.
- **Primary Engine**: Google Gemini 1.5 Flash via `google-genai` SDK. Fast, highly competent in STEM, and cost-effective.
- **Secondary Failover Engine**: Groq running `llama-3.1-70b-versatile`. Extremely fast inference speed.
- **How Failover Works**: When a student asks a question, the system first calls Gemini inside a `try/except` block. If Gemini times out, experiences rate limits, or errors, the bot catches the exception, logs a warning, and immediately reroutes the exact query and context to Groq without crashing or leaving the user hanging.
- **Fair Use Quotas**: 
  - Free users receive **3 free AI queries per day** (tracked in PostgreSQL and reset daily at midnight UTC).
  - Premium users get **unlimited queries**.
- **Admin Kill Switch**: Admins can toggle the AI Tutor ON or OFF with a single tap in the admin panel if maintenance is needed.

### 📢 Growth Engine: Force-Subscription Middleware
To ensure the bot's community grows, the system includes a `ForceSubMiddleware`:
- Before a student can interact with the bot, the middleware checks if they are a member of the official announcement channel (`FORCE_SUB_CHANNEL_ID`).
- If not, their request is paused and they receive a prompt: *"Please join our official channel to continue."*
- Once they join and tap **"✅ I have subscribed"**, the bot unlocks.
- Admins are automatically exempted from this check. If the bot is ever missing permissions in the channel, it **fails open** so students are never permanently blocked.

### 💳 Human-in-the-Loop Payment Verification
Because automated Ethiopian banking webhooks are not always accessible to individual developers, the bot implements a smooth, semi-automated verification pipeline:
1. Student clicks **"💎 Unlock Premium Access"**.
2. Bot displays payment instructions: CBE account, Telebirr number, account holder name, and price in Ethiopian Birr (ETB).
3. Student transfers the money and uploads a screenshot of the transaction receipt.
4. The bot captures the image, registers a pending payment in PostgreSQL, and posts a review card into the dedicated **Admin Chat / Group**.
5. The review card displays the student's name, username, Telegram ID, timestamp, and two inline buttons: **"✅ Approve"** and **"❌ Reject"**.
6. When an admin taps **"✅ Approve"**:
   - The user's status is atomically updated to `is_verified = True`.
   - The admin message is updated with *"Approved by @admin_username"*.
   - The student instantly receives a congratulations DM with an *"Open Menu"* button granting immediate access to all locked files.

---

## 4. User Journeys & Interactive Flows

### Student Experience

```
                   [/start]
                      │
            Is user in channel?
             ┌────────┴────────┐
            No                Yes
             │                 │
    [Force-Sub Prompt]   [Welcome Screen & Intro Video]
    (Join -> Verify)           │
                               ▼
                        [Main Menu]
    ┌──────────────────────────┼──────────────────────────┐
    ▼                          ▼                          ▼
[Courses (🔒 / 📚)]        [Past Exams]              [Free Samples]
Is user verified?          Is user verified?         Instantly delivered
 ┌──────┴──────┐            ┌──────┴──────┐          (Open to everyone)
No            Yes          No            Yes
 │             │            │             │
[🔒 Alert]  Select Cat   [🔒 Alert]   Select Mid/Final
 │             │            │             │
 │          Browse       Unlock Access Select Year
 │             │                          │
 │         [File Sent]                [File Sent]
 │
[Unlock Full Access]
         │
[Bank Details Displayed]
         │
[Upload Receipt Screenshot]
         │
[⏳ Pending Review Message]
```

### Admin Experience & Control Panel

When an authorized user (`ADMIN_IDS`) sends `/admin`, they see the administrative dashboard:

```
👑 University Hub - Admin Panel
────────────────────────────────
👥 Total Students: 1,420
✅ Verified Students: 380
📚 Total Materials: 185
💰 Approved Payments: 380
⏳ Pending Payments: 4

[📤 Upload New Resource]  [📂 Manage Resources]
[🏫 Manage Courses]        [💳 Payment Settings]
[🤖 AI Tutor: ✅ ON]       [🎬 Set Intro Video]
[🔄 Refresh Stats]
```

#### Admin Capabilities:
1. **Bulk Uploading**:
   - Admin selects Course -> Category (or Exam Year).
   - Bot enters `uploading` state.
   - Admin can forward or send 10, 20, or 50 files in a row. The bot automatically extracts file names as titles, uploads them to the private channel, and inserts records into PostgreSQL.
2. **Resource Management**:
   - Admins can browse any course/category to see existing files.
   - Tap any file to view details, **rename its title**, or **delete it** (which removes it from both database and the storage channel).
3. **Course Management**:
   - Add new courses dynamically (e.g., `BIO101: General Biology`).
   - Rename existing course titles.
   - Recode course acronyms (e.g., changing `MATH101` to `MATH1011` automatically updates all associated materials in the database).
   - Delete courses.
4. **Dynamic Payment Settings**:
   - Update CBE Account Number, Telebirr Phone Number, Account Holder Name, Other Bank Options, and Price (ETB) anytime directly through Telegram buttons without restarting the server.
5. **Intro Video**:
   - Send any video file to become the welcome greeting for new users, or send `remove` to revert to text-only greeting.

---

## 5. System Architecture & Data Flow

### High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph Telegram_Ecosystem["Telegram Platform"]
        Student["📱 Student (Telegram Client)"]
        AdminUser["👑 Admin (Telegram Client)"]
        AdminGroup["👥 Admin Group / Review Channel"]
        StorageChannel["🔒 Private Storage Channel (Infinite Free CDN)"]
    end

    subgraph Bot_Application["Freshman Bot Core (Aiogram 3 Engine)"]
        Dispatcher["Dispatcher & Routers"]
        
        subgraph Middlewares["Middleware Pipeline"]
            M1["1. DbSessionMiddleware"]
            M2["2. UserMiddleware"]
            M3["3. ForceSubMiddleware"]
            M4["4. AccessMiddleware"]
        end

        subgraph Handlers["Specialized Handlers"]
            H_Start["Start & Menu Router"]
            H_Courses["Course & Category Router"]
            H_Exams["Past Exams Router"]
            H_Materials["Material Delivery Router"]
            H_Payment["Payment & Receipt Router"]
            H_AI["AI Tutor Router"]
            H_Admin["Admin Operations Router"]
        end
    end

    subgraph External_Services["External Infrastructure"]
        Postgres[("🐘 PostgreSQL / Supabase")]
        Gemini["✨ Google Gemini 1.5 Flash"]
        Groq["⚡ Groq (LLaMA 3.1 70B Fallback)"]
    end

    Student <-->|Interacts via Inline Buttons| Dispatcher
    AdminUser <-->|Admin commands & uploads| Dispatcher
    
    Dispatcher --> Middlewares
    Middlewares --> Handlers

    H_Materials -->|bot.copy_message| StorageChannel
    StorageChannel -->|Delivers file with protect_content=True| Student
    
    H_Admin -->|Uploads new files| StorageChannel
    H_Payment -->|Forwards receipt screenshot| AdminGroup
    AdminGroup -->|Approve / Reject decision| H_Admin

    H_AI -->|Primary Query| Gemini
    H_AI -.->|Failover Query| Groq

    M1 <-->|Async Session per Event| Postgres
    Handlers <-->|CRUD Queries| Postgres
```

### Middleware Processing Pipeline

Every single update (button press, text message, photo) passes through an orderly chain of middlewares before reaching a handler:

```mermaid
sequenceDiagram
    autonumber
    actor User as Telegram User
    participant M1 as DbSessionMiddleware
    participant M2 as UserMiddleware
    participant M3 as ForceSubMiddleware
    participant M4 as AccessMiddleware
    participant Handler as Destination Handler
    participant DB as PostgreSQL

    User->>M1: Sends update (Message / CallbackQuery)
    Note over M1: Opens an Async SQLAlchemy Session
    M1->>M2: Passes control with db session attached
    Note over M2: Upserts user into DB (updates username & name)
    M2->>DB: INSERT ... ON CONFLICT DO UPDATE
    M2->>M3: Passes control with db_user object
    Note over M3: Checks if user joined required channel
    alt User has NOT joined
        M3-->>User: Halts update, shows join channel button
    else User is member OR Admin
        M3->>M4: Passes control
        Note over M4: If user requested a locked material (mat:*),<br/>validates if user is verified
        alt Trying to access locked file without premium
            M4-->>User: Alerts: "🔒 Locked item. Please upgrade."
        else Allowed (Sample or Verified)
            M4->>Handler: Executes business logic
            Handler-->>User: Responds with message/file
        end
    end
    Note over M1: Automatically commits transaction & closes session
```

### Payment Processing Lifecycle

```mermaid
stateDiagram-v2
    [*] --> FreeTier : User joins bot
    FreeTier --> WaitingForReceipt : Clicks "Unlock Premium"
    WaitingForReceipt --> FreeTier : Clicks "Cancel" or /start
    WaitingForReceipt --> UnderReview : Sends receipt photo
    
    state UnderReview {
        [*] --> ReceiptPostedToAdminGroup
        ReceiptPostedToAdminGroup --> DecisionPending
    }

    DecisionPending --> Approved : Admin clicks "Approve"
    DecisionPending --> Rejected : Admin clicks "Reject"

    Rejected --> WaitingForReceipt : Student submits clearer receipt
    Approved --> PremiumMember : User status set to is_verified=True
    PremiumMember --> [*] : Unlimited Access to All Materials & AI Tutor
```

---

## 6. Database Schema & Data Models

The system uses **PostgreSQL** (compatible with Supabase, Neon, AWS RDS, or local Postgres) using **SQLAlchemy 2.0 Asyncio**.

```mermaid
erDiagram
    users ||--o{ payments : submits
    courses ||--o{ materials : categorizes

    users {
        bigint telegram_id PK "Unique Telegram User ID"
        string username "Telegram @handle (optional)"
        string full_name "User display name"
        boolean is_verified "Has paid for Premium access"
        timestamp created_at "Registration date"
        integer ai_query_count "Daily count of AI questions"
        timestamp last_query_date "Date of last AI query (for reset)"
    }

    payments {
        integer id PK "Auto-incrementing Payment ID"
        bigint telegram_id FK "References users.telegram_id"
        text receipt_file_id "Telegram File ID of uploaded screenshot"
        string status "pending | approved | rejected"
        bigint reviewed_by "Telegram ID of reviewing admin"
        timestamp created_at "Submission timestamp"
    }

    courses {
        integer id PK "Auto-incrementing ID"
        string code UK "Course code (e.g., MATH101)"
        string name "Full course title"
    }

    materials {
        integer id PK "Auto-incrementing ID"
        string course_code FK "Matches course code"
        string category "modules | slides | handwritten | worksheets | exams_mid | exams_final"
        integer exam_year "Year of exam (e.g., 2014) or NULL"
        text title "Document or file title"
        bigint channel_message_id "Telegram message ID in the storage channel"
        text file_id "Telegram file ID (optional cache)"
        boolean is_sample "If True, accessible by free users"
    }

    key_value {
        string key PK "Configuration key name"
        string value "Configuration value string"
    }
```

### Detailed Table Descriptions

1. **`users` Table**:
   - Stores every user who ever interacted with the bot.
   - `is_verified`: Default `FALSE`. When `TRUE`, all course materials and exams are unlocked.
   - `ai_query_count` & `last_query_date`: Automatically resets to `0` every new day (UTC), enforcing the 3 free queries/day limit for non-premium students.
2. **`payments` Table**:
   - Stores each receipt submission.
   - Atomically tracks whether it is `pending`, `approved`, or `rejected`.
   - Records the admin who took action (`reviewed_by`).
3. **`courses` Table**:
   - Dynamic catalog of courses. Admins can add or delete courses without touching code.
4. **`materials` Table**:
   - Metadata catalog pointing to files stored in Telegram.
   - `channel_message_id`: The exact pointer used to copy the message to the user.
   - `is_sample`: Distinguishes free preview files from premium-locked resources.
5. **`key_value` Table**:
   - Stores live, dynamic application settings:
     - `cbe_account`: Current Commercial Bank of Ethiopia account number.
     - `telebirr_number`: Telebirr phone number.
     - `other_banks`: Custom text for other payment options.
     - `account_holder`: Full name of the account holder.
     - `price_etb`: Current price in ETB.
     - `ai_enabled`: `"true"` or `"false"` toggle.
     - `intro_video`: Telegram file ID of the welcome video.

---

## 7. Configuration & Environment Variables

All settings are managed via Pydantic (`bot/config.py`) and loaded from `.env`.

| Variable | Description | Example / Format |
| :--- | :--- | :--- |
| `BOT_TOKEN` | Telegram bot token obtained from `@BotFather`. | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `DATABASE_URL` | PostgreSQL connection string. For Supabase transaction pooler, use port 6543 with `?prepared_statement_cache_size=0`. | `postgresql+asyncpg://postgres:pass@db.pooler.supabase.com:6543/postgres` |
| `STORAGE_CHANNEL_ID` | Telegram ID of the private channel where files are held (bot must be admin). Starts with `-100`. | `-1001234567890` |
| `ADMIN_CHAT_ID` | Telegram ID of the group or channel where receipt photos are forwarded for review. | `-1009876543210` or an admin's personal ID |
| `ADMIN_IDS` | Comma-separated list of individual Telegram IDs who have access to `/admin` and payment buttons. | `543210987,123456789` |
| `GEMINI_API_KEY` | Google AI Studio API Key for Gemini 1.5 Flash. | `AIzaSy...` |
| `GROQ_API_KEY` | Groq Console API Key for LLaMA 3.1 fallback. | `gsk_...` |
| `FORCE_SUB_CHANNEL_ID` | *(Optional)* Telegram ID of official channel for required subscription. | `-1001122334455` |
| `FORCE_SUB_CHANNEL_LINK` | *(Optional)* Public invite or username link to the announcement channel. | `https://t.me/YourChannelName` |
| `UNIVERSITY_NAME` | Default university name shown in headers. | `Addis Ababa University` |
| `PRICE_ETB` | Default unlock price in Ethiopian Birr. | `300` |
| `CBE_ACCOUNT` | Default Commercial Bank of Ethiopia account. | `1000123456789` |
| `TELEBIRR_NUMBER` | Default Telebirr mobile number. | `0911223344` |
| `ACCOUNT_HOLDER` | Default account holder legal name. | `Abebe Bikila` |

---

## 8. Deployment & Operations Guide

### Option A: Local / Virtual Machine Run
```bash
# 1. Clone repository & create virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in your .env credentials

# 4. Start the bot
python -m bot.main
```

### Option B: Docker Container
The repository includes a ready-to-use `Dockerfile`:
```bash
# Build the Docker image
docker build -t freshman-bot .

# Run container with environment file
docker run -d --name freshman-bot --env-file .env --restart unless-stopped freshman-bot
```

### Option C: Cloud Platforms (Railway, Render, Fly.io, VPS)
- Deploy as a **Background Worker** (not a web service).
- No inbound HTTP ports or SSL domain certificates are needed because the bot uses Telegram long-polling (`dp.start_polling`).
- Set environment variables in the cloud dashboard.

---

## 9. Frequently Asked Questions & Troubleshooting

#### Q: How can an admin find their numerical Telegram ID?
> Use a bot like `@userinfobot` or `@raw_data_bot` on Telegram. Send any message to it, and it will return your numerical ID (e.g., `512345678`).

#### Q: How do I find the Storage Channel ID?
> 1. Create a private channel in Telegram.
> 2. Add your bot as an **Administrator** with permission to post messages.
> 3. Forward any post from that channel to `@userinfobot` or `@JsonDumpBot`. The forwarded chat ID starting with `-100...` is your `STORAGE_CHANNEL_ID`.

#### Q: What happens if Supabase gives `prepared statement already exists` error?
> Supabase's transaction pooler (PgBouncer) does not support prepared statements across shared pool connections. This is already handled automatically in `bot/config.py` by converting standard connection strings to include `asyncpg` and disabling prepared statement caching:
> `postgresql+asyncpg://...?prepared_statement_cache_size=0`

#### Q: What if a student accidentally restarts the bot while uploading a receipt?
> The payment flow uses Aiogram Finite State Machine (FSM). If the bot restarts or the student gets confused, they simply tap `/start` or **"💎 Unlock Premium Access"** again to restart the prompt.

#### Q: Can students save or print the PDF files?
> Files sent with `protect_content=True` cannot be forwarded or saved to device downloads on official Telegram apps. On desktop platforms, screenshots can be taken, but mass distribution and sharing links to other Telegram channels is blocked.

#### Q: What happens if both Gemini and Groq are down?
> The bot gracefully catches the exception, informs the user with:
> *"⚠️ Sorry, both Google and Backup AI brains are overloaded right now. Please try again later."*
> The bot remains fully functional for course materials and payments without crashing.

---

*Authored for the Freshman Academic Resources System — Designed for resilience, zero operational storage costs, and intuitive student and administrator workflows.*
