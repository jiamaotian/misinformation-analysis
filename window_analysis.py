"""Pure fixed-window calculations shared by the app and acceptance tests."""
import importlib.util
from pathlib import Path
import pandas as pd

spec = importlib.util.spec_from_file_location('coverage_backend', Path(__file__).parent/'phase2-euan/coverage_analysis.py')
coverage_backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage_backend)
FEEDS = coverage_backend.FEEDS
LEVELS = ['HELPFUL','SOMEWHAT_HELPFUL','NOT_HELPFUL']
RESOLVED = ['CURRENTLY_RATED_HELPFUL','CURRENTLY_RATED_NOT_HELPFUL']


def truth(values):
    return values.astype('string').str.lower().isin(['true','1'])


def dates(values):
    return pd.to_datetime(pd.to_numeric(values, errors='coerce').where(
        pd.to_numeric(values, errors='coerce').gt(0)), unit='ms', utc=True, errors='coerce')


def response_analysis(notes, ratings, *, cutoff, window, start, end, classifications, note_type='All'):
    cutoff = pd.Timestamp(cutoff)
    n = notes.copy()
    n['created'] = dates(n.createdAtMillis)
    n['classification'] = n.classification.fillna('').replace('', 'Unknown')
    selected = n.created.ge(pd.Timestamp(start)) & n.created.lt(pd.Timestamp(end)) & n.classification.isin(classifications)
    media = truth(n.isMediaNote); collaborative = truth(n.isCollaborativeNote)
    known_media = n.isMediaNote.astype('string').str.lower().isin(['0','1','true','false'])
    known_collab = n.isCollaborativeNote.astype('string').str.lower().isin(['0','1','true','false'])
    if note_type == 'Media': selected &= media
    elif note_type == 'Non-media': selected &= known_media & ~media
    elif note_type == 'Collaborative': selected &= collaborative
    elif note_type == 'Unknown': selected &= ~known_media | ~known_collab
    n = n.loc[selected].copy()
    n['event'] = dates(n.timestampMillisOfFirstNonNMRStatus)
    status_created = dates(n.createdAtMillis_status)
    matched = n.currentStatus.notna()
    consistent_creation = status_created.eq(n.created)
    raw_event = n.timestampMillisOfFirstNonNMRStatus.fillna('').astype(str)
    absent_event = raw_event.isin(['','-1'])
    first = n.firstNonNMRStatus.fillna('').str.strip()
    valid_event = (n.event.ge(n.created) & first.isin(RESOLVED) & truth(n.qc_response_eligible))
    no_event = absent_event & first.isin(['','NEEDS_MORE_RATINGS']) & n.currentStatus.eq('NEEDS_MORE_RATINGS')
    consistent = ~truth(n.qc_status_time_inconsistent) & ~truth(n.qc_negative_latency)
    usable = matched & consistent_creation & consistent & (valid_event | no_event)
    mature = (n.created + pd.Timedelta(days=window)).le(cutoff)
    diagnostics = {'selected_notes':len(n), 'immature_notes':int((~mature).sum()),
                   'unmatched_status':int((~matched).sum()),
                   'unusable_matched_history':int((matched & ~usable).sum()),
                   'excluded_mature_history':int((mature & ~usable).sum()),
                   'invalid_creation_times_all_notes':int(dates(notes.createdAtMillis).isna().sum())}
    cohort = n.loc[usable & mature].copy()
    cohort['completed'] = cohort.event.le(cohort.created + pd.Timedelta(days=window)) & cohort.event.le(cutoff)
    cohort['response_hours'] = ((cohort.event-cohort.created).dt.total_seconds()/3600).where(cohort.completed)
    r = ratings.loc[ratings.noteId.isin(cohort.noteId)].copy()
    r = r.merge(cohort[['noteId','created']],on='noteId',validate='many_to_one')
    r['rated'] = dates(r.createdAtMillis)
    r['age'] = r.rated-r.created
    valid_key = truth(r.qc_key_valid)
    valid_time = r.rated.notna() & r.age.ge(pd.Timedelta(0)) & r.rated.le(cutoff)
    diagnostics['invalid_or_precreation_ratings'] = int((~valid_time).sum())
    early = r.loc[valid_key & valid_time & r.age.le(pd.Timedelta(hours=24))].groupby('noteId').size()
    cohort['early_ratings'] = cohort.noteId.map(early).fillna(0).astype(int)
    in_window = valid_key & valid_time & r.age.le(pd.Timedelta(days=window))
    levels = r.helpfulnessLevel.str.strip().str.upper()
    valid_level = levels.isin(LEVELS) & truth(r.qc_valid_helpfulness)
    diagnostics['excluded_rating_levels'] = int((in_window & ~valid_level).sum())
    counts = levels.loc[in_window & valid_level].value_counts().reindex(LEVELS,fill_value=0)
    helpfulness = counts.rename_axis('helpfulness').reset_index(name='ratings')
    total = int(counts.sum())
    helpfulness['percent'] = counts.to_numpy()/total*100 if total else float('nan')
    summary = cohort.groupby('classification').agg(eligible=('noteId','size'),completed=('completed','sum'),
                                                  median_hours=('response_hours','median')).reset_index()
    summary['no_recorded_transition'] = summary.eligible-summary.completed
    summary['helpful_first'] = summary.classification.map(
        cohort.loc[cohort.completed & cohort.firstNonNMRStatus.eq('CURRENTLY_RATED_HELPFUL')].groupby('classification').size()).fillna(0).astype(int)
    summary['not_helpful_first'] = summary.completed-summary.helpful_first
    summary['no_transition_percent'] = 100*summary.no_recorded_transition/summary.eligible
    waiting = cohort.loc[~cohort.completed]
    summary['waiting_median_first_day_ratings'] = summary.classification.map(waiting.groupby('classification').early_ratings.median())
    summary['waiting_zero_first_day_ratings'] = summary.classification.map(
        waiting.loc[waiting.early_ratings.eq(0)].groupby('classification').size()).fillna(0).astype(int)
    summary['waiting_zero_first_day_percent'] = (100*summary.waiting_zero_first_day_ratings / summary.no_recorded_transition.where(summary.no_recorded_transition.gt(0)))
    return cohort, summary, helpfulness, diagnostics
