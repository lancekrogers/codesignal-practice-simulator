# Build festivals

These are sanitized snapshots of the three completed festivals used to build the
simulator, copied from the JobSearch campaign's completed festival archive.
They show [Festival](https://fest.build/) in use: requirements, decisions,
execution, reviews, and verification kept with the work. See the
[Festival source repository](https://github.com/Obedience-Corp/festival) and
[quickstart](https://docs.fest.build/getting-started/quickstart/) to try the
workflow on your own project.

| Festival | Scope |
| --- | --- |
| [CP0001 — Practice simulator](codesignal-practice-simulator-CP0001/FESTIVAL_OVERVIEW.md) | Python CLI, scoring, timed attempts, and study material |
| [CB0001 — Browser assessment simulator](codesignal-browser-assessment-simulator-CB0001/FESTIVAL_OVERVIEW.md) | Local browser IDE and shared application backend |
| [CP0002 — Practice library](codesignal-practice-library-CP0002/FESTIVAL_OVERVIEW.md) | Original exercises, repeatable attempts, history, and submission review |

Each snapshot retains requirements, plans, task records, review and verification
evidence, festival configuration, and `.fest` progress data.
All three festivals include build replay GIFs. CP0001's replay was generated
from its preserved progress records after the archives were published.

For public sharing, local home and campaign paths use neutral placeholders;
activity records omit actor usernames and hostnames. Empty lock files and raw
judge logs are omitted. The CP0001 campaign-integration transcript is replaced
with a historical result summary, and unrelated repository names are omitted.
The archived migration manifest retains user-authored and vendor provenance
records, with local environment inventory removed. Summary counts still describe
the original inventory. The application runtime manifest is unchanged.

Historical commands, project links, and commit references describe the
campaign workspace at the time of the build;
these archives are not active work queues or instructions for running the app.
Markdown whitespace is normalized for the repository checks; explicit `<br>`
breaks preserve historical hard line breaks.
See the [project README](../README.md) for current usage.
