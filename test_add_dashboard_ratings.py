import pandas as pd
from add_dashboard_ratings import merge_ratings


def test_duplicate_and_conflicting_pairs():
    columns=['noteId','raterParticipantId','createdAtMillis','helpfulnessLevel']
    old=pd.DataFrame([['1','a','100','HELPFUL'],['2','b','200','HELPFUL']],columns=columns)
    new=pd.DataFrame([['1','a','100','HELPFUL'],['2','b','200','NOT_HELPFUL'],['3','c','300','HELPFUL']],columns=columns)
    result,duplicates,conflicts=merge_ratings(old,new)
    assert duplicates==1
    assert conflicts==2
    assert result.noteId.tolist()==['1','3']
    assert len(old)==2
