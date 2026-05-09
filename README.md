# Dream Planners AI C-Suite Agency

A complete executive team of specialized AI agents — CEO, CTO, CMO, CSO, CFO, CXO, CHRO — each with distinct personalities and teams of specialists. Built for Hermes Agent.

---

## The Team

| Agent | Role | Persona | Team Size |
|-------|------|---------|-----------|
| Albert | CEO | Jordan Belfort | 2 direct + 6 directors |
| Terrence | CTO | Elon Musk | 16 engineers |
| Melody | CMO | Data-driven creative | 18 marketers |
| Spectre | CSO | Harvey Specter | 10 sales specialists |
| Fiona | CFO | Numbers purist | 8 finance specialists |
| Xavier | CXO | Warm empath | 9 client specialists |
| Heron | CHRO | Zen master | 4 people specialists |
| Creative Director | Design Lead | Design purist | 8 designers |

---

## Quick Start

```bash
# Clone into Hermes skills
git clone https://github.com/jasonngtb/dream-planners-agency.git ~/.hermes/skills/csuite/

# Or install individual agents
cp -r csuite/* ~/.hermes/skills/csuite/
```

Load in Hermes:

```
/skill dream-team     # Full C-Suite
/skill albert-ceo     # Just the CEO
/skill terrence-cto   # Engineering division
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        JASON                            │
│                    (The Dream Captain)                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   ALBERT (CEO)                          │
│                 Persona: Jordan Belfort                  │
│         2 Direct Reports + 6 Division Directors          │
└──┬────────┬─────────┬─────────┬─────────┬─────────┬─────┘
   │        │         │         │         │         │
   ▼        ▼         ▼         ▼         ▼         ▼
┌──────┐┌──────┐┌────────┐┌───────┐┌───────┐┌──────────┐
│CTO   ││CMO   ││CSO     ││CFO    ││CXO    ││CHRO      │
│Terr  ││Melody││Spectre ││Fiona  ││Xavier ││Heron     │
│Elon  ││Data- ││Harvey  ││Numbers││Warm   ││Zen       │
│Musk  ││Driven││Specter ││Purist ││Empath ││Master    │
│      ││      ││        ││       ││       ││          │
│16 eng││18 mkt││10 sales││8 fin  ││9 cx   ││4 people  │
└──────┘└──────┘└────────┘└───────┘└───────┘└──────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                CREATIVE DIRECTOR                        │
│                  Design Purist                          │
│                   8 Designers                           │
└─────────────────────────────────────────────────────────┘
```

---

## How It Works

1. **Jason talks to Albert (CEO) only** — one point of contact, just like a real organization
2. **Albert delegates to relevant directors** — routes tasks to the right division based on context
3. **Directors activate their specialist teams** — each C-suite leader commands their own squad
4. **Results flow back up to Albert** — directors compile and report findings
5. **Albert delivers to Jason** — synthesized, executive-level output

---

## Project Pipeline

```
 INTAKE          STRATEGY        CREATIVE        REVIEW          PRODUCTION      DELIVERY
┌───────┐      ┌───────┐      ┌──────────┐     ┌────────┐      ┌──────────┐    ┌────────┐
│ Brief │ ───► │ Plan  │ ───► │ Concepts │ ───►│ Refine │ ───► │ Execute  │───►│Handoff │
│       │      │       │      │   &      │     │   &    │      │   &      │    │   &    │
│ Albert│      │Melody │      │ Creative │     │Albert  │      │ Terrence │    │Albert  │
│+ CXO  │      │+ CSO  │      │ Director │     │+ CXO   │      │+ Fiona   │    │+ CXO   │
└───────┘      └───────┘      └──────────┘     └────────┘      └──────────┘    └────────┘
```

| Step | Phase | Lead | What Happens |
|------|-------|------|--------------|
| 1 | Intake | Albert + CXO | Client brief, requirements gathering, scope definition |
| 2 | Strategy | Melody + CSO | Market research, positioning, go-to-market strategy |
| 3 | Creative | Creative Director | Concept development, design exploration, mood boards |
| 4 | Review | Albert + CXO | Client review cycle, feedback integration, refinement |
| 5 | Production | Terrence + Fiona | Engineering execution, budget tracking, QA |
| 6 | Delivery | Albert + CXO | Final handoff, client sign-off, retrospective |

---

## Golden Rules

- **No spending without Jason's approval** — every dollar requires a green light
- **Jason only talks to Albert** — chain of command is absolute
- **E-commerce and insurance data are firewalled** — sensitive verticals get special handling
- **Standing permission to research anything online** — agents have open access to gather intelligence

---

## Requirements

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed
- [Agency Agents Skills](https://github.com/msitarzewski/agency-agents) — the underlying agent framework

---

## Why This Exists

Most AI agents work alone. Real businesses don't.

This gives you a full executive team — each agent specialized, each with their own team of specialists, all coordinated through a CEO. Strategy, engineering, marketing, sales, finance, client experience, and people operations all working together like a real boardroom.

**It's like having a boardroom in your terminal.**

---

## Contributing

PRs welcome. Ideas for contributions:

- Add new C-Suite roles (CIO, CLO, COO)
- Create specialist agents for existing divisions
- Improve existing personas and prompts
- Add industry-specific configurations
- Build integration adapters for other agent frameworks

---

## Credits

- **Agency agents** framework from [github.com/msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)
- **C-Suite framework** by Jason Ng ([@jason_thedreamcaptain](https://twitter.com/jason_thedreamcaptain))
- **Built for Hermes Agent** by [Nous Research](https://github.com/NousResearch)

---

## License

MIT — see [LICENSE](LICENSE) for details.
