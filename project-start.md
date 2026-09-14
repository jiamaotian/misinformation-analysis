# Project Starting Point

## Selected Project Area

Misinformation on Social Media — Social Platform / Trust and Safety

## Why Our Team Is Interested in It

Our team is interested in how social platforms can respond to potential misinformation through a community-based system rather than relying only on centralized moderation. We want to understand where the Community Notes process loses coverage or time and how data could help a Product Manager direct limited contributor effort more effectively without weakening note quality or broad agreement.

## Candidate Vision A — Improving Coverage

A Community Notes Product Manager at X must decide which groups of posts or note requests need targeted note-writing effort to reduce gaps in Community Notes coverage.

## Candidate Vision B — Improving Response Time

A Community Notes Product Manager at X must decide which types of notes need additional rating effort to reduce the time required to reach a final status.

## Core Data Source We Confirmed We Can Access

We confirmed access to the [X Community Notes public data](https://communitynotes.x.com/guide/en/under-the-hood/download-data) without a login. The team successfully opened TSV data for Notes, Note Requests, and Note Status History using Python and pandas. The tested tables contain `tweetId` and `noteId`, providing a potential join path from requests to notes and from notes to status histories. The Ratings data still needs to be inspected.

## Three Questions We Still Need to Resolve

1. How should we define and measure a “coverage gap”? For example, should we focus on note requests that remain unanswered, posts that receive notes but never reach a final status, or specific types of posts with consistently low coverage?
2. How can we identify which potentially misleading posts are least likely to receive a Community Note?
3. How should we distinguish notes that remain unresolved because they have too few ratings from notes that have enough ratings but lack broad agreement, and what status should count as a final status?
