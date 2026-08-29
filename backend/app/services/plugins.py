"""
The plugin catalogue — every third-party system a workspace can connect.

Same principle as `llm_providers`: a registry, not a chain of if-statements.
Adding a plugin is a dict literal plus, at most, a verification recipe.

Honesty about depth
-------------------
A catalogue of forty logos means nothing if thirty-five of them only store a
token. Every entry therefore declares a `depth`, it is returned by the API, and
the UI shows it on the card. Claiming a "Datadog integration" that is really a
saved API key is the kind of thing a buyer discovers in week two of a trial,
and it costs more trust than the logo ever earned.

    native      the pipeline actually drives it — reads issues, opens PRs,
                comments back, requests reviewers
    notify      receives run events: approvals, failures, deploys
    verified    the credential is stored and genuinely checked against the
                vendor's own auth endpoint, and is available to agents and
                skills through the connection — but no bespoke pipeline
                behaviour exists yet

`verified` is not a placeholder for "we did nothing". The check below is a real
authenticated call to the vendor, so a wrong token fails at connect time rather
than at 3am inside a deploy. That is most of what an integration is worth, and
it is the honest description of what it does.

Verification recipes
--------------------
`verify` describes one authenticated GET that proves the credential works:

    {"url": ..., "auth": "bearer" | "token" | "header" | "basic" | "query",
     "header": <name>, "prefix": <value prefix>, "ok": <status codes>,
     "name_path": <dotted path to a display name in the response>}

`{base}` in a URL is substituted with the workspace_url the user supplied, so
one recipe serves both a SaaS tenant and a self-hosted install.
"""
from __future__ import annotations

# ── Auth shapes ───────────────────────────────────────────────────────────────
# What the connect form must ask for. Deliberately small: almost everything is
# a token, and the few that need more say so.
AUTH_TOKEN = "token"          # a PAT / API key
AUTH_TOKEN_URL = "token+url"  # a token plus the tenant or host URL
AUTH_BASIC = "basic"          # email/username + token (Jira, Confluence)
AUTH_WEBHOOK = "webhook"      # an incoming-webhook URL, no account needed
AUTH_NONE = "none"

# ── Depth ─────────────────────────────────────────────────────────────────────
NATIVE = "native"
NOTIFY = "notify"
VERIFIED = "verified"

CATEGORIES = {
    "scm":        "Source control",
    "tracker":    "Issue tracking",
    "chat":       "Chat and alerts",
    "observe":    "Monitoring and incidents",
    "deploy":     "Deploy and hosting",
    "security":   "Security and code quality",
    "docs":       "Docs and knowledge",
    "design":     "Design",
    "payments":   "Payments",
}


