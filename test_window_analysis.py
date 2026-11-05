import pandas as pd
import pytest
from window_analysis import response_analysis, coverage_backend

BASE = pd.Timestamp('2026-01-01T00:00:00Z')
MS = BASE.value//1000000


def fixture():
    notes=[]
    for i,hours in enumerate([2,10,30,169,None],1):
        notes.append(dict(noteId=str(i),tweetId=str(i),createdAtMillis=str(MS),createdAtMillis_status=str(MS),
            classification='A',isMediaNote='0',isCollaborativeNote='0',
            timestampMillisOfFirstNonNMRStatus=str(MS+int(hours*3600000)) if hours is not None else '-1',
            firstNonNMRStatus='CURRENTLY_RATED_HELPFUL' if hours is not None else '',
            currentStatus='CURRENTLY_RATED_HELPFUL' if hours is not None else 'NEEDS_MORE_RATINGS',
            qc_response_eligible='True' if hours is not None else 'False',qc_status_time_inconsistent='False',qc_negative_latency='False'))
    ratings=pd.DataFrame([dict(noteId='1',createdAtMillis=str(MS+3600000),qc_key_valid='True',
        helpfulnessLevel=level,qc_valid_helpfulness=str(level in ['HELPFUL','SOMEWHAT_HELPFUL','NOT_HELPFUL']))
        for level in ['HELPFUL']*7+['SOMEWHAT_HELPFUL']+['NOT_HELPFUL']*2+['']*3])
    return pd.DataFrame(notes),ratings


def run(notes,ratings,window=7):
    return response_analysis(notes,ratings,cutoff='2026-02-01T00:00:00Z',window=window,
        start='2026-01-01T00:00:00Z',end='2026-01-02T00:00:00Z',classifications=['A'])


def test_response_acceptance_and_helpfulness():
    notes,ratings=fixture()
    cohort,summary,helpfulness,diagnostics=run(notes,ratings)
    assert len(cohort)==5
    assert cohort.completed.sum()==3
    assert cohort.response_hours.median()==10
    assert helpfulness.ratings.sum()==10
    assert helpfulness.iloc[0]['percent']==70
    assert diagnostics['excluded_rating_levels']==3
    assert cohort.iloc[0].early_ratings==13
    assert run(notes,ratings,14)[0].completed.sum()==4


def test_missing_and_inconsistent_history_not_unresolved():
    notes,ratings=fixture()
    notes.loc[0,'currentStatus']=None
    notes.loc[1,'createdAtMillis_status']=str(MS-1)
    notes.loc[4,'currentStatus']='CURRENTLY_RATED_HELPFUL'
    cohort,_,_,diagnostics=run(notes,ratings)
    assert len(cohort)==2
    assert diagnostics['excluded_mature_history']==3


def test_boundaries_and_empty():
    notes,ratings=fixture()
    notes.loc[0,'timestampMillisOfFirstNonNMRStatus']=str(MS+7*86400000)
    ratings.loc[0,'createdAtMillis']=str(MS+24*3600000)
    cohort,_,_,_=run(notes,ratings)
    assert cohort.iloc[0].completed
    assert cohort.iloc[0].early_ratings==13
    notes['classification']='B'
    cohort,summary,helpfulness,_=run(notes,ratings)
    assert cohort.empty and summary.empty and helpfulness.ratings.sum()==0


def test_coverage_multiple_notes_and_immaturity():
    requests=pd.DataFrame({'tweetId':[str(i) for i in range(1,12)],
        'noteRequestFeedEligibleAtMillis':[str(MS)]*10+[str(MS+6*86400000)]})
    notes=pd.DataFrame({'noteId':['1','2','3','4','5','6'], 'tweetId':['1','1','1','2','3','4'],
                        'createdAtMillis':[str(MS),str(MS+1),str(MS+2),str(MS+1),str(MS+7*86400000),str(MS+100)]})
    result=coverage_backend.analyze_coverage(requests,notes,cutoff='2026-01-08T00:00:00Z')
    assert result['summary']['eligible_requests']==10
    assert result['summary']['covered_requests']==4
    assert result['summary']['coverage_rate']==.4
    assert result['summary']['immature_requests_in_selected_dates']==1


