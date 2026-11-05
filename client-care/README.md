# Client-care toolkit

**Goal:** no existing client goes cold.
**Owner:** Xavier (client experience). **Approver:** Jason reviews every outgoing client message before it goes out. Everything here is a template; nothing is sent from this folder.
**Scope:** generic, Singapore. No client data, insurer names or products.

| File | What it's for |
|---|---|
| [`cadence.md`](cadence.md) | 12-month touchpoint calendar per client (welcome, 30-day, birthday, festive, half-year, life events, claims, annual review), with what's appropriate and what isn't |
| [`messages.md`](messages.md) | 40 WhatsApp/email templates (M01–M40) in warm Singapore English, with the ones the adviser must personalise flagged ✍️, plus a pre-send checklist |
| [`annual-review-agenda.md`](annual-review-agenda.md) | 30-minute review agenda and checklists (fact-find refresh, nominations/will/LPA, contact details, beneficiaries), MAS fair dealing, documenting advice |
| [`claims-support.md`](claims-support.md) | Supporting a client emotionally and practically through a claim (generic, no insurer process) |
| [`referral-ask.md`](referral-ask.md) | Low-pressure referral asks at policy delivery (P86) and reviews; PDPA and Do Not Call rules with PDPC citations |
| [`tracker-template.csv`](tracker-template.csv) | Follow-up tracker columns (one fictional example row) |

## Five rules
1. **Give, don't ask.** Care messages never sell, promise anything, or mention premiums or returns.
2. **Cold = 120 days without two-way contact.** The adviser calls personally.
3. **Max two unprompted messages per client per month.**
4. **No referral asks in writing, during claims, or at sensitive moments.**
5. **No real client data in this repository.** Working copies of the tracker live only in the team's approved, access-controlled system (PDPA).

## Tracker columns

| Column | Meaning |
|---|---|
| `client_ref` | Internal ID only. **Never NRIC** or names in shared files |
| `adviser` | Responsible adviser |
| `policy_issue_date` | Starts the 12-month cadence (YYYY-MM-DD) |
| `contact_pref` | e.g. "greetings OK", "service only", "no WhatsApp" |
| `preferred_channel` | WhatsApp / email / call |
| `greetings_opt_in` | Y/N: client happy to receive birthday and festive greetings |
| `birthday_month` | Month only (MM). Keep the full date of birth in the approved system, not here |
| `festivals` | Festivals the client told you they celebrate, `;`-separated |
| `in_mourning_until` | Skip celebratory greetings until this date (send M16-style messages instead) |
| `last_two_way_contact` / `days_since_two_way` / `cold_flag` | Cold flag = Y at 120+ days |
| `welcome_sent` … `birthday_sent` | Cadence touches done (Y/N or date) |
| `life_events` | Short neutral note, e.g. "new baby 2027-02". No medical details |
| `review_suggested` | Y if a life event means a review should be offered at the next natural touchpoint |
| `last_review` / `next_review` / `review_invite_sent` | Annual review tracking |
| `claim_open` / `claim_last_update` | Weekly updates while open. No medical details |
| `referral_ask_date` / `referral_declined_until` | Max twice a year; if declined, no ask for 12 months |
| `complaint_open` | Y = no referral asks, escalate per the insurer's process |
| `next_action` / `next_action_date` | The one next thing to do |
| `jason_approved` | pending / Y for the next outgoing message |
| `notes` | Neutral, factual. Write as if the client will read it |
