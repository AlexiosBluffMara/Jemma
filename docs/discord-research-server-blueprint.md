# Discord research server blueprint

This setup treats Discord as the collaboration surface, not the source of truth. Let everyone in immediately, keep speech professional, moderate aggressively, and move durable code and artifacts into GitHub plus external storage.

## Recommended operating model

- **Open by default:** everyone lands with a `visitor` role and can read `#start-here`, post in `#introductions`, and talk in `#open-lobby`.
- **Structured progression:** members earn `researcher` after acknowledging rules or lightweight verification, which unlocks project forums, code review, and artifact channels.
- **Heavy moderation without a hostile vibe:** use bot-assisted screening for spam, slurs, harassment, credential leaks, and non-professional conduct, then escalate into private moderator threads instead of public arguments.
- **Forum-first research flow:** use forum channels for `research-intake`, `code-review`, and `artifacts-and-datasets` so each idea, paper, benchmark, or dataset has its own durable thread with tags.
- **Private escalation path:** keep a `mod-intake` forum where the bot opens private threads for incident handling, appeals, and security reports.

## How to use server subscriptions well

- Keep **entry and core discussion free** so the community stays open.
- Use the subscription role for **office hours, curated AMAs, sponsor updates, or early-access implementation labs**, not for the main research commons.
- Protect subscriber spaces with a dedicated role such as `supporter`, but keep important announcements mirrored publicly when possible.

## Rules and permissions design

- Avoid `Administrator` for moderators. Give moderators only what they need: `MODERATE_MEMBERS`, `MANAGE_THREADS`, `READ_MESSAGE_HISTORY`, and normal communication permissions.
- Let `@everyone` read onboarding channels and speak in a slowmode-controlled lobby.
- Let `researcher` create public threads in the main forums.
- Reserve private threads and mod-only forums for moderators, bot operators, and trusted staff.
- Keep GitHub and CI bridges in their own channels so automation noise does not pollute discussion spaces.

## OAuth and bot installation

- Use the `bot` and `applications.commands` scopes.
- Pre-select the guild when possible and disable guild selection for safer installation.
- Use a redirect URI only when you need a full OAuth code flow for a dashboard or external control plane.
- Store `DISCORD_BOT_TOKEN`, `DISCORD_CLIENT_ID`, and `DISCORD_CLIENT_SECRET` in environment variables, not in the repository.

## What you need to fill out

Fill these values in your local environment before running the bot:

- `DISCORD_CLIENT_ID`: the Application ID from the Discord Developer Portal.
- `DISCORD_GUILD_ID`: your Discord server ID for **Alexios Bluff Mara**.
- `DISCORD_BOT_TOKEN`: the bot token from the Bot tab in the Discord Developer Portal.
- `DISCORD_CLIENT_SECRET`: only if you want a real OAuth callback flow beyond the install URL.

Then run:

- `jemma discord-setup-check`
- `jemma discord-oauth-url`
- `jemma discord-run-bot --sync-commands`

## File, code, and artifact handling

- **Code:** keep canonical code in GitHub. Discord should carry links to PRs, issues, gists, benchmarks, and actions results.
- **Files:** Discord attachments are good for intake, previews, and quick collaboration, especially when your server subscription improves upload limits. Mirror anything important into `artifacts\`, `datasets\`, GitHub Releases, or object storage.
- **Automation:** hash uploaded files, record metadata, and reply with the canonical storage link so Discord remains searchable without becoming the only copy.
- **Threads:** one artifact family, benchmark run, or paper discussion per thread keeps research history searchable and reusable.

## Commands added in this repo

- `jemma discord-blueprint`
- `jemma discord-oauth-url`
- `jemma discord-run-bot --sync-commands`

The runtime added in `src\jemma\discord\bot.py` gives you slash commands for asking the model questions, viewing the server blueprint, reviewing policy, and opening public or private intake threads.
