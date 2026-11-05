# Educational calculators (draft — needs review before client use)

Four static pages for client meetings. Open `index.html` in any browser; no install or server needed.

| Page | What it shows | Default figures |
|---|---|---|
| `emergency-fund.html` | Months of expenses your savings cover, and the gap to a target you choose | None (the fact pack has no official guideline) |
| `retirement-gap.html` | Illustrative, inflation-adjusted lump sum needed at retirement and shortfall | None; user enters every rate. Reference hints: life expectancy at 65 (21.6 yrs), CPI 2025 (0.9%) and Sep 2026 (2.2%) |
| `cpf-retirement-sums.html` | BRS/FRS/ERS for members turning 55 in 2026 and 2027, and how far an RA balance is from each | Retirement Sums (fact pack 1.3) and CPF's payout estimates (1.4) |
| `cost-of-delay.html` | Saving monthly from now vs starting later, same end date | None; user enters the rate |

All figures come from `compliance/sg-fact-pack-2026-11.md` (checked 3 Nov 2026) with links to the official pages. **Update `calc.js` and `cpf-retirement-sums.html` when CPF publishes new Retirement Sums** (next fact-pack review: 1 Jan 2027).

## Privacy and safety

- No server, cookies, storage, analytics or external scripts. A Content-Security-Policy blocks all network requests (`connect-src 'none'`, `form-action 'none'`).
- Every page carries the current disclaimer. Illustration pages say they are not projections or guarantees.
- No product or insurer names.

## Files

- `calc.js` — all maths, pure functions, shared by the pages and tests.
- `ui.js` — formatting and form handling. One small `*.js` per page.
- `calc.test.js` — unit tests (Node built-in runner):

```bash
node --test tools/calculators/calc.test.js
```

## Formulas (for Fiona)

- **Emergency fund:** target = expenses × months; months covered = savings ÷ expenses.
- **Retirement gap:** gap today = max(0, wanted − other income). Gap at retirement = gap × (1 + inflation)^years-to-retirement. Lump sum needed = present value at retirement of a yearly gap growing with inflation, paid at the start of each year, for the years entered (rounded up), discounted at the "during retirement" return. Savings grow at the "before retirement" return. Shortfall also shown ÷ inflation factor (today's dollars). Other income is assumed to rise with inflation; the page warns that CPF LIFE Standard Plan payouts are level.
- **CPF sums:** difference = sum − RA balance; percentage = balance ÷ sum.
- **Cost of delay:** monthly rate = (1 + yearly rate)^(1/12) − 1; deposits at month end; future value of an ordinary annuity over whole months.
