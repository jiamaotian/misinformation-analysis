# **Vision A — Improving Coverage**
## A Community Notes Product Manager at X must decide which groups of posts or note requests **need targeted note-writing effort** to **reduce gaps in Community Notes coverage**.

## **Supported**

The data can identify which posts were eligible for Community Notes and which posts actually received notes.  
`batSignals` provides tweetId and note-request/feed eligibility timestamps, while `notes` links each note to a tweetId and provides note creation time and note characteristics.  
Therefore, we can analyze patterns such as:  

Which observed posts received Community Notes?
How long after becoming eligible was a note created?
How many notes were created for observed eligible posts?

We can also examine the characteristics of notes that were created, such as `classification`, `isMediaNote`, and `isCollaborativeNote`.   
 

## **Partly supported**

We can measure observed note coverage among the posts represented in the available data and examine how coverage varies with the observable information available in `batSignals`, such as Note Request Feed eligibility and timing.

However, note characteristics such as `classification` are only available for posts that received a note. Therefore, they cannot be used to characterize posts that did not receive notes.


## **Outside the data's scope**

We cannot determine whether an uncovered post actually needs a Community Note or whether the lack of a note represents an unmet need.

We also cannot reliably determine which groups of uncovered posts should receive targeted note-writing effort because the available data does not provide enough substantive post-level characteristics to meaningfully segment these posts into actionable groups.

Finally, we cannot conclude that increasing note-writing effort for a particular group would causally improve coverag. The data is observational and does not contain an intervention or counterfactual that would allow us to measure the causal effect of additional note-writing effort.

## **conclution**

The available data allows us to measure observed Community Notes coverage and identify posts that did not receive a note. However, the data does not provide enough information to determine whether uncovered posts actually need a Note or to meaningfully identify which groups should receive targeted note-writing effort. Therefore, the data can support identifying potential coverage gaps, but not fully support the decision of where to allocate additional note-writing effort. 

# **Vision B — Improving Response Time**
## A Community Notes Product Manager at X must decide which types of notes **need additional rating effort** to **reduce the time required to reach a final status**.

## **Supported**

`ratings` records when ratings were submitted, who submitted them, and how each note was evaluated. `noteStatusHistory` records important status milestones, including when a note first moved beyond NEEDS_MORE_RATINGS.

Therefore, we can calculate and compare metrics such as:

Number of ratings received by a note
Rating activity and rating arrival over time
Time from note creation to its first non-NMR status
Time from note creation to its current or latest status
Rating activity in relation to response time
Response time across different note characteristics

`userEnrollment` can also provide contributor-level information that allows us to examine rating activity across different contributor populations or enrollment groups.

## **Partly supported**

We can prioritize note types that:

have relatively long response times,
receive relatively few or slow-arriving ratings, and
show an observed association between greater/faster rating activity and faster status progression.

We can also compare response time and rating activity across note characteristics such as classification, isMediaNote, and rating helpfulness or disagreement patterns.

This allows us to move from simply identifying slow notes to making a data-informed prioritization of where additional rating effort may be most valuable.

However, the observational data cannot tell us exactly how much additional rating effort would be needed to achieve a specific reduction in response time.

## **Outside the data's scope**

We cannot conclude that increasing the number of ratings causes a note to reach a final status faster.

For example, notes that receive ratings quickly may also be easier to evaluate, less controversial, or different in other ways that independently affect response time. Therefore, an observed relationship between rating activity and response time does not by itself establish a causal effect.

Testing whether additional rating effort actually reduces response time would require an intervention, experiment, or stronger quasi-experimental design that is not available in the current observational data. 

## **Conclution**

The available data allows us to measure rating activity and response time and examine their associations across different types of notes. However, the data cannot establish that additional rating effort would cause faster status resolution or determine the optimal amount of additional effort needed. Therefore, the data can support a data-informed prioritization of where rating effort may be most valuable, but not a causal estimate of the impact of that intervention.