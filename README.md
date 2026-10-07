# Invoice Tracker

## Structure
- `sql/schema.sql` — Supabase tables + RLS + bucket + view
- `desktop/` — Windows app (Python + CustomTkinter)
- `web/` — Photo proof app (Next.js, deploy Vercel)

## Desktop quickstart
```
cd desktop
copy .env.example .env   # fill SUPABASE_URL + ANON_KEY
pip install -r requirements.txt
python main.py
```

## Web quickstart
```
cd web
copy .env.example .env.local  # fill NEXT_PUBLIC_ vars
npm install
npm run dev
```
Deploy on Vercel with same env vars.

## Flows
- standard: Created → PR → PO → GRN → SentToFinance → Paid
- straight: Created → SentToFinance → Paid
- SentToFinance manual via desktop Advance button, or automatic via web photo upload.
- Every change writes `audit_log` with actor/source.
