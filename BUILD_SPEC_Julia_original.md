# 1. Vision & Use Cases

## 1.1 Target User

The primary target user is a **Community Notes Product Manager** who is responsible for monitoring the coverage and response time of Community Notes.

The Product Manager needs to understand how many eligible posts have received notes, how many posts remain uncovered, how quickly notes receive ratings, and how note helpfulness is distributed across different classifications.

## 1.2 Decision-Making Problem

The Product Manager currently faces challenges in understanding the overall coverage and response-time patterns of Community Notes.

Specifically, the Product Manager needs to identify:

- how many eligible posts have received notes and how many remain uncovered.
- How long it takes for eligible posts to receive their first note.
- How response times differ across note classifications.
- How rating activity and observed helpfulness vary across notes.

Instead of reviewing coverage, response-time, and rating information separately, the Product Manager needs a consolidated dashboard to compare these patterns across time periods and note classifications. The dashboard improves current monitoring practice by bringing these metrics into one place, allowing the Product Manager to identify observed coverage gaps, compare response-time patterns, and examine rating activity without manually reviewing multiple datasets. These observations help the Product Manager prioritize areas for further investigation, while the dashboard does not establish which interventions will improve outcomes.

## 1.3 Project Vision

The vision of the **Observed Coverage and Response-Time Monitor** is to provide a dashboard that helps Community Notes Product Managers monitor observed coverage, response times, and rating patterns.

The dashboard will bring together information from Note Request, Notes, Ratings, and Note Status History datasets to provide a clearer understanding of how Community Notes activity changes over time.

The dashboard is intended to support data-informed monitoring and help the Product Manager identify potential areas for further review. It is an observational tool and does not establish causal relationships between rating activity, note-writing effort, and response time.

## 1.4 Core Use Cases

### Use Case 1: Monitor Community Notes Coverage

**User selects/inputs:**
The Product Manager selects a date range and a feed eligibility definition.

**Dashboard shows:**
The dashboard displays the number of eligible posts, the number of eligible posts that received at least one note, and the number of eligible posts that remain uncovered. It also shows coverage patterns over time, based on distinct eligible tweetId values and notes created after eligibility.

**User decides:**
The Product Manager identifies periods or areas with observed coverage gaps and decides which areas may require further investigation or product attention.

### Use Case 2: Monitor Time to First Non-NMR

**User selects/inputs:**
The Product Manager selects a date range and one or more note classifications.

**Dashboard shows:**
The dashboard displays the time from note creation to the first non-Needs More Ratings status, using timestampMillisOfFirstNonNMRStatus. It summarizes this duration and compares patterns across note classifications and time periods.

**User decides:**
The Product Manager identifies notes or classifications with relatively longer times to reach a first non-Needs More Ratings status and decides whether those patterns warrant further investigation.

### Use Case 3: Understand Rating Activity and Observed Helpfulness

**User selects/inputs:**
The Product Manager selects a date range and, when applicable, one or more note classifications.

**Dashboard shows:**
The dashboard displays rating activity over time and the distribution of HELPFUL, SOMEWHAT_HELPFUL, and NOT_HELPFUL ratings. It also compares observed helpfulness across note classifications and allows the Product Manager to examine rating activity alongside response-time patterns.

**User decides:**
The Product Manager identifies differences in rating activity and observed helpfulness and decides which notes, classifications, or time periods may require additional analysis.

