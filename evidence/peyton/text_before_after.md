# Text preservation and five independent record checks

Expectations were saved before preparation. All source strings were intentionally preserved; no unsupported text repairs were applied.

| Case | Field | Before (JSON quoted) | After (JSON quoted) | Matches |
|---|---|---|---|---|
| ordinary | raterParticipantId | "C4F546539DE2DAD1DE53FAAE782A1A2AE4D584E486738F1D3C58D85FF0338953" | "C4F546539DE2DAD1DE53FAAE782A1A2AE4D584E486738F1D3C58D85FF0338953" | Yes |
| ordinary | helpfulnessLevel | "HELPFUL" | "HELPFUL" | Yes |
| ordinary | suggestion | "" | "" | Yes |
| ordinary | ratedOnTweetId | "2021236742460756143" | "2021236742460756143" | Yes |
| ordinary | suggestionId | "-1" | "-1" | Yes |
| post_sentinel | raterParticipantId | "19698311EA41B0D497639572086AA178D94342FEAE756D57BE8814E5DCAFAD94" | "19698311EA41B0D497639572086AA178D94342FEAE756D57BE8814E5DCAFAD94" | Yes |
| post_sentinel | helpfulnessLevel | "HELPFUL" | "HELPFUL" | Yes |
| post_sentinel | suggestion | "" | "" | Yes |
| post_sentinel | ratedOnTweetId | "-1" | "-1" | Yes |
| post_sentinel | suggestionId | "-1" | "-1" | Yes |
| whitespace_suggestion | raterParticipantId | "D3D21AB0B9897B960D8B6F3F20584ABC82E52A65EDA5764EF4AD553E32190397" | "D3D21AB0B9897B960D8B6F3F20584ABC82E52A65EDA5764EF4AD553E32190397" | Yes |
| whitespace_suggestion | helpfulnessLevel | "SOMEWHAT_HELPFUL" | "SOMEWHAT_HELPFUL" | Yes |
| whitespace_suggestion | suggestion | "        " | "        " | Yes |
| whitespace_suggestion | ratedOnTweetId | "2013014195281793492" | "2013014195281793492" | Yes |
| whitespace_suggestion | suggestionId | "-1" | "-1" | Yes |
| nonempty_suggestion | raterParticipantId | "E8CE52D7EFE476D7F637B5F2C0CB4AD83C57D5A79D1636903856502B6F126CF3" | "E8CE52D7EFE476D7F637B5F2C0CB4AD83C57D5A79D1636903856502B6F126CF3" | Yes |
| nonempty_suggestion | helpfulnessLevel | "NOT_HELPFUL" | "NOT_HELPFUL" | Yes |
| nonempty_suggestion | suggestion | "He’s racist " | "He’s racist " | Yes |
| nonempty_suggestion | ratedOnTweetId | "2020875282702270656" | "2020875282702270656" | Yes |
| nonempty_suggestion | suggestionId | "-1" | "-1" | Yes |
| leading_zero_participant | raterParticipantId | "0281A3E88C3C226058BEE76E1CF5061FC8A6D553ACEA0BF7ED8BD4D1CBA8E939" | "0281A3E88C3C226058BEE76E1CF5061FC8A6D553ACEA0BF7ED8BD4D1CBA8E939" | Yes |
| leading_zero_participant | helpfulnessLevel | "HELPFUL" | "HELPFUL" | Yes |
| leading_zero_participant | suggestion | "" | "" | Yes |
| leading_zero_participant | ratedOnTweetId | "2021236742460756143" | "2021236742460756143" | Yes |
| leading_zero_participant | suggestionId | "-1" | "-1" | Yes |

All five dates and flags also matched; see `record_checks.json` for original, expected, actual, and reasons.
