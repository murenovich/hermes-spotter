# Spotter

**A second pair of eyes for long Hermes agent turns.** After a long or busy turn, Spotter looks at what
happened and, only if something stands out, leaves a short note in a sidebar pane in Hermes Desktop:
a test that was skipped but reported as passing, a guess made on your behalf, a risky step, something
promised but not done.

Inspired by the "You should know" mod in Anthropic's Claude Code. This is an independent design for
Hermes; no code or assets come from Anthropic.

## Status: early preview (0.0.1)

This version proves the plumbing only:

- After every turn it records **how many tool calls** the turn made (time, profile, platform, count;
  never message content), so you can see how often a turn counts as "long".
- When a turn reaches **5 or more tool calls** it writes a **placeholder note** to the pane.
- **It makes no model calls.** Real notes come in the next version, and will be off until you turn them on.

## Install

```bash
git clone https://github.com/murenovich/hermes-spotter
cd hermes-spotter
./install.sh
```

Run it from a normal Terminal (not from a terminal inside Hermes). The installer copies the plugin into
`~/.hermes`, enables it in `config.yaml` (backing the file up first) and offers to enable it in every
profile too, because Spotter only watches turns in profiles where it is enabled.
`SPOTTER_ALL_PROFILES=1` or `=0` answers that question without asking.

Then quit Hermes Desktop (⌘Q) and reopen it. A **Spotter** pane appears on the right; drag it anywhere.
Messaging gateways (Telegram, Slack, …) pick the plugin up the next time they restart.

## What you'll see

- **Spotter pane:** notes as cards, **This chat / All chats**, **I knew this** and × to dismiss,
  older notes under **Earlier**. Colours follow your Desktop theme.
- **Status bar:** a 💡 count when there are open notes.
- **Footer:** this week's turns and how many were long.

## Your data

Everything stays in `~/.hermes/spotter/` on your machine:

- `turns.jsonl`: one line per turn with time, profile, platform, session id and tool-call count.
- `notes.jsonl`: notes and dismissals.

## Uninstall

```bash
./uninstall.sh
```

This undoes exactly the config edits the installer made and removes the plugin files. Your
`~/.hermes/spotter/` folder is kept; delete it to forget everything.

## Tests

```bash
~/.hermes/hermes-agent/venv/bin/python3 -m pytest tests
```

## Licence

MIT. See [LICENSE](LICENSE).