def test_fixed_window_app_controls():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    if not (Path(__file__).parent/'outputs/dashboard/validation.json').exists():
        pytest.skip('Local prepared dataset unavailable')
    app=AppTest.from_file(str(Path(__file__).with_name('dashboard.py'))).run(timeout=30)
    assert not app.exception
    assert not app.checkbox
    assert not app.exception
    assert not app.error
    assert app.select_slider[1].value[0] <= app.select_slider[1].value[1]
    before=[m.value for m in app.metric[:3]]
    app.multiselect[0].set_value([]).run(timeout=30)
    assert not app.exception and not app.error
    assert [m.value for m in app.metric[:3]]==before
    assert app.metric[3].value=='0'
    reset=[b for b in app.button if b.label=='Reset Response'][0]
    reset.click().run(timeout=30)
    assert not app.exception and not app.error
    assert len(app.multiselect[0].value)>0
    response_before=[m.value for m in app.metric[3:]]
    focus=next(x for x in app.selectbox if x.label=='Focus week')
    focus.select(focus.options[1]).run(timeout=30)
    assert [m.value for m in app.metric[3:]] == response_before
    assert app.metric[0].value != before[0]
    next(b for b in app.button if b.label=='Reset Coverage').click().run(timeout=30)
    assert [m.value for m in app.metric[:3]] == before
    assert not any(x.label=='Note type' for x in app.selectbox)
    app.selectbox(key='cov_window').select(14).run(timeout=60)
    assert not app.exception and not app.error
    app.selectbox(key='resp_window').select(28).run(timeout=30)
    assert not app.exception and not app.error


def test_response_maturity_and_rating_window():
    notes,ratings=fixture()
    # A note created only three days before the cutoff is not eligible for seven days.
    recent=pd.Timestamp('2026-01-29T00:00:00Z').value//1000000
    notes.loc[4,'createdAtMillis']=str(recent)
    notes.loc[4,'createdAtMillis_status']=str(recent)
    ratings.loc[0,'createdAtMillis']=str(MS+7*86400000)
    ratings.loc[1,'createdAtMillis']=str(MS+7*86400000+1)
    ratings.loc[2,'createdAtMillis']=str(MS-1)
    cohort,_,helpfulness,diagnostics=response_analysis(notes,ratings,
        cutoff='2026-02-01T00:00:00Z',window=7,start='2026-01-01T00:00:00Z',
        end='2026-02-01T00:00:00Z',classifications=['A'])
    assert len(cohort)==4
    assert diagnostics['immature_notes']==1
    assert helpfulness.ratings.sum()==8
    assert cohort.iloc[0].early_ratings==10


@pytest.mark.parametrize('feed',['Standard','Small','Large','XL'])
def test_real_feed_reconciliation(feed):
    from pathlib import Path
    from window_analysis import FEEDS
    p=Path(__file__).parent/'outputs/dashboard'
    if not (p/'notes.parquet').exists(): pytest.skip('Local prepared dataset unavailable')
    notes=pd.read_parquet(p/'notes.parquet')
    requests=pd.read_parquet(p/'requests.parquet')
    result=coverage_backend.analyze_coverage(requests,notes,cutoff='2026-10-02T23:59:59.999Z',feed=feed)
    assert result['weekly'].eligible_requests.sum()==result['summary']['eligible_requests']
    assert result['weekly'].covered_requests.sum()==result['summary']['covered_requests']
    assert result['requests'].tweetId.is_unique


def test_review_metrics_distinguish_outcomes_and_waiting_activity():
    notes,ratings=fixture()
    notes.loc[1,'firstNonNMRStatus']='CURRENTLY_RATED_NOT_HELPFUL'
    notes.loc[1,'currentStatus']='CURRENTLY_RATED_NOT_HELPFUL'
    cohort,summary,_,_=run(notes,ratings)
    row=summary.iloc[0]
    assert row.helpful_first==2
    assert row.not_helpful_first==1
    assert row.no_recorded_transition==2
    assert row.no_transition_percent==40
    assert row.waiting_median_first_day_ratings==0
    assert row.waiting_zero_first_day_ratings==2
    assert row.waiting_zero_first_day_percent==100
    notes=notes.iloc[:3]
    _,summary,_,_=run(notes,ratings)
    assert pd.isna(summary.iloc[0].waiting_median_first_day_ratings)
    assert pd.isna(summary.iloc[0].waiting_zero_first_day_percent)
