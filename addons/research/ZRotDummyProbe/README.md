# ZRot Dummy Observability Probe (research-only)

**Scope:** `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. This is a **local observability experiment**, not a General Rotation addon, live rotation advisor, DPS analyzer, combat logger, or encounter plan.

## Why this small addon exists

Two verified WCL Fury 15-second samples (54 and 51 player casts) lack any explicit raw cooldown, charge, recharge, reset or ready-state fields in the player-related events analyzed. The independent research engine cannot reconstruct actual competing-skill readiness from recast gaps, and no player-error verdict is authorized from these sources.

World of Warcraft Midnight 12.x restricts reading combat information through **Secret Values**. Blizzard's `C_Spell.GetSpellCooldown` and `C_Spell.GetSpellCharges` return data whose numeric timing and charge fields may be secret during combat. Blizzard marks certain fields (`isEnabled`, `isActive`, `maxCharges`) **NeverSecret**, but none proves full action readiness. `SPELL_UPDATE_COOLDOWN` doesn't guarantee a snapshot at cooldown completion, and `UNIT_SPELLCAST_SUCCEEDED` doesn't guarantee immediate cooldown API update. The addon must avoid any inference of exact readiness unless independently justified.

Blizzard/Warcraft Wiki reference contracts:
- https://news.blizzard.com/en-gb/article/24246290/combat-philosophy-and-addon-disarmament-in-midnight
- https://warcraft.wiki.gg/wiki/API:C_Spell.GetSpellCooldown
- https://warcraft.wiki.gg/wiki/API:C_Spell.GetSpellCharges
- https://warcraft.wiki.gg/wiki/API:issecretvalue
- https://warcraft.wiki.gg/wiki/UNIT_SPELLCAST_SUCCEEDED
- https://warcraft.wiki.gg/wiki/SPELL_UPDATE_COOLDOWN
- https://warcraft.wiki.gg/wiki/SPELL_UPDATE_CHARGES

## Local-only testing after explicit user selection

The `.toc` targets the **verified Retail 12.1.5 interface `120105`**, current on 2026-11-03. It is intentionally not on MAIN or an official published addon channel. If a later WoW patch changes the interface or API, update this research copy after checking the installed client and official documentation.

1. Place the `ZRotDummyProbe` folder in the normal `World of Warcraft/_retail_/Interface/AddOns/` location using the built branch's files; enable this research-only addon.
2. In a safe target-dummy environment use `/zrdprobe start`, practice a few casts, then `/zrdprobe stop`. The recorder is **opt-in**, does not run before start and does not identify enemies or modify game actions.
3. `/zrdprobe stats` reports only session count, tracked IDs and whether recording is active. `/zrdprobe track 123456` adds an ordinary numeric spell ID while recording is stopped, with a limit of 16 IDs.
4. For later independent analysis, the client's **normal SavedVariables** `WTF/Account/<account>/SavedVariables/ZRotDummyProbe.lua` will contain up to five sessions, each bounded to 2,400 observations. No external file I/O or web connections occur inside the addon. Any previous data with an unfamiliar schema is left untouched and recording disabled.

For safety, the addon does not use `COMBAT_LOG_EVENT_UNFILTERED`, foreign unit inspection, restricted automation, secure-frame manipulation, named targets, precise cooldown timers, input interception or arbitrary filesystem access. The observed numeric spell ID in `UNIT_SPELLCAST_SUCCEEDED` is **not proof of a manual keypress**.

## Retained schema and interpretation

Each local session has `schema=ZrotDummySafeSpellObservabilityV1`. Supported records:

- `PLAYER_CAST_SUCCEEDED` — player unit event; only non-secret numeric `spell_id` and local time; `manual_keypress`, `source_readiness_pre` and `verdict` remain `UNKNOWN`.
- `SPELL_OBSERVATION` — sampling at manual start or Blizzard cooldown/charge update event. Each spell stores only safe Boolean activity statuses (`OBSERVED_TRUE/FALSE`), safe non-secret current/max charge counts if available, and explicit `UNKNOWN_*` markers otherwise.
- `CAST_UNOBSERVABLE` / `SNAPSHOT_UNOBSERVABLE` — evidence not readable safely, no secret value included.

The addon **never accesses or serializes** `startTime`, `duration`, `cooldownStartTime`, `cooldownDuration`, `modRate`, `chargeModRate` or `isOnGCD`. `isActive=true` means a cooldown or recharge animation is active, **not that the spell is unavailable**; false does not imply full readiness. Max charges is capacity, not current availability. Observations are event-driven and **not guaranteed continuous**; the external research engine must still enforce strict PRE (`snapshot timestamp < cast timestamp`) and carry unknowns for unobserved transitions, resource cost, GCD, reset procs and target count.

## Verification boundaries

- GitHub Actions source checks, `luac -p` and a **mock Lua client** can validate source syntax, event registration, caller logic, secrecy sanitization, bounded storage, and non-destructive handling of mismatched SavedVariables.
- **Actual in-game Retail API behavior and target-dummy practice sessions have not been executed by GitHub CI**. No actual runtime permission or combat-mode exemption is claimed. In-game verification is an explicit separate requirement before any production Dummy Trainer output.
- A real user cast sequence cannot be called correct or incorrect solely from this probe. The research engine remains independent; any feedback must rely on verified General Rotation model plus comparable strict-PRE state and alternative readiness.

**Production/MAIN status:** NOT PROMOTED.
