# Auxiliary Data Investigation

**Name:** Peyton Tom  
**Project Area:** Misinformation on Social Media — Social Platform / Trust and Safety

## Candidate Vision A — Improving Coverage

A Community Notes Product Manager at X must decide which groups of posts or note requests need targeted note-writing effort to reduce gaps in Community Notes coverage.

## Candidate Vision B — Improving Response Time

A Community Notes Product Manager at X must decide which types of notes need additional rating effort to reduce the time required to reach a final status.

---

## Vision A: Improving Coverage

### Important information missing from the core data

The Community Notes data identify posts using a `tweetId`, but we still need information about the original posts themselves. In particular, we need each post’s topic, language, text, and level of engagement.

Without this information, we could determine that certain posts did not receive notes, but we might not be able to identify meaningful coverage gaps. For example, we could not determine whether posts about elections, public health, or another topic are less likely to receive notes.

### Promising auxiliary data source

A promising source is the **X API Post Lookup endpoint**, which is operated by X. The API documentation indicates that post records may include fields such as the post ID, text, language, creation time, context annotations, and public engagement metrics.

**Source:** [X API — Get Posts by IDs](https://docs.x.com/x-api/posts/get-posts-by-ids)

### What one row would represent

One row would represent one X post.

Possible fields could include:

- `tweetId`
- `text`
- `lang`
- `created_at`
- `topic` or `context_annotation`
- `impression_count`
- `like_count`
- `reply_count`
- `repost_count`

### How it would connect to the core data

The auxiliary post data could be joined to the Community Notes notes and note-request data using `tweetId`.

After connecting the tables, the team could group posts by topic, language, or engagement level and calculate measures such as:

- Percentage of requested posts that received at least one note
- Average time between a note request and the first written note
- Number of posts without notes in each topic or language
- Whether highly viewed posts receive notes faster than posts with less engagement

### New question this data would make answerable

This addition would allow us to ask:

> Which topics, languages, or levels of post engagement have the largest gaps between requests for notes and notes actually being written?

### What could fail or remain uncertain

Some posts may have been deleted, made private, or otherwise become unavailable. API access may also have pricing, rate, or permission restrictions. Topic classifications may be missing or inaccurate, and engagement counts may change over time.

It is also important not to assume that every post without a note contains misinformation. A lack of coverage only indicates that a note was not written, not that the post was misleading.

### Synthetic alternative

If the API data are unavailable, we could create a small synthetic table with fields such as:

| tweetId | topic | language | impression_group |
|---|---|---|---|
| 101 | Elections | English | High |
| 102 | Public health | Spanish | Medium |
| 103 | Finance | English | Low |

This synthetic table could demonstrate how post information would connect to the Community Notes data. However, it would only test the analysis process and would not provide evidence about actual coverage gaps.

---

## Vision B: Improving Response Time

### Important information missing from the core data

The public ratings data show which ratings were submitted and when they were submitted. However, they do not show which contributors were given an opportunity to rate a particular note.

Because of this, a note with few ratings could mean that it was not shown to enough eligible contributors, that contributors saw it but chose not to rate it, or that there were not enough active contributors available at that time.

### Promising auxiliary data source

A promising addition would be X’s internal Community Notes recommendation or impression logs. X would collect these data when a note is displayed to an eligible contributor in the rating interface.

This source may not be publicly available, so access would likely require permission from X and privacy protections for contributors.

### What one row would represent

One row would represent one instance in which a note was shown to a contributor as an opportunity to rate it.

Possible fields could include:

- `noteId`
- `participantId` or an anonymized contributor ID
- `shownAtMillis`
- `ratingSubmitted`
- `ratedAtMillis`
- `contributor_language`
- `contributor_modeling_group`
- `recommendation_location`

### How it would connect to the core data

The impression data could connect to the ratings and note-status-history tables using `noteId`. If privacy rules permit, the anonymized contributor identifier could also connect to contributor enrollment data using `participantId`.

This would allow us to compare:

- Number of times a note was shown
- Number of ratings the note received
- Percentage of impressions that resulted in ratings
- Time from note creation to its first rating
- Time from note creation to a final status
- Availability of raters from different contributor groups

### New question this data would make answerable

This addition would allow us to ask:

> Are slow notes unresolved because they were shown to too few contributors, because contributors did not respond, or because the submitted ratings lacked broad agreement?

This distinction would help the product manager decide whether a note needs greater distribution, more contributor outreach, or additional ratings from contributors with different perspectives.

### What could fail or remain uncertain

These internal logs may not be available to our team. They could also create privacy concerns because they describe individual contributor behavior. Contributor identifiers would need to be anonymized, and the team should report group-level patterns rather than evaluate individual contributors.

Being shown a note also does not prove that the contributor carefully read it. Therefore, an impression should be treated as an opportunity to rate, not proof of attention.

### Synthetic alternative

If X’s internal impression data are unavailable, we could create a small synthetic table such as:

| noteId | times_shown | ratings_received | distinct_groups_reached |
|---|---:|---:|---:|
| 201 | 100 | 8 | 2 |
| 202 | 20 | 15 | 5 |
| 203 | 80 | 45 | 6 |

This could demonstrate the difference between limited exposure, low response, and possible disagreement. However, it would not provide real evidence about why actual Community Notes remain unresolved.

---

## What We Checked

We reviewed the following sources:

- [Community Notes public data](https://communitynotes.x.com/guide/en/under-the-hood/download-data)
- [Community Notes note-ranking process](https://communitynotes.x.com/guide/en/under-the-hood/ranking-notes)
- [Community Notes open-source code](https://github.com/twitter/communitynotes)
- [X API Post Lookup documentation](https://docs.x.com/x-api/posts/get-posts-by-ids)

The public Community Notes data provide notes, ratings, status information, contributor information, and note-request information that can be connected through identifiers such as `noteId`, `tweetId`, and `participantId`.

## What Remains Uncertain

We still need to determine:

1. Whether our team can obtain post-level information from the X API within its access and pricing restrictions.
2. Whether deleted or unavailable posts would create a biased picture of coverage.
3. Whether any contributor-impression or note-recommendation data are publicly accessible.
4. Which Community Notes statuses our team will define as final.
5. How we will measure broad agreement separately from simply having a large number of ratings.

## Sourced Facts Versus Hypotheses

The descriptions of the public Community Notes files, ranking process, and available X API post fields are based on the linked documentation.

The proposed uses of post metadata and internal impression logs are project hypotheses. We have not confirmed that X would provide internal impression data or that these additions would fully explain coverage and response-time differences.
