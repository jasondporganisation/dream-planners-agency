# Pipeline Tracker: Stages and Rules

Template: `07-pipeline-tracker.csv`. **Keep the live tracker only in the firm's approved system.** The CSV here is a blank template with one example row; don't commit real candidate data. Use Candidate IDs (`DP27-001`), never names, phone numbers or emails in the tracker. Contact details live only in the consented booking/HR system.

## Stages

| Code | Stage | Enters when | Exit criteria / next stage |
|---|---|---|---|
| 01-Lead | Lead | Booked a career conversation through a consented form, or referred with consent | Conversation held → 02 |
| 02-Conversation | Career conversation | 20-min conversation done; honest career preview given | Wants to apply → 03; not interested → 99 |
| 03-Applied | Applied | Application received | Eligibility checked → 04 |
| 04-Eligibility | Eligibility check | Age-21-by-appointment and education confirmed from documents [S5] | Eligible → 05; not yet (e.g. under 21) → 10-Internship or 98 |
| 05-Interview1 | Interview 1 | Structured interview, two scorecards | 48–60 and no Q5/Q7 red flag → 07; 36–47 or a Q5/Q7 red flag → 06; below 36 → 98 (see `03-interview-guide.md` decision guide) |
| 06-Interview2 | Second conversation | Needed for 36–47 or a red flag; led by person without recruitment targets [S9] | → 07 or 98 |
| 07-Offer | Offer discussion | Principal's written terms shown; supervision capacity confirmed [S8] | Accepted → 08; declined → 99 |
| 08-PreLicensing | Pre-licensing | Terms signed as read; exams booked | All required modules passed → 09 |
| 09-Appointment | Appointment | Fit and proper checks done; principal lodges with MAS [S16][S17] | On MAS register [S6] → 11 |
| 10-Internship | Non-advising internship | Student or under-21 candidate in internship | Becomes eligible → 04; ends → 98 |
| 11-Onboarding | Onboarding Days 1–90 | Day 1 of the 90-day plan | Day 90 check done → 12 |
| 12-Active | Active after Day 90 | Day 90 check done | Track `active_month13` |
| 98-NotNow | Not this intake | Not eligible yet or didn't meet bar | Re-contact only if they agreed |
| 99-Withdrawn | Withdrawn / exited | Candidate withdrew or left | Record `exit_reason_category` |

## Column guide

| Column | Allowed values |
|---|---|
| track | graduate, career_switcher, part_time_to_full_time, internship |
| source_channel | linkedin, mycareersfuture, campus, referral, careerdna, other |
| owner_role | team_leader, heron, mentor (roles, not names) |
| preview_given, red_flag_q5_q7, non_target_interviewer, fit_proper_declared, written_terms_signed, on_mas_register, active_day90, active_month13 | Y / N |
| eligibility_* | yes, no, unknown |
| res5/m9/m9a/hi_status | not_booked, booked, passed, failed_resit_booked, not_required |
| day7/30/60/90_check | date done (YYYY-MM-DD) or blank |
| exit_reason_category | fit, income, exams, personal, other |

## Monthly report to Heron (aggregates only)
Leads by channel · conversion stage to stage · exams passed first time · days from offer to appointment · Day 30/60/90 checks done on time · active at Day 90 and Month 13 · exit reasons by category.