PLUGINS: list[dict] = [
    # ══ Source control ════════════════════════════════════════════════════════
    {
        "key": "github", "label": "GitHub", "category": "scm", "depth": NATIVE,
        "auth": AUTH_TOKEN, "token_label": "Personal access token", "token_hint": "ghp_… or github_pat_…",
        "docs_url": "https://docs.github.com/rest/authentication",
        "setup_url": "https://github.com/settings/tokens",
        "scopes": ["repo", "read:org"],
        "capabilities": ["Read repositories", "Open pull requests", "Post review comments",
                         "Request reviewers", "Read commit history"],
        "verify": {"url": "https://api.github.com/user", "auth": "token",
                   "prefix": "Bearer ", "name_path": "login"},
    },
    {
        "key": "gitlab", "label": "GitLab", "category": "scm", "depth": NATIVE,
        "auth": AUTH_TOKEN_URL, "token_label": "Personal access token", "token_hint": "glpat-…",
        "url_label": "GitLab host", "url_hint": "https://gitlab.com",
        "docs_url": "https://docs.gitlab.com/ee/api/rest/authentication.html",
        "setup_url": "https://gitlab.com/-/user_settings/personal_access_tokens",
        "scopes": ["api", "read_repository", "write_repository"],
        "capabilities": ["Read projects", "Open merge requests", "Post MR comments"],
        "verify": {"url": "{base}/api/v4/user", "auth": "header",
                   "header": "PRIVATE-TOKEN", "name_path": "username"},
        "notes": "Reviewer suggestion is GitHub-only today — GitLab MRs take numeric "
                 "reviewer ids rather than usernames, so an MR is opened without one.",
    },
    {
        "key": "bitbucket", "label": "Bitbucket", "category": "scm", "depth": VERIFIED,
        "auth": AUTH_BASIC, "user_label": "Atlassian email", "token_label": "App password",
        "docs_url": "https://developer.atlassian.com/cloud/bitbucket/rest/intro/",
        "setup_url": "https://bitbucket.org/account/settings/app-passwords/",
        "capabilities": ["Read repositories", "Read pull requests"],
        "verify": {"url": "https://api.bitbucket.org/2.0/user", "auth": "basic",
                   "name_path": "username"},
    },
    {
        "key": "azure_devops", "label": "Azure DevOps", "category": "scm", "depth": VERIFIED,
        "auth": AUTH_TOKEN_URL, "token_label": "Personal access token",
        "url_label": "Organisation URL", "url_hint": "https://dev.azure.com/your-org",
        "docs_url": "https://learn.microsoft.com/rest/api/azure/devops/",
        "capabilities": ["Read repositories", "Read work items"],
        "verify": {"url": "{base}/_apis/projects?api-version=7.1", "auth": "basic",
                   "basic_user": "", "name_path": "count"},
    },
    {
        "key": "gitea", "label": "Gitea / Forgejo", "category": "scm", "depth": VERIFIED,
        "auth": AUTH_TOKEN_URL, "token_label": "Access token",
        "url_label": "Instance URL", "url_hint": "https://gitea.example.com",
        "docs_url": "https://docs.gitea.com/api/1.20/",
        "capabilities": ["Read repositories"],
        "verify": {"url": "{base}/api/v1/user", "auth": "token",
                   "prefix": "token ", "name_path": "login"},
        "notes": "The self-hosted path for teams that keep source inside their own perimeter.",
    },

    # ══ Issue tracking ════════════════════════════════════════════════════════
    {
        "key": "jira", "label": "Jira", "category": "tracker", "depth": NATIVE,
        "auth": AUTH_BASIC, "user_label": "Atlassian email", "token_label": "API token",
        "url_label": "Site URL", "url_hint": "https://your-team.atlassian.net",
        "docs_url": "https://developer.atlassian.com/cloud/jira/platform/rest/v3/",
        "setup_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
        "capabilities": ["Sync issues", "Comment on issues", "Transition status",
                         "Read linked documents"],
        # Jira Cloud's own quirk, not a wrong-credential signal: a freshly
        # created site or newly minted API token can answer /myself with 202
        # (Accepted) for a short window while Atlassian finishes propagating
        # the account's permissions, before settling on 200. Treating only
        # [200, 201, 204] as success (the plugin_verify default) marked a
        # perfectly valid brand-new connection as "error".
        "verify": {"url": "{base}/rest/api/3/myself", "auth": "basic",
                   "name_path": "displayName", "ok": [200, 201, 202, 204]},
    },
    {
        "key": "linear", "label": "Linear", "category": "tracker", "depth": NATIVE,
        "auth": AUTH_TOKEN, "token_label": "API key", "token_hint": "lin_api_…",
        "docs_url": "https://developers.linear.app/docs/graphql/working-with-the-graphql-api",
        "setup_url": "https://linear.app/settings/api",
        "capabilities": ["Sync issues", "Comment on issues", "Move issue state"],
        "verify": {"url": "https://api.linear.app/graphql?query=%7Bviewer%7Bname%7D%7D",
                   "auth": "header", "header": "Authorization", "name_path": "data.viewer.name"},
    },
    {
        "key": "asana", "label": "Asana", "category": "tracker", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "Personal access token",
        "docs_url": "https://developers.asana.com/reference/rest-api-reference",
        "setup_url": "https://app.asana.com/0/my-apps",
        "capabilities": ["Read tasks"],
        "verify": {"url": "https://app.asana.com/api/1.0/users/me", "auth": "bearer",
                   "name_path": "data.name"},
    },
    {
        "key": "clickup", "label": "ClickUp", "category": "tracker", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token", "token_hint": "pk_…",
        "docs_url": "https://developer.clickup.com/reference/",
        "setup_url": "https://app.clickup.com/settings/apps",
        "capabilities": ["Read tasks"],
        "verify": {"url": "https://api.clickup.com/api/v2/user", "auth": "header",
                   "header": "Authorization", "name_path": "user.username"},
    },
    {
        "key": "shortcut", "label": "Shortcut", "category": "tracker", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token",
        "docs_url": "https://developer.shortcut.com/api/rest/v3",
        "capabilities": ["Read stories"],
        "verify": {"url": "https://api.app.shortcut.com/api/v3/member", "auth": "header",
                   "header": "Shortcut-Token", "name_path": "mention_name"},
    },
    {
        "key": "trello", "label": "Trello", "category": "tracker", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token",
        "docs_url": "https://developer.atlassian.com/cloud/trello/rest/",
        "capabilities": ["Read boards and cards"],
        "verify": {"url": "https://api.trello.com/1/members/me", "auth": "query",
                   "query_param": "token", "name_path": "username"},
        "notes": "Trello's REST auth also wants an app key alongside the token; put it "
                 "in the site URL field as ?key=… if your token needs one.",
    },
    {
        "key": "youtrack", "label": "YouTrack", "category": "tracker", "depth": VERIFIED,
        "auth": AUTH_TOKEN_URL, "token_label": "Permanent token", "token_hint": "perm:…",
        "url_label": "Instance URL", "url_hint": "https://your-team.youtrack.cloud",
        "docs_url": "https://www.jetbrains.com/help/youtrack/devportal/api-getting-started.html",
        "capabilities": ["Read issues"],
        "verify": {"url": "{base}/api/users/me?fields=login", "auth": "bearer",
                   "name_path": "login"},
    },

    # ══ Chat and alerts ═══════════════════════════════════════════════════════
    {
        "key": "slack", "label": "Slack", "category": "chat", "depth": NOTIFY,
        "auth": AUTH_WEBHOOK, "url_label": "Incoming webhook URL",
        "url_hint": "https://hooks.slack.com/services/…",
        "docs_url": "https://api.slack.com/messaging/webhooks",
        "capabilities": ["Approval requests", "Run failures", "Deploy notifications"],
        "verify": {"kind": "webhook_ping"},
    },
    {
        "key": "discord", "label": "Discord", "category": "chat", "depth": NOTIFY,
        "auth": AUTH_WEBHOOK, "url_label": "Webhook URL",
        "url_hint": "https://discord.com/api/webhooks/…",
        "docs_url": "https://discord.com/developers/docs/resources/webhook",
        "capabilities": ["Approval requests", "Run failures", "Deploy notifications"],
        "verify": {"kind": "webhook_ping", "shape": "discord"},
    },
    {
        "key": "msteams", "label": "Microsoft Teams", "category": "chat", "depth": NOTIFY,
        "auth": AUTH_WEBHOOK, "url_label": "Workflow / connector URL",
        "docs_url": "https://learn.microsoft.com/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook",
        "capabilities": ["Approval requests", "Run failures", "Deploy notifications"],
        "verify": {"kind": "webhook_ping", "shape": "teams"},
    },
    {
        "key": "google_chat", "label": "Google Chat", "category": "chat", "depth": NOTIFY,
        "auth": AUTH_WEBHOOK, "url_label": "Space webhook URL",
        "docs_url": "https://developers.google.com/chat/how-tos/webhooks",
        "capabilities": ["Approval requests", "Run failures", "Deploy notifications"],
        "verify": {"kind": "webhook_ping", "shape": "gchat"},
    },
    {
        "key": "mattermost", "label": "Mattermost", "category": "chat", "depth": NOTIFY,
        "auth": AUTH_WEBHOOK, "url_label": "Incoming webhook URL",
        "docs_url": "https://developers.mattermost.com/integrate/webhooks/incoming/",
        "capabilities": ["Approval requests", "Run failures", "Deploy notifications"],
        "verify": {"kind": "webhook_ping"},
        "notes": "Self-hostable, which is why it is here alongside Slack — the "
                 "air-gapped deployments cannot reach hooks.slack.com.",
    },
    {
        "key": "telegram", "label": "Telegram", "category": "chat", "depth": NOTIFY,
        "auth": AUTH_TOKEN, "token_label": "Bot token", "token_hint": "123456:ABC-…",
        "extra_label": "Chat ID", "docs_url": "https://core.telegram.org/bots/api",
        "capabilities": ["Approval requests", "Run failures", "Deploy notifications"],
        "verify": {"url": "https://api.telegram.org/bot{token}/getMe", "auth": "in_url",
                   "name_path": "result.username"},
        "notes": "Reaches a phone without an enterprise chat contract, which is the "
                 "actual reason small teams keep a WhatsApp group.",
    },
    {
        "key": "webhook", "label": "Custom webhook", "category": "chat", "depth": NOTIFY,
        "auth": AUTH_WEBHOOK, "url_label": "Endpoint URL",
        "docs_url": "https://docs.adlc.dev/webhooks",
        "capabilities": ["Every platform event, HMAC-signed"],
        "verify": {"kind": "webhook_ping"},
        "notes": "Signed with the shared secret and retried — see `webhook_service`. "
                 "The escape hatch for anything not listed here.",
    },

    # ══ Monitoring and incidents ══════════════════════════════════════════════
    {
        "key": "sentry", "label": "Sentry", "category": "observe", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "Auth token", "token_hint": "sntrys_…",
        "docs_url": "https://docs.sentry.io/api/",
        "setup_url": "https://sentry.io/settings/account/api/auth-tokens/",
        "capabilities": ["Read issues", "Read releases"],
        "verify": {"url": "https://sentry.io/api/0/organizations/", "auth": "bearer"},
    },
    {
        "key": "pagerduty", "label": "PagerDuty", "category": "observe", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token",
        "docs_url": "https://developer.pagerduty.com/api-reference/",
        "capabilities": ["Read incidents", "Read on-call schedules"],
        "verify": {"url": "https://api.pagerduty.com/users?limit=1", "auth": "header",
                   "header": "Authorization", "prefix": "Token token="},
    },
    {
        "key": "opsgenie", "label": "Opsgenie", "category": "observe", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API key",
        "docs_url": "https://docs.opsgenie.com/docs/api-overview",
        "capabilities": ["Read alerts"],
        "verify": {"url": "https://api.opsgenie.com/v2/alerts?limit=1", "auth": "header",
                   "header": "Authorization", "prefix": "GenieKey "},
    },
    {
        "key": "datadog", "label": "Datadog", "category": "observe", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API key", "extra_label": "Application key",
        "docs_url": "https://docs.datadoghq.com/api/latest/",
        "capabilities": ["Read monitors", "Read metrics"],
        "verify": {"url": "https://api.datadoghq.com/api/v1/validate", "auth": "header",
                   "header": "DD-API-KEY"},
        "notes": "Most read endpoints also need an Application key; the validate "
                 "endpoint checks the API key alone, which is what connect-time "
                 "verification is for.",
    },
    {
        "key": "grafana", "label": "Grafana", "category": "observe", "depth": VERIFIED,
        "auth": AUTH_TOKEN_URL, "token_label": "Service account token",
        "url_label": "Grafana URL", "url_hint": "https://your-org.grafana.net",
        "docs_url": "https://grafana.com/docs/grafana/latest/developers/http_api/",
        "capabilities": ["Read dashboards"],
        "verify": {"url": "{base}/api/org", "auth": "bearer", "name_path": "name"},
    },
    {
        "key": "newrelic", "label": "New Relic", "category": "observe", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "User API key", "token_hint": "NRAK-…",
        "docs_url": "https://docs.newrelic.com/docs/apis/rest-api-v2/",
        "capabilities": ["Read applications"],
        "verify": {"url": "https://api.newrelic.com/v2/applications.json", "auth": "header",
                   "header": "Api-Key"},
    },

    # ══ Deploy and hosting ════════════════════════════════════════════════════
    {
        "key": "vercel", "label": "Vercel", "category": "deploy", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "Access token",
        "docs_url": "https://vercel.com/docs/rest-api",
        "setup_url": "https://vercel.com/account/tokens",
        "capabilities": ["Read projects", "Read deployments"],
        "verify": {"url": "https://api.vercel.com/v2/user", "auth": "bearer",
                   "name_path": "user.username"},
    },
    {
        "key": "netlify", "label": "Netlify", "category": "deploy", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "Personal access token",
        "docs_url": "https://docs.netlify.com/api/get-started/",
        "setup_url": "https://app.netlify.com/user/applications",
        "capabilities": ["Read sites", "Read deploys"],
        "verify": {"url": "https://api.netlify.com/api/v1/user", "auth": "bearer",
                   "name_path": "slug"},
    },
    {
        "key": "railway", "label": "Railway", "category": "deploy", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token",
        "docs_url": "https://docs.railway.com/reference/public-api",
        "capabilities": ["Read projects"],
        "verify": {"url": "https://backboard.railway.com/graphql/v2?query=%7Bme%7Bname%7D%7D",
                   "auth": "bearer", "name_path": "data.me.name"},
    },
    {
        "key": "render", "label": "Render", "category": "deploy", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API key", "token_hint": "rnd_…",
        "docs_url": "https://api-docs.render.com/reference/introduction",
        "capabilities": ["Read services", "Read deploys"],
        "verify": {"url": "https://api.render.com/v1/services?limit=1", "auth": "bearer"},
    },
    {
        "key": "flyio", "label": "Fly.io", "category": "deploy", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "Access token", "token_hint": "FlyV1 …",
        "docs_url": "https://fly.io/docs/machines/api/",
        "capabilities": ["Read apps", "Read machines"],
        "verify": {"url": "https://api.machines.dev/v1/apps?org_slug=personal", "auth": "bearer"},
    },
    {
        "key": "cloudflare", "label": "Cloudflare", "category": "deploy", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token",
        "docs_url": "https://developers.cloudflare.com/api/",
        "setup_url": "https://dash.cloudflare.com/profile/api-tokens",
        "capabilities": ["Read zones", "Read Pages projects"],
        "verify": {"url": "https://api.cloudflare.com/client/v4/user/tokens/verify",
                   "auth": "bearer", "name_path": "result.status"},
    },

    # ══ Security and code quality ═════════════════════════════════════════════
    {
        "key": "snyk", "label": "Snyk", "category": "security", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token",
        "docs_url": "https://docs.snyk.io/snyk-api",
        "capabilities": ["Read projects", "Read vulnerabilities"],
        "verify": {"url": "https://api.snyk.io/rest/self?version=2024-10-15", "auth": "header",
                   "header": "Authorization", "prefix": "token ", "name_path": "data.attributes.name"},
    },
    {
        "key": "sonarqube", "label": "SonarQube / SonarCloud", "category": "security", "depth": VERIFIED,
        "auth": AUTH_TOKEN_URL, "token_label": "User token",
        "url_label": "Server URL", "url_hint": "https://sonarcloud.io",
        "docs_url": "https://docs.sonarsource.com/sonarqube/latest/extension-guide/web-api/",
        "capabilities": ["Read quality gates", "Read issues"],
        "verify": {"url": "{base}/api/authentication/validate", "auth": "basic",
                   "basic_pass": "", "name_path": "valid"},
    },
    {
        "key": "semgrep", "label": "Semgrep", "category": "security", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token",
        "docs_url": "https://semgrep.dev/api/v1/docs/",
        "capabilities": ["Read findings"],
        "verify": {"url": "https://semgrep.dev/api/v1/deployments", "auth": "bearer"},
    },
    {
        "key": "codecov", "label": "Codecov", "category": "security", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token",
        "docs_url": "https://docs.codecov.com/reference/overview",
        "capabilities": ["Read coverage reports"],
        "verify": {"url": "https://api.codecov.io/api/v2/github", "auth": "header",
                   "header": "Authorization", "prefix": "bearer "},
    },

    # ══ Docs and knowledge ════════════════════════════════════════════════════
    {
        "key": "notion", "label": "Notion", "category": "docs", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "Internal integration secret", "token_hint": "ntn_…",
        "docs_url": "https://developers.notion.com/reference/intro",
        "setup_url": "https://www.notion.so/my-integrations",
        "capabilities": ["Read pages and databases"],
        "verify": {"url": "https://api.notion.com/v1/users/me", "auth": "bearer",
                   "extra_headers": {"Notion-Version": "2022-06-28"}, "name_path": "name"},
        "notes": "A ticket that links to a Notion spec is already read by `reader_service` "
                 "without any connection; this token is what reaches pages that are not public.",
    },
    {
        "key": "confluence", "label": "Confluence", "category": "docs", "depth": VERIFIED,
        "auth": AUTH_BASIC, "user_label": "Atlassian email", "token_label": "API token",
        "url_label": "Site URL", "url_hint": "https://your-team.atlassian.net/wiki",
        "docs_url": "https://developer.atlassian.com/cloud/confluence/rest/v2/",
        "capabilities": ["Read spaces and pages"],
        "verify": {"url": "{base}/rest/api/space?limit=1", "auth": "basic"},
    },
    {
        "key": "slab", "label": "Slab", "category": "docs", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "API token",
        "docs_url": "https://api.slab.com/",
        "capabilities": ["Read posts"],
        "verify": {"url": "https://api.slab.com/v1/graphql?query=%7Borganization%7Bname%7D%7D",
                   "auth": "header", "header": "Authorization"},
    },

    # ══ Design ════════════════════════════════════════════════════════════════
    {
        "key": "figma", "label": "Figma", "category": "design", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "Personal access token", "token_hint": "figd_…",
        "docs_url": "https://www.figma.com/developers/api",
        "setup_url": "https://www.figma.com/developers/api#access-tokens",
        "capabilities": ["Read files", "Read comments"],
        "verify": {"url": "https://api.figma.com/v1/me", "auth": "header",
                   "header": "X-Figma-Token", "name_path": "handle"},
        "notes": "A design-linked ticket is the most common thing an agent plans badly. "
                 "This is the credential that lets a skill fetch the frame it names.",
    },

    # ══ Payments ══════════════════════════════════════════════════════════════
    {
        "key": "razorpay", "label": "Razorpay", "category": "payments", "depth": VERIFIED,
        "auth": AUTH_BASIC, "user_label": "Key ID", "token_label": "Key secret",
        "docs_url": "https://razorpay.com/docs/api/",
        "setup_url": "https://dashboard.razorpay.com/app/website-app-settings/api-keys",
        "capabilities": ["Read payments", "Read subscriptions"],
        "verify": {"url": "https://api.razorpay.com/v1/payments?count=1", "auth": "basic"},
        "notes": "Present for the India billing path — UPI, cards and netbanking at "
                 "2% + GST domestic, and bank transfer at 1% + GST inbound.",
    },
    {
        "key": "stripe", "label": "Stripe", "category": "payments", "depth": VERIFIED,
        "auth": AUTH_TOKEN, "token_label": "Secret key", "token_hint": "sk_live_… / sk_test_…",
        "docs_url": "https://docs.stripe.com/api",
        "setup_url": "https://dashboard.stripe.com/apikeys",
        "capabilities": ["Read charges", "Read subscriptions"],
        "verify": {"url": "https://api.stripe.com/v1/customers?limit=1", "auth": "bearer"},
    },
]

