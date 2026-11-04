"""Interactive fixed-window dashboard backed by locally validated compact tables."""
from pathlib import Path
import json
import pandas as pd
import streamlit as st
import altair as alt
from dashboard_data import export_csv
from window_analysis import FEEDS, coverage_backend, response_analysis, dates

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'outputs/dashboard'


@st.cache_data(show_spinner='Loading prepared tables…')
def load_prepared(version):
    return (pd.read_parquet(OUT/'notes.parquet'), pd.read_parquet(OUT/'ratings.parquet'),
            pd.read_parquet(OUT/'requests.parquet'), json.loads((OUT/'validation.json').read_text()))


@st.cache_data(show_spinner='Updating coverage…')
def coverage(version, cutoff, feed, window, start, end):
    notes, _, requests, _ = load_prepared(version)
    return coverage_backend.analyze_coverage(requests, notes[['tweetId','noteId','createdAtMillis']],
        cutoff=cutoff, feed=feed, window_days=window, start=start, end=end)


@st.cache_data(show_spinner='Updating response and ratings…')
def response(version, cutoff, window, start, end, classifications, note_type):
    notes, ratings, _, _ = load_prepared(version)
    return response_analysis(notes, ratings, cutoff=cutoff, window=window, start=start, end=end,
                             classifications=classifications, note_type=note_type)


def display_number(value, suffix=''):
    return 'N/A' if pd.isna(value) else f'{value:,.1f}{suffix}'


def reset(prefix):
    for key in list(st.session_state):
        if key.startswith(prefix): del st.session_state[key]


def filters(prefix, cutoff, available_dates):
    window = st.selectbox('Observation window (days)', [7,14,28], key=prefix+'window')
    values = available_dates(window).dropna()
    days = sorted(set(values.dt.date))
    if not days:
        st.info('No supported dates are available for this feed and observation window.')
        return None
    last = days[-1]
    first = next(d for d in days if d >= (pd.Timestamp(last)-pd.Timedelta(days=27)).date())
    st.caption(f'Available dates (UTC): {days[0]} through {last}. Only dates represented in the supported cohort can be selected.')
    key = prefix+'dates_'+str(window)+'_'+str(days[0])+'_'+str(last)
    if len(days) == 1:
        start = end = days[0]
        st.write(f'Available date: {start}')
    else:
        start, end = st.select_slider('Date range (UTC, inclusive)', options=days,
            value=(first,last), format_func=lambda d:d.strftime('%b %d, %Y'), key=key)
    return window, pd.Timestamp(start,tz='UTC').isoformat(), (pd.Timestamp(end,tz='UTC')+pd.Timedelta(days=1)).isoformat()


