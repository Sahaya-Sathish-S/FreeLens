# FlowLens — Freelancer Cash Flow Predictor

A polished Flask prototype for Team 7's FinTech challenge. The core is an **explainable six-week cash ledger**, not a black-box model. The UI includes the supplied hero video and background image, interactive forecast chart, editable invoice/expense events, what-if actions, CSV import, Google sign-in via Supabase Auth, and optional Gemini/OpenRouter explanations.

## Features
- Six-week forecast: closing cash = opening cash + expected inflow − expected outflow.
- Safety-buffer threshold and first risky week detection.
- Up to three concrete recommendation cards with conditional, not guaranteed, cash impacts.
- What-if recalculation for earlier invoice timing and optional-expense deferral.
- Sample dataset based on the team's slide example ($3,200 opening balance, $1,500 buffer; week-four low of $950).
- Add invoices and expenses, edit amounts/week, delete events, switch currency, CSV import.
- Optional AI explanation through Gemini or OpenRouter. The numeric forecast is calculated in Python and never delegated to an LLM.
- Google login through Supabase JS. Without Supabase settings, the app runs in local demo mode.

## Run locally
1. Install Python 3.10+.
2. In this folder, create and activate a virtual environment.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill credentials you want to enable.
5. Start:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000`.

Windows PowerShell setup:
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

## Supabase Google login setup
1. Create a Supabase project.
2. In **Authentication → Providers → Google**, enable Google and enter the OAuth client ID/secret from Google Cloud Console.
3. Set the Supabase **Site URL** to your local or deployed URL, and add `http://127.0.0.1:5000/**` (or your exact callback route pattern) to allowed redirect URLs.
4. Run `schema.sql` in Supabase SQL Editor to create RLS-protected scenario tables.
5. Put the project URL and anon/publishable key into `.env` as `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
6. Restart Flask. Click **Continue with Google**.

When signed in and after running `schema.sql`, the **Save scenario** control stores the current scenario in Supabase and the app loads the latest saved scenario on sign-in. RLS policies restrict access to the signed-in owner. Without Supabase credentials, edits remain in browser memory for the demo.

## AI provider setup
- Add `GEMINI_API_KEY` for Gemini, or `OPENROUTER_API_KEY` for OpenRouter.
- Optional model overrides: `GEMINI_MODEL`, `OPENROUTER_MODEL`.
- Keys remain server-side in `.env`; never paste them into HTML/JavaScript or commit `.env` to Git.
- AI is only used to explain the already-calculated forecast. If no key is configured, the core product still works.

## CSV import format
Headers: `type,label,client,amount,week,category`

Example:
```csv
type,label,client,amount,week,category
invoice,Website milestone,Northstar Studio,2000,1,
expense,Rent and workspace,,1100,1,essential
expense,Optional design subscription,,35,2,optional
```
`type` should be `invoice`/`income` or `expense`/`outflow`; week must be 1–6. Imported rows are previewed before being added.

## Forecast logic & assumptions
For each week: `closing balance = opening balance + expected receipts − expected outflows`. Invoice dates are represented as expected receipt weeks in this MVP. A risk week is the first closing balance below the user-selected buffer. When there is little history, treat this as a scenario forecast, not certainty. Client delays, disputed invoices, taxes and one-off costs should be entered explicitly. Recommendations are conditional on client approval and are never automatically sent.

## Security / deployment notes
- `.env` is ignored by Git; keep all provider secrets server-side.
- Supabase Row Level Security policies are included in `schema.sql`.
- Set a strong `FLASK_SECRET_KEY`, turn `FLASK_DEBUG=false`, and use HTTPS in deployment.
- The included sample figures and client names are fictional and illustrative.
- This is a challenge prototype, not accounting, tax, investment or guaranteed-income advice.
