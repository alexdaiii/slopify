---
name: zotero-local
description: Access the user's local Zotero library from the sandbox — check it is running, get the full text of any stored document (paper, book chapter, report, preprint, regulatory/clinical text) via the local API /fulltext endpoint, look up items by key/metadata, and read figures from the underlying PDF. Use whenever needed text is not freely available online — not only for NCBI/PMC/PubMed misses but for paywalled papers, books, grey literature, or anything the user is more likely to have in their own Zotero. Also covers how the user should save attachments so full text is retrievable.
---

# Accessing the local Zotero library

Zotero 7+ ships a built-in **local HTTP API** (mirrors the Zotero Web API) on
port **23119**. From inside the sandbox the host is reached via
`host.docker.internal`; on the host itself it is `localhost`.

```
BASE=http://host.docker.internal:23119     # from the sandbox
BASE=http://localhost:23119                 # from the host
```

> **Treat Zotero as READ-ONLY while this skill is invoked.** Use **GET only**.
> Do **not** send `POST`/`PUT`/`DELETE` to any `/api/...` or `/connector/...`
> endpoint — those mutate the user's library (the connector `saveItems`,
> `saveSnapshot`, `import`, `installStyle`, `updateSession` endpoints add or change
> items; data-API writes edit/delete them). This is the user's real reference
> library; never write to it unless they explicitly ask. Everything this skill
> needs (search, metadata, full text) is a GET.

## 1. Check Zotero is running

```bash
curl -s -m 8 -o /dev/null -w "%{http_code}\n" http://host.docker.internal:23119/connector/ping
```

- **200** (body `<html><body>Zotero is running</body></html>`) → good, proceed.
- **Connection refused / timeout / non-200** → Zotero is not reachable.

### If it is NOT running — suggested fixes (ask the user to do these on the host)

1. **Launch the Zotero desktop app.** The local API only exists while the app is
   open — there is no headless daemon.
2. **Confirm the local API/connector is enabled.** Zotero → Settings/Preferences →
   **Advanced** → check *"Allow other applications on this computer to communicate
   with Zotero"* (the connector/local API). 
3. **Port 23119 must be free** and not blocked. If another Zotero-compatible app
   grabbed the port, quit it and restart Zotero.
4. **Sandbox networking:** the sandbox reaches host services via
   `host.docker.internal`, not `localhost`. If even `connector/ping` times out
   while Zotero is clearly running, confirm `host.docker.internal` resolves and
   that `localhost:23119` is allowed in the sandbox network policy.

## 2. Find the item / attachment key

The full-text endpoint is keyed by the **attachment** item, not the parent paper.

```bash
# list items (each attachment has its own key; filter to PDFs/snapshots)
curl -s -m 10 "http://host.docker.internal:23119/api/users/0/items?limit=100&format=json" \
  | python3 -c "
import sys,json
for it in json.load(sys.stdin):
    d=it.get('data',{}); ct=d.get('contentType')
    if ct in ('application/pdf','text/html'):
        print(it['key'],'|',ct,'|',d.get('filename'))
"
```

Useful lookups: `?q=<search>`, `?itemType=...`, and per-item metadata at
`/api/users/0/items/<KEY>?format=json` (the attachment JSON also carries a `url`
field = the original source URL, often an open-access link you can fetch directly).

### Search the whole library by content — `q` + `qmode=everything`

`qmode=everything` searches **inside the indexed body text**, not just metadata —
so you can find which saved papers discuss a variant/term without knowing keys.
(Verified: a body-only term like `HeLa-TKO` is found in `everything` mode but
returns nothing in `qmode=titleCreatorYear`, which is metadata-only.)

```bash
# which items mention this term anywhere (incl. full text)? -> attachment/item keys
curl -s "http://host.docker.internal:23119/api/users/0/items?q=V1538M&qmode=everything&format=keys"
```

Workflow: full-text-search to get keys → `/fulltext` on a hit to read it. This
turns the library into a searchable corpus. `qmode=titleCreatorYear` restricts to
metadata when you want a narrow title/author/year match instead.

## 3. Get the full text — `/fulltext` (the route that works from the sandbox)

```bash
curl -s -m 12 "http://host.docker.internal:23119/api/users/0/items/<KEY>/fulltext"
# -> {"content": "<full extracted text>", "indexedPages": N, "totalPages": M}
```

Read `.content` — it is the full extracted body text over plain HTTP. No PDF
binary and no mounted filesystem are needed. This is the preferred way to *read*
a paper out of Zotero from the sandbox.

```bash
# convenience: dump just the text
curl -s "http://host.docker.internal:23119/api/users/0/items/<KEY>/fulltext" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['content'])"
```

### Do NOT use the file-bytes endpoint from the sandbox

`GET /api/users/0/items/<KEY>/file` returns **HTTP 302** redirecting to a
`file:///.../Zotero/storage/<KEY>/<file>` path on the **host**, which is not
mounted in the sandbox → 0 bytes. The local API does not stream local file bytes
over HTTP. Always use `/fulltext` instead.

## Reading the content — text vs figures

**`/fulltext` is already plain text** (Zotero extracted it). Read it directly —
do **not** run it through markitdown or any PDF-to-text converter; there is no PDF
binary in this path and conversion would only mangle it.

- **Text, quotes, grepping for a variant/term** → use `/fulltext`. It is the
  complete body text and is all you need to read the prose and pull verbatim
  sentences.
