# Alternatives Investigation

**Name:** Yoojin Hwang  
**Project Area:** Misinformation on Social Media — Social Platform / Trust and Safety

## Candidate Vision A — Improving Coverage

A Community Notes Product Manager at X must decide which groups of posts or note requests need targeted note-writing effort to reduce gaps in Community Notes coverage.

## Candidate Vision B — Improving Response Time

A Community Notes Product Manager at X must decide which types of notes need additional rating effort to reduce the time required to reach a final status.

---

## Vision A: Improving Coverage

### How Might the Product Manager Make This Decision Today?

This decision might be triggered when the team notices that many note requests have not received a note. Without a new coverage-analysis tool, the Product Manager could compare the existing Note Requests and Notes data to identify requested posts that did not receive any notes.

The Product Manager might work with data analysts or other Community Notes staff to review these patterns. The team could identify unanswered requests, group them using the information available in the data, and compare coverage across those groups. Existing Community Notes features allow requested posts to be brought to the attention of Community Notes contributors when enough requests are received. The Product Manager could review whether lower-coverage groups receive more notes over time. This is a possible process, but the public documentation does not confirm that X currently follows these exact steps.

### Where Might the Process Be Difficult or Uncertain?

The public data may show which requested posts received a note, but it may not provide enough information about the original posts to create meaningful groups. For example, topic, language, and content type may be missing. This would make it difficult to determine whether a specific group actually has lower coverage.

It is also unclear whether a request without a note represents a true coverage problem. A post may remain unanswered because contributors did not see the request, did not have enough knowledge to write a note, or believed that a note was not needed. In addition, we have not verified how X currently reviews coverage gaps or decides which requests to show more often to contributors.

### Three Google Searches

1. How are Community Note requests shown to contributors on X?
2. What information is included in the Community Notes Note Requests and Notes data?
3. Can Community Notes contributors see posts that have requested a note?

### Evidence Supporting or Challenging This Process

The Community Notes guide states that when a post receives enough requests, contributors will see an alert and can choose to propose a note. This confirms that requested posts can be brought to contributors’ attention.

The public-data guide describes the Note Requests data as requests for a Community Note that were shown to contributors. This supports the possibility of reviewing requested posts and studying which requests receive notes.

However, these sources do not confirm that X Product Managers currently group requests by coverage level or follow the exact decision process described above.

### Sources

- [Requested a Community Note](https://communitynotes.x.com/guide/en/under-the-hood/note-requests)
- [Downloading Community Notes Data](https://communitynotes.x.com/guide/en/under-the-hood/download-data)

## Vision B: Improving Response Time

### How Might the Product Manager Make This Decision Today?

This decision might be triggered when the team notices that some notes remain unresolved for a long time. Without a new response-time tool, the Product Manager could review the existing Ratings and Note Status History data to identify notes that have stayed in an unresolved status and compare how many ratings they have received.

The Product Manager might work with data analysts or other Community Notes staff to examine these patterns. The team could first identify notes that have not reached a clear status, measure how long they have remained unresolved, and compare their rating activity. Notes with few ratings could be separated from notes that have received more ratings but still lack agreement among contributors. Based on this review, the Product Manager could decide which types of notes may need additional rating attention and later check whether they reach a status more quickly. This is a possible process, but the public documentation does not confirm that X currently follows these exact steps.

### Where Might the Process Be Difficult or Uncertain?

A note can remain unresolved for different reasons. Some notes may have too few ratings, while others may have many ratings but still lack agreement among contributors with different perspectives. Because of this, a low number of ratings cannot be treated as the only reason for a delay.

The team would also need to decide which status counts as a final status and when response time should begin. In addition, the public data may show when ratings were submitted, but it may not show how often a note was displayed to eligible contributors. Without that information, it may be difficult to know whether a note received few ratings because it was not shown often or because contributors chose not to rate it.

### Three Google Searches

1. How does Community Notes use ratings and agreement to determine a note’s status?
2. What information is included in the Community Notes Ratings and Note Status History data?
3. How are notes that need more ratings shown to Community Notes contributors?

### Evidence Supporting or Challenging This Process

The Community Notes ranking guide explains that the scoring system is designed to identify notes that are helpful to people from different points of view. This supports the idea that the scoring process considers more than the total number of ratings.

The public-data guide states that the Note Status History file contains information derived from notes and ratings, along with the outputs of the note-scoring algorithm. It also documents a timestamp for when a note received its current status, including “Needs More Ratings.” This supports the possibility of studying how long notes remain unresolved.

The Needs Your Help ranking guide states that contributors see a prompt to help rate proposed notes. This confirms that Community Notes has an existing way to bring proposed notes to contributors for ratings.

However, the sources do not confirm that X Product Managers currently classify delayed notes using the process described above. They also do not show that receiving more ratings will always make a note reach a clear status faster.

### Sources

- [Note Ranking Algorithm](https://communitynotes.x.com/guide/en/under-the-hood/ranking-notes)
- [Downloading Community Notes Data](https://communitynotes.x.com/guide/en/under-the-hood/download-data)
- [Needs Your Help Ranking](https://communitynotes.x.com/guide/en/under-the-hood/timeline-tabs)