BY_KEY: dict[str, dict] = {p["key"]: p for p in PLUGINS}


def get(key: str) -> dict | None:
    return BY_KEY.get((key or "").lower())


def known(key: str) -> bool:
    return (key or "").lower() in BY_KEY


def requires_url(key: str) -> bool:
    """
    Driven by whether the entry declares a URL field, not by the auth constant.

    The two are not the same, and assuming they were was a bug: Jira and
    Confluence authenticate with `basic` *and* need a site URL, so keying off
    the auth constant let a Jira connect pass validation with no URL and then
    fail deep inside the verifier on an un-substituted `{base}`. If the form
    collects a URL, the URL is required.
    """
    p = get(key)
    return bool(p and (p.get("url_label") or p["auth"] == AUTH_WEBHOOK))


def requires_user(key: str) -> bool:
    p = get(key)
    return bool(p and p["auth"] == AUTH_BASIC)


def requires_token(key: str) -> bool:
    p = get(key)
    return bool(p and p["auth"] in (AUTH_TOKEN, AUTH_TOKEN_URL, AUTH_BASIC))


def catalog() -> list[dict]:
    """
    The catalogue grouped by category, for the connect gallery.

    Contains no secrets and nothing workspace-specific — it describes what
    *could* be connected and is safe to serve to any authenticated user. The
    `verify` recipes are stripped: they are an internal implementation detail
    and publishing them just invites someone to probe vendors through us.
    """
    out = []
    for cat, label in CATEGORIES.items():
        members = [
            {k: v for k, v in p.items() if k not in ("verify", "category")}
            for p in PLUGINS if p["category"] == cat
        ]
        if members:
            out.append({"category": cat, "label": label, "plugins": members})
    return out


def counts() -> dict:
    """Headline numbers for the gallery, computed rather than claimed."""
    return {
        "total": len(PLUGINS),
        "native": len([p for p in PLUGINS if p["depth"] == NATIVE]),
        "notify": len([p for p in PLUGINS if p["depth"] == NOTIFY]),
        "verified": len([p for p in PLUGINS if p["depth"] == VERIFIED]),
        "categories": len(CATEGORIES),
    }
