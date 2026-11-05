# Dream Planners Agency

Working repo for **Jason Ng's Dream Planners**, a Great Eastern (Singapore) adviser team. Packs and tools here are drafted by Claude cloud sessions and reviewed by AI directors before Jason signs off.

- **Every document on `main`, with a one-line summary:** [`docs/INDEX.md`](docs/INDEX.md)
- **Opening a PR?** The [PR template](.github/pull_request_template.md) checklist is mandatory.

---

## Who reviews what

| Director | Area | Reviews |
|---|---|---|
| **Terrence** | Tech (CTO) | Tools, scripts, GitHub Actions, hosting |
| **Melody** | Marketing (CMO) | Podcast, reels, social posts, content banks |
| **Heron** | People (CHRO) | Recruitment, training, internships |
| **Xavier** | Clients (CXO) | Client-care templates, newsletters |
| **Spectre** | Sales (CSO) | Prospecting, objection handling |
| **Fiona** | Finance (CFO) | Budgets, calculators, figures |
| **Brand Guardian** | Compliance | Everything client-facing or public, checked against the fact pack |

Albert (CEO) and the Creative Director are persona skills too; see [Agent skills](#agent-skills) below.

---

## Folder map: on `main`

| Folder | What's in it | Owner | Status |
|---|---|---|---|
| [`compliance/`](compliance/) | Singapore personal-finance **fact pack** (Nov 2026). The single source for figures. | Brand Guardian | On main. Awaiting human sign-off; next review 1 Jan 2027 |
| [`content/podcast-research/`](content/podcast-research/) | *Quiet Compounding* public research pack, Ep 47–82, plus fact register | Melody (Brand Guardian review) | On main |
| [`content/podcast-research-advisers/`](content/podcast-research-advisers/) | *Quiet Compounding* adviser-track research pack, Ep 47–82 | Melody / Heron | On main |
| [`content/reel-scripts/`](content/reel-scripts/) | 30 Instagram reel scripts (R01–R30) | Melody (Brand Guardian review) | On main. 26 pass, 4 fixed |
| [`client-care/`](client-care/) | 12-month client cadence, 40 message templates, annual review, claims support, referral ask | Xavier | On main. Templates only; Jason approves every outgoing message |
| [`training/new-adviser-90-days/`](training/new-adviser-90-days/) | First-90-days pack for the Jan 2027 intake (modules A–F, coach checklist) | Heron | On main. Re-check figures the week before 4 Jan 2027 |
| [`programmes/winter-internship-2026/`](programmes/winter-internship-2026/) | Winter Internship 2026 pack: plan, workshops, forms, rubric, PDPA consent | Heron | On main. Draft for Jason; forms due to principal 30 Nov 2026 |
| [`research/`](research/) | 2027 FA representative recruitment market research | Heron | On main |
| [`greatlink-funds/`](greatlink-funds/) | GreatLink fund comparison tool: scraper and offline dashboard | Terrence | On main. Live (served at site root via `vercel.json`) |
| [`.github/`](.github/) | GreatLink refresh workflow (SHA-pinned) and PR template | Terrence | On main |
| [`docs/`](docs/) | Repo index | Terrence | On main |
| `*-ceo/`, `*-cto/`, `*-cmo/`, `*-cso/`, `*-cfo/`, `*-cxo/`, `*-chro/`, `creative-director/`, `dream-team/` | Persona `SKILL.md` files (see below) | Albert / each director | On main |

## In review: open pull requests

These folders are **not on `main` yet**. Do not rely on them until merged.

| PR | Folder(s) | What | Owner | Status |
|---|---|---|---|---|
| [#15](https://github.com/jasondporganisation/dream-planners-agency/pull/15) | `podcast/scripts/` | *Quiet Compounding* draft scripts, Ep 47–56 (adviser track) | Melody (Brand Guardian review) | In review |
| [#16](https://github.com/jasondporganisation/dream-planners-agency/pull/16) | `training/` (objection playbook and cheat sheet) | Objection-handling playbook and one-page cheat sheet for new reps | Spectre / Heron | In review |
| [#17](https://github.com/jasondporganisation/dream-planners-agency/pull/17) | `greatlink-funds/`, `.github/workflows/` | GreatLink refresh: data-sanity checks, offline parser tests, stale-data banner | Terrence | In review |
| [#18](https://github.com/jasondporganisation/dream-planners-agency/pull/18) | `recruitment/2027-kit/` | 2027 recruitment kit: job ads, campus talk, interview guide, onboarding, pipeline tracker | Heron | In review |
| [#19](https://github.com/jasondporganisation/dream-planners-agency/pull/19) | `clients/newsletters/` | Client newsletters, Dec 2026 to Jun 2027 (drafts, not sent) | Xavier (Brand Guardian review) | In review |
| [#20](https://github.com/jasondporganisation/dream-planners-agency/pull/20) | `programmes/winter-internship-2026/slides/` | Internship facilitator slide outlines (Days 1–5), Day 5 brief and rubric, feedback form | Heron | In review |
| [#21](https://github.com/jasondporganisation/dream-planners-agency/pull/21) | `content/2027-bank/` | 2027 content bank: 100 educational posts for Instagram and LinkedIn | Melody (Brand Guardian review) | In review |

Newer drafts (for example [#22](https://github.com/jasondporganisation/dream-planners-agency/pull/22), calculators, and [#23](https://github.com/jasondporganisation/dream-planners-agency/pull/23), huddle agendas) are listed on the [pull requests page](https://github.com/jasondporganisation/dream-planners-agency/pulls).

---

## House rules (all folders)

1. **Brand Guardian checks anything client-facing or public.** That means no guarantees, no return or earnings claims, no product or insurer promotion, and general education only.
2. **No client data in this repo.** No names, NRIC, contact details, policy or health information. Use placeholders only.
3. **Figures come from the fact pack** ([`compliance/sg-fact-pack-2026-11.md`](compliance/sg-fact-pack-2026-11.md)) or from an official source with a checked date. Anything unchecked is marked **UNVERIFIED**.
4. **GitHub Actions are pinned to full commit SHAs**, never tags.
5. **Nothing is spent or sent without Jason's approval.**

---

## Agent skills

Persona prompts for the AI C-suite, used with Hermes Agent (`/skill dream-team` loads them all).

| Skill | Role |
|---|---|
| [`albert-ceo`](albert-ceo/SKILL.md) | CEO, orchestrator. Jason talks to Albert, and Albert delegates |
| [`terrence-cto`](terrence-cto/SKILL.md) | Tech |
| [`melody-cmo`](melody-cmo/SKILL.md) | Marketing |
| [`spectre-cso`](spectre-cso/SKILL.md) | Sales |
| [`fiona-cfo`](fiona-cfo/SKILL.md) | Finance |
| [`xavier-cxo`](xavier-cxo/SKILL.md) | Client experience |
| [`heron-chro`](heron-chro/SKILL.md) | People |
| [`creative-director`](creative-director/SKILL.md) | Design |
| [`dream-team`](dream-team/SKILL.md) | Loads all of the above |

## Credits

C-suite framework by Jason Ng ([@jason_thedreamcaptain](https://twitter.com/jason_thedreamcaptain)). Built on [agency-agents](https://github.com/msitarzewski/agency-agents) for [Hermes Agent](https://github.com/NousResearch/hermes-agent). MIT licensed.