- **Figures / images** (gels, blots, dose-response or Ca²⁺-release traces,
  structure panels, lollipop plots) → `/fulltext` does NOT contain these; it only
  has the sentences describing them. To actually see a figure you need the real
  PDF. Since Zotero's file bytes are unreachable from the sandbox (see above), ask
  the user to drop the PDF into `~/Documents` (the one mounted path), then **read
  it with Claude's native PDF support** (the `Read` tool ingests PDFs visually,
  preserving figures). Prefer native PDF reading over markitdown, which is
  text-only and discards every figure.
- **markitdown** is only a niche fallback — a very large PDF where you want cheap
  text-only output and `/fulltext` is unavailable. For normal reading it is not
  needed.

**There is no API route that returns a paper's figures.** Figures are embedded in
the PDF; the local API exposes no image/figure extraction. The only image-like
items it returns are user-drawn PDF **annotations** (`itemType=annotation`, via the
`children` endpoint), and even those store their cached PNG on disk behind the
unreachable `file://` path. So a figure can only be seen by reading the actual PDF
(drop it in `~/Documents`, read natively).

## Brief API schema (verified — Zotero 9.0.3, `Zotero-Api-Version: 3`)

Local server mirrors the Zotero Web API v3. Use `users/0` for the default local
library (responses echo the real numeric library id, which also works).

| Endpoint (prefix `/api/users/0`) | Returns |
|---|---|
| `/items` | all items (array). See query params below |
| `/items/top` | top-level items only (excludes child attachments/notes) |
| `/items/trash` | items in the trash |
| `/items/<KEY>` | one item |
| `/items/<KEY>/children` | child items: attachments, notes, annotations |
| `/items/<KEY>/fulltext` | `{"content","indexedPages","totalPages"}` — **the read route** |
| `/items/<KEY>/file` | **302 → `file://` (unreachable in sandbox) — do not use** |
| `/tags`, `/items/tags` | all tags / tags in use (library here has ~510) |
| `/collections`, `/collections/top` | collection tree |
| `/searches` | saved searches |
| `/publications/items` | "My Publications" |
| `/groups`, `/settings` | group libraries; library settings |

**`/items` query params:** `limit`, `start` (paginate) · `q` + `qmode`
(`everything` = full text, `titleCreatorYear` = metadata) · `itemType` (supports
exclusion/boolean, e.g. `-attachment`) · `tag` · `sort` (`dateModified`, …) +
`direction` · `since` (use with `format=versions` for sync deltas).

**`format=`** (export): `json`, `keys`, `versions`, `bibtex`, `ris`, `csljson`,
`mods`, `coins`, `wikipedia`, `tei`, `bib` (with `style=<csl>`, e.g. `apa`). Or
bundle into JSON with `include=data,citation,bib&style=apa`.
(`rdf_bibliontology` errors.)

**Schema/metadata (no library segment):** `/api/schema` (full Zotero schema,
`version`, `itemTypes`, `meta`, `csl`, `locales`), `/api/itemTypes`,
`/api/itemFields`, `/api/creatorFields`, `/api/itemTypeFields?itemType=…`,
`/api/itemTypeCreatorTypes?itemType=…`.

**`/connector/…`** exists (`ping` = the health check) but is otherwise
**POST/write-oriented** — off-limits for this read-only skill (see the guard at
top). Better BibTeX RPC endpoints are only present if that plugin is installed.

Item JSON shape: `{key, version, library, links{self,alternate,up,enclosure},
meta{...}, data{...}}`. For an **attachment**, `data` holds `itemType="attachment"`,
`contentType` (`application/pdf`\|`text/html`), `filename`, `linkMode`, `md5`,
`mtime`, and `url` (original source URL — often an open-access link worth fetching
directly). Pagination: read the `Total-Results` header and the `Link` header
(`rel="next"`/`"last"`), or page manually with `start`/`limit`.

## 4. How the user should save attachments (so `/fulltext` returns the body)

`/fulltext` returns Zotero's full-text **index** of an attachment, so it only
works if that attachment actually contains indexable text:

- **Recommended: save the full-text PDF.** PDFs with a real text layer index
  cleanly and completely. **When saving to Zotero, recommend saving the article
  as a PDF** — it is the most reliable source for `/fulltext`.
- **HTML snapshots also work**, but only index the text on the page that was
  saved.
- **Will not index:** scanned/image-only PDFs (no text layer, would need OCR), and
  attachments Zotero has not finished indexing yet.

If `/fulltext` comes back empty for an item that should have text, the attachment
is likely image-only or an abstract-only snapshot — ask the user to re-save it as
a full-text **PDF**.

## When to reach for Zotero

Use this whenever the text you need is not freely available online — this is **not
limited to NCBI/PMC/PubMed misses**. In particular, reach for Zotero when a source
is **not open access / requires a subscription or institutional login** (the user
has already authenticated and saved it), as well as for books and book chapters,
theses, reports, grey literature, regulatory/clinical documents, and anything the
user is more likely to have curated in their own library than to be openly
downloadable.

Recommended retrieval order for a given document:

1. Zotero `/fulltext` for the attachment key (this skill) — reads the body text.
2. The attachment's `url` field, if it points at an open-access source.
3. For figures, or if text did not index: ask the user to drop the PDF into
   `~/Documents` and read it natively (see *Reading the content* above), or to
   re-save the item as a full-text PDF.
