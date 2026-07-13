# Stock Research Terminal (NSE/BSE) — Deploy & Share Guide

This gets you a public link (like `https://yourapp.streamlit.app`) that anyone
can open in a browser — Windows, Mac, phone, doesn't matter. No install needed
on their end. You only do the setup once.

---

## Step 1 — Push this folder to GitHub

1. Go to https://github.com/new and create a new repository (e.g. `stock-agent`). Public or private both work.
2. Upload all the files in this folder to that repo. Easiest way if you're not comfortable with git commands:
   - On the repo page, click **"uploading an existing file"**
   - Drag in every file from this folder (`app.py`, `config.py`, `data_fetcher.py`, `rules_engine.py`, `scoring.py`, `history_log.py`, `narrative.py`, `test_gemini_key.py`, `requirements.txt`)
   - Commit the changes

---

## Step 2 — Deploy on Streamlit Community Cloud (free)

1. Go to **https://share.streamlit.io** and sign in with your GitHub account
2. Click **"New app"**
3. Select the repo you just created
4. Set **Main file path** to `app.py`
5. Click **Deploy**

Streamlit will install everything from `requirements.txt` automatically and give you a public URL within a minute or two.

---

## Step 3 — Add your Gemini key as a Secret (so the narrative feature works for everyone)

Your key powers the AI narrative for every visitor — it's never visible to them and never appears in your GitHub code.

1. On your app's page on share.streamlit.io, click **⚙️ Settings → Secrets**
2. Paste this in, with your real key:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
3. Save — the app restarts automatically with the key active

That's it. Share the app's URL with anyone — they just open it like a website.

---

## Updating the app later

Whenever you want to change something: edit the file on GitHub (or push new commits), and Streamlit Cloud redeploys automatically within a minute.

---

## Honest limitations to know about

- **Shared free-tier quota**: everyone who clicks "Generate narrative" draws from *your* Gemini free-tier limit (~15 requests/minute, a daily cap). The app has a 15-second cooldown per visitor to soften this, but if it gets popular you may hit limits during busy moments. If that happens often, the fix is switching each visitor to use their own key instead — tell me and I'll change it.
- **Analysis history resets on redeploy**: the `data/analysis_history.csv` log (used for future backtesting) lives on Streamlit Cloud's temporary storage — it can reset when the app restarts or redeploys. Fine for now; if you want it to persist long-term, we'd move it to a small free database (e.g. Google Sheets or Supabase) later.
- **Promoter pledge/holding data**: not directly available from Yahoo Finance for NSE stocks — the app uses institutional holding as a rough stand-in. For the real number, check **screener.in**.
- **Interest coverage** is estimated, not exact — exact interest expense isn't always exposed for NSE-listed companies.
- This is for research and education only — not investment advice.

---

## Running it locally instead (optional)

If you ever want to run it on your own Mac instead of/alongside the public version:

```bash
cd stock_agent
pip install -r requirements.txt
streamlit run app.py
```

To enable the narrative feature locally, set an environment variable instead of using Secrets:
```bash
export GEMINI_API_KEY="your-key-here"
python3 test_gemini_key.py   # verify it works
streamlit run app.py
```

---

## What's in this folder

- `app.py` — the dashboard itself
- `config.py` — thresholds and scoring weights (tweak anytime)
- `data_fetcher.py` — pulls prices/fundamentals from Yahoo Finance
- `rules_engine.py` — the red-flag checks (debt, valuation, cash flow, etc.)
- `scoring.py` — turns the checks into a 0–10 composite score
- `history_log.py` — saves every analysis for future backtesting
- `narrative.py` — the Gemini bull/bear writeup
- `test_gemini_key.py` — standalone check that a Gemini key works
- `requirements.txt` — packages Streamlit Cloud installs automatically