def render():
    st.title('Community Notes • Coverage & Response')
    st.write('For product managers investigating observed coverage gaps and waiting-note patterns. '
             'Selected data shards cannot establish platform-wide absence or the effect of adding writers or ratings.')
    left, right = st.columns(2)
    with left:
        st.markdown('**Where were new notes observed?**')
        st.write('Coverage follows requests and the notes written afterward. Use it to identify periods worth investigating.')
    with right:
        st.markdown('**How quickly did notes reach a status?**')
        st.write('Response and ratings follow February 4–10 notes. Compare recorded response times and rating opinions.')
    st.caption('The sections use different historical periods. Their filters are independent; their totals should not be compared as one population.')
    paths = [OUT/n for n in ['notes.parquet','ratings.parquet','requests.parquet','validation.json']]
    if not all(p.exists() for p in paths):
        st.info('Prepared tables are not ready. Run `.venv/bin/python prepare_dashboard.py` from the project folder, then retry.')
        if st.button('Retry preparation status'): st.rerun()
        return
    version = tuple((p.stat().st_mtime_ns,p.stat().st_size) for p in paths)
    try:
        notes, ratings, requests, report = load_prepared(version)
    except (OSError,ValueError) as exc:
        st.error(f'Could not load prepared data: {exc}')
        if st.button('Retry loading'): st.cache_data.clear(); st.rerun()
        return
    cutoff = report['cutoff_utc']
    st.warning(f'Unverified snapshot • Recorded provisional cutoff: {cutoff}. '
               'This is the agreed provisional cutoff for all four datasets. Original download dates and snapshot completeness remain unverified; results are exploratory.')
    with st.expander('Validation and snapshot evidence'):
        st.write(report['scope'])
        st.write('The scan reconciles all imported status/rating row counts and QC totals to Yoojin’s reports, '
                 'checks status ID uniqueness, and checks matched rating-pair uniqueness. '
                 'It does not revalidate the unavailable original raw files or prove snapshot completeness.')
        st.json(report)
    if not st.checkbox('Explore fixed-window results using the provisional October 2 cutoff', key='explore_windows'):
        st.info('Select exploratory mode above to view results using the shared provisional cutoff.')
        return
    st.caption('Exploratory mode • All times UTC • Filters affect only their own section • Refreshing source files requires rerunning preparation.')
    st.header('Coverage')
    st.write('Dates below refer to when requests became eligible for the selected feed, not when ratings were submitted.')
    st.button('Reset Coverage', on_click=reset, args=('cov_',))
    feed = st.selectbox('Request feed',list(FEEDS),key='cov_feed')
    eligibility = dates(requests[FEEDS[feed]])
    cf = filters('cov_',cutoff, lambda w: eligibility.loc[(eligibility+pd.Timedelta(days=w)).le(pd.Timestamp(cutoff))])
    if cf:
        window,start,end = cf
        try:
            result = coverage(version,cutoff,feed,window,start,end)
        except (ValueError,OSError,KeyError) as exc:
            st.error(f'Coverage could not be calculated: {exc}')
            if st.button('Retry coverage'): coverage.clear(); st.rerun()
        else:
            table = result['weekly'].copy()
            table['week'] = table.eligibility_week_utc.dt.strftime('%Y-%m-%d')
            table['coverage_percent'] = table.coverage_rate*100
            context = f'{feed}_{window}_{start}_{end}'
            selected_week = st.selectbox('Focus week', ['All weeks']+table.week.tolist(),key='cov_focus_'+context)
            if len(table):
                pick = alt.selection_point(name='week_pick',fields=['week'],on='click',clear='dblclick')
                chart = alt.Chart(table).mark_bar().encode(x=alt.X('week:N',title='Eligibility week (UTC)'),
                    y=alt.Y('coverage_percent:Q',title='Coverage (%)'),
                    opacity=alt.condition(pick,alt.value(1),alt.value(.4)),
                    tooltip=['week','eligible_requests','covered_requests','no_observed_note',alt.Tooltip('coverage_percent:Q',format='.1f')]).add_params(pick)
                event = st.altair_chart(chart,width='stretch',on_select='rerun',key='cov_chart_'+context)
                points = event.selection.get('week_pick',[])
                if points: selected_week = points[0]['week']
                st.caption('Click a bar to focus the cards/table; double-click to clear the chart selection. Chart selection takes precedence over Focus week.')
            scoped = table if selected_week=='All weeks' else table.loc[table.week.eq(selected_week)]
            eligible = int(scoped.eligible_requests.sum()); covered = int(scoped.covered_requests.sum())
            st.caption(f'Active week: {selected_week}')
            a,b,c = st.columns(3)
            a.metric('Eligible requests',f'{eligible:,}')
            b.metric('Covered requests',f'{covered:,}',help='Each request is counted once, even when it receives several notes.')
            c.metric('Coverage rate',display_number(covered/eligible*100 if eligible else float('nan'),'%'))
            st.write(f'No observed qualifying note: **{eligible-covered:,}**. '
                     f'Immature requests excluded in selected dates: **{result["summary"]["immature_requests_in_selected_dates"]:,}**.')
            st.caption(f'Invalid/nonpositive eligibility times across the full feed: {result["summary"]["invalid_or_nonpositive_eligibility_all_requests"]:,}. '
                       'Eligible requests have the full observation window. Boundary events are included.')
            if not eligible:
                st.info('No eligible requests match. This is missing data for the selection, not 0% coverage. Change the feed or dates, or use Reset Coverage.')
            elif not covered:
                st.info(f'There are {eligible:,} eligible requests, but no qualifying new notes were observed within {window} days in the supplied files. This is an observed 0% rate, not a calculation error.')
            st.dataframe(scoped,hide_index=True,width='stretch')
            meta = dict(cutoff_utc=cutoff,cutoff_verified=False,feed=feed,window_days=window,start_utc=start,end_exclusive_utc=end,selected_week=selected_week)
            st.download_button('Export coverage',export_csv(scoped,**meta),'windowed_coverage.csv','text/csv')
            if eligible:
                low = scoped.sort_values('coverage_rate').iloc[0]
                st.info(f'Review candidate: week {low.week} has {low.covered_requests:,} covered requests out of {low.eligible_requests:,}. '
                        'Review source coverage before interpreting this as unmet need.')
    st.header('Response time & ratings')
    st.info('February 4–10, 2026 • Dates refer to note creation. This is the period where our notes, status history, and observed ratings overlap. Coverage dates above remain independent.')
    st.button('Reset Response',on_click=reset,args=('resp_',))
    classes = sorted(notes.classification.fillna('').replace('','Unknown').unique())
    choice = st.multiselect('Classification',classes,default=classes,key='resp_classes')
    note_type = st.selectbox('Note type',['All','Media','Non-media','Collaborative','Unknown'],key='resp_type')
    st.caption('Collaborative and media categories can overlap. Unknown means a missing or unrecognized type flag.')
    st.caption('Response and ratings are restricted to note-creation dates with observed matched ratings in the supplied files. All eligible notes within those dates remain in the denominator, including notes without ratings. This is a selected historical period, not the full dataset.')
    def rating_dates(w):
        full, _, _, _ = response(version,cutoff,w,'2000-01-01T00:00:00Z','2100-01-01T00:00:00Z',tuple(classes),'All')
        return full.loc[full.noteId.isin(ratings.noteId), 'created']
    rf = filters('resp_',cutoff,rating_dates)
    if rf:
        window,start,end = rf
        try:
            cohort,summary,helpfulness,diagnostics = response(version,cutoff,window,start,end,tuple(choice),note_type)
        except (ValueError,OSError,KeyError) as exc:
            st.error(f'Response results could not be calculated: {exc}')
            if st.button('Retry response'): response.clear(); st.rerun()
        else:
            completed = cohort.loc[cohort.completed]
            a,b,c,d = st.columns(4)
            a.metric('Eligible notes',f'{len(cohort):,}')
            b.metric('Reached first non-NMR',f'{len(completed):,}')
            c.metric('No recorded transition in window',f'{len(cohort)-len(completed):,}')
            d.metric('Median completed time',display_number(completed.response_hours.median(),' h'))
            st.caption(f'Completion rate: {display_number(100*len(completed)/len(cohort) if len(cohort) else float("nan"),"%")} • '
                       f'Median uses {len(completed):,} completed notes. First non-NMR includes Helpful and Not Helpful.')
            st.write(f'Excluded: {diagnostics["immature_notes"]:,} immature notes; '
                     f'{diagnostics["excluded_mature_history"]:,} mature notes with missing/unusable history. '
                     f'Among selected notes, {diagnostics["unmatched_status"]:,} have no matching status record.')
            with st.expander('Response exclusions'): st.json(diagnostics)
            if cohort.empty: st.info('No eligible notes match. Widen dates, choose other classifications/types, or reduce the window.')
            if len(summary):
                bars = summary.melt('classification',value_vars=['completed','no_recorded_transition'],var_name='outcome',value_name='notes')
                st.altair_chart(alt.Chart(bars).mark_bar().encode(x='classification:N',y=alt.Y('notes:Q',title='Notes'),color='outcome:N',tooltip=['classification','outcome','notes']),width='stretch')
            st.dataframe(summary,hide_index=True,width='stretch')
            st.subheader('First-day ratings and completed response time')
            points = completed.sample(min(2000,len(completed)),random_state=576)
            if completed.empty:
                st.info('No completed events in this selection; no median or scatter can be calculated. Try another classification or use Reset Response.')
            elif not completed.early_ratings.gt(0).any():
                st.info('No ratings were observed during these completed notes’ first 24 hours in the supplied ratings file. The scatter plot is hidden because all first-day counts are zero. This does not establish that nobody rated the notes.')
            elif len(points):
                st.altair_chart(alt.Chart(points[['early_ratings','response_hours','classification']]).mark_circle(opacity=.6).encode(
                    x=alt.X('early_ratings:Q',title='Observed ratings in first 24 hours',scale=alt.Scale(zero=True)),
                    y=alt.Y('response_hours:Q',title='Hours to first non-NMR',scale=alt.Scale(domain=[0,window*24])),
                    color='classification:N',tooltip=['classification','early_ratings',alt.Tooltip('response_hours:Q',format='.1f')]),width='stretch')
                st.caption(f'Showing {len(points):,} of {len(completed):,} completed notes (fixed random seed if sampled). '
                           'First-day ratings may arrive after the first transition. Association does not demonstrate causation.')
            st.subheader('Helpfulness within the observation window')
            denominator = int(helpfulness.ratings.sum())
            st.caption(f'Valid rating denominator: {denominator:,}; missing/legacy levels excluded: {diagnostics["excluded_rating_levels"]:,}. '
                       'This uses ratings for the same eligible note cohort; rating opinions are not note statuses.')
            if denominator: st.bar_chart(helpfulness,x='helpfulness',y='ratings')
            else: st.info('No valid ratings match these notes within the selected window in our supplied file. This is not a 0% helpfulness result. Try another classification or use Reset Response.')
            if denominator:
                st.dataframe(helpfulness.rename(columns={'helpfulness':'Rating','ratings':'Count','percent':'Share (%)'}),hide_index=True,width='stretch')
            meta = dict(cutoff_utc=cutoff,cutoff_verified=False,window_days=window,start_utc=start,end_exclusive_utc=end,
                        classifications=';'.join(choice),note_type=note_type,units='hours; counts; percent')
            st.download_button('Export response',export_csv(summary,**meta),'windowed_response.csv','text/csv')
            st.download_button('Export helpfulness',export_csv(helpfulness,**meta),'windowed_helpfulness.csv','text/csv')
            if len(summary):
                group = summary.sort_values('no_recorded_transition',ascending=False).iloc[0]
                st.info(f'Review candidate: {group.classification} has {group.no_recorded_transition:,} of {group.eligible:,} eligible notes '
                        'without a recorded transition within the window. This does not establish that more ratings would resolve them faster.')
    with st.expander('Definitions and limits'):
        st.write('Coverage counts requests once when a new note appears at or after eligibility and at or before the window end. '
                 'Response includes notes with a full window and consistent matched status history. Missing histories are excluded, not labeled unresolved. '
                 'Later transitions count as no transition within the chosen window. Blank/legacy rating levels are excluded from helpfulness only. '
                 'The rating shard is partial: zero observed ratings does not imply zero platform-wide activity. '
                 'All exports match the displayed aggregate scope. Percentages are calculated from counts, not averages of weekly percentages.')
