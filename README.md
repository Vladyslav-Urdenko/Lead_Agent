# Lead_Master: Automated Lead Generation Tool

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-red.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Patreon](https://img.shields.io/badge/Support_me-Patreon-orange.svg)](https://www.patreon.com/Vladyslav_Urdenko)

Lead_Master is a powerful, Python-based automation tool designed to streamline the process of finding and collecting B2B leads. Stop wasting hours on manual prospecting and let the script do the heavy lifting for you.

> **COMMERCIAL USE NOTICE:**  
> This project is distributed under the **AGPLv3 License**. It is 100% free for personal, educational, and non-commercial use. However, if you intend to use Lead_Master in a commercial environment or integrate it into a closed-source business product, you must purchase a Commercial License.  
> [Get a Commercial License on my Patreon](https://www.patreon.com/Vladyslav_Urdenko)

**Created by:** Vladyslav Urdenko

---

## About the Project

I built Lead Master to help automate the boring parts of finding new clients. Whether you're a freelancer looking for gigs, a small agency owner, or just a developer interested in how data pipelines work, this tool is for you.

It combines several powerful technologies:
- **Web Scraping**: Uses `Playwright` and `BeautifulSoup` to find contact details from websites.
- **Search Intelligence**: Integrates with Google Search & Maps (via Serper.dev) to find businesses in specific niches and locations.
- **AI Power**: Uses OpenAI to analyze leads and generate personalized outreach messages.
- **Telegram Integration**: Sends you real-time alerts when new hot leads are found, so you can act immediately.

### Who is this for?
- **Students & Learners**: A great example of a modern Python async application using FastAPI, SQLAlchemy, and Celery.
- **Freelancers**: Find potential clients in your area automatically.
- **Business Owners**: Monitor your niche for new competitors or opportunities.

---

## License & Usage Terms

This project is distributed under the **AGPLv3 License**.

It is open for **educational purposes** and **personal use**. I want you to learn from it, experiment with it, and maybe even use it to find your first few clients!

However, **for commercial use, resale, or large-scale enterprise deployment**, you must obtain a **Commercial License**. Please respect the effort put into creating this software.

[Get a Commercial License on my Patreon](https://www.patreon.com/Vladyslav_Urdenko)

---

## Step-by-Step Installation Guide

Let's get you set up! Follow these steps to get Lead Master running on your local machine.

### 1. Prerequisites
You'll need:
- **Python 3.10+** installed.
- **PostgreSQL** (or Docker to run it easily).
- **Redis** (for background tasks).

### 2. Clone the Repository
```bash
git clone https://github.com/Start-Vlad/Lead_Master.git
cd Lead_Master
```

### 3. Set up a Virtual Environment
It's always best to keep dependencies isolated being organized is key!
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Mac/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
playwright install  # Needed for the scraper browser
```

### 5. Configure Environment Variables
This is the most important part! We don't want your secrets leaking.
1.  Copy the example file:
    ```bash
    cp .env.example .env
    ```
    *(Or just rename `.env.example` to `.env` manually)*

2.  Open `.env` in your editor and fill in your keys:
    *   **Database**: Set your Postgres user/pass. default user `postgres` usually works if you're local.
    *   **OpenAI API Key**: Required for the AI engine to write emails.
    *   **Serper API Key**: Get a free key at [serper.dev](https://serper.dev/) for Google search results.
    *   **Telegram**:
        *   Talk to `@BotFather` on Telegram to create a new bot and get a **Token**.
        *   Talk to `@userinfobot` to get your personal **Chat ID**.
        *   Paste them into the `.env` file.

### 6. Initialize the Database
Run this script to create the necessary tables in your database:
```bash
python init_db.py
```
*Note: Make sure your Postgres server is running first!*

### 7. Run the Application
You're ready to go!
```bash
python run.py
```
The server will start at `http://localhost:8001`.

---

## Features & How to Use

- **Dashboard**: Open your browser to `http://localhost:8001` to see the leads table.
- **Notifications**: Click the "Bell" icon to see recent alerts.
- **Refresh**: Hit the refresh button to grab the latest data without reloading the page.
- **Telegram Bot**: The system will send you a message whenever a high-quality lead (with an email found) is processed.

---

## Recommendations & Best Wishes

Building software is a journey. This project has a lot of moving parts-database, async queues, external APIs-so don't worry if it takes a moment to understand how they all fit together.

**My tips for you:**
*   Start small. Try to just get the database running first.
*   Watch the logs! They tell you exactly what's happening behind the scenes.
*   Don't be afraid to break things and fix them again. That's how we learn.

I hope Lead Master serves you well in your studies or your business. Good luck, and happy coding!

— **Vladyslav Urdenko**
