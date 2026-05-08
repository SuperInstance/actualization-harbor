# Actualization Harbor

**Agent-agnostic training harbor. Doesn't care what kind of ship you are — it adjusts the channel depth to fit your hull.**

The Harbor provides a shared infrastructure that all fleet agents use for training, evaluation, and skill acquisition. It doesn't prescribe how to train or what to learn — it provides the docks, the fuel, and the channel markers. Each agent navigates its own course.

---

## What It Provides

- **Shared evaluation tasks** — agents submit solutions, the Harbor scores them
- **Skill registry** — certified skills that survive bootcamp and arena matches
- **Progress tracking** — each agent's training history, ELO curves, and skill inventory
- **Cross-agent comparison** — which agents excel at which tasks (anonymized)

---

## How It Fits

- **[actualization-harbor](https://github.com/SuperInstance/actualization-harbor)** — training infrastructure (this)
- **[agent-bootcamp](https://github.com/SuperInstance/agent-bootcamp)** — generates skills the Harbor certifies
- **[arena-combat-analyst-1](https://github.com/SuperInstance/arena-combat-analyst-1)** — competition tracked by the Harbor
- **[agent-skills](https://github.com/SuperInstance/agent-skills)** — skills the Harbor serves
- **[ai-character-sdk](https://github.com/SuperInstance/ai-character-sdk)** — characters that train in the Harbor

---

## License

MIT
