import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.vstack([
        mo.md("""
        # **Speedrun Ethereum Developer Retention Analysis**
        <small>Author: <span style="background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px;">OSO Team</span> · Last Updated: <span style="background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px;">December 2025</span></small>
        """),
        mo.md("""
        This app analyzes retention patterns of developers who completed the Speedrun Ethereum program.<br>
        Track where developers were before and where they are now, measure dropoff rates,
        analyze Ethereum mindshare over time, and identify top performers by cohort.
        """),
        mo.accordion({
            "<b>Click to see details on how app was made</b>": mo.accordion({
                "Methodology": """
                - **Cohort Definition**: Developers are grouped by `sre_cohort_year` (when they joined SRE) and `sre_batch_id`
                - **Retention**: Tracks monthly PushEvent activity after SRE completion
                - **Ecosystem Classification**: Repos are classified as Ethereum, Solana, AI, Personal, or Other based on ecosystem mappings
                - **Dropoff Rate**: Calculated as the percentage of developers who stop contributing after a given period
                - **Mindshare**: Percentage of total developer activity (PushEvents) in Ethereum vs other ecosystems
                - **Leaderboard**: Ranked by total event count and challenges completed
                """,
                "Data Sources": """
                - SRE GitHub users (`int_sre_github_users`)
                - GitHub events by user (`int_sre_github_events_by_user`)
                - OpenDevData ecosystem mappings (`stg_opendevdata__*`)
                """,
                "Further Resources": """
                - [Getting Started with Pyoso](https://docs.opensource.observer/docs/get-started/python)
                - [Using the Semantic Layer](https://docs.opensource.observer/docs/get-started/using-semantic-layer)
                - [Marimo Documentation](https://docs.marimo.io/)
                """
            })
        })    
    ])
    return


@app.cell
def _():
    import marimo as mo
    import pyoso
    import pandas as pd
    import os
    from dotenv import load_dotenv
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    import plotly.express as px
    import plotly.graph_objects as go
    import altair as alt
    from datetime import datetime
    import sklearn
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.inspection import permutation_importance
    load_dotenv('../.env')
    return (
        GradientBoostingClassifier,
        LogisticRegression,
        RandomForestClassifier,
        StandardScaler,
        alt,
        classification_report,
        mo,
        np,
        os,
        pd,
        permutation_importance,
        pyoso,
        roc_auc_score,
        roc_curve,
        train_test_split,
    )


@app.cell
def _(os, pyoso):
    OSO_API_KEY = os.environ['OSO_API_KEY']

    client = pyoso.Client(api_key=OSO_API_KEY)
    return


@app.cell
def _(mo):
    mo.md(r"""
    pyoso_db_conn = pyoso.Client().dbapi_connection()
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    # Building data Model
    """)
    return


@app.cell
def _():
    stringify = lambda arr: "'" + "','".join(arr) + "'"
    return


@app.cell
def fetch_data():
    # df_sre_users_all = mo.sql(
    #     f"""
    #     WITH users AS (
    #       SELECT
    #         github_handle AS user_name,
    #         MAX(COALESCE(challenges_completed,0)) AS challenges_completed,
    #         MIN(batch_id) AS batch_id,
    #         MIN(created_at) AS start_date
    #       FROM int_sre_github_users
    #       GROUP BY 1
    #     )
    #     SELECT
    #       user_name,
    #       start_date,
    #       challenges_completed,
    #       batch_id,
    #       CAST(DATE_TRUNC('MONTH', start_date) AS DATE) AS start_month,
    #       YEAR(start_date) AS cohort_year
    #     FROM users
    #     """,
    #     output=False,
    #     engine=pyoso_db_conn
    # )

    # df_github_events_all = mo.sql(
    #     f"""
    #     WITH repo_mapping AS (
    #       WITH repo_attributes AS (
    #         SELECT
    #           LOWER(r._name) AS repo_name,
    #           e._name AS ecosystem_name,
    #           er.ecosystem_id AS ecosystem_id
    #         FROM stg_opendevdata__repos r
    #         JOIN stg_opendevdata__ecosystems_repos_recursive er
    #           ON r.id = er.repo_id
    #         JOIN stg_opendevdata__ecosystems e
    #           ON e.id = er.ecosystem_id
    #       ),
    #       ecosystem_flags AS (
    #         SELECT
    #           repo_name,
    #           bool_or(ecosystem_name = 'Ethereum') AS is_ethereum,
    #           bool_or(ecosystem_name = 'Ethereum Virtual Machine Stack') AS is_evm
    #         FROM repo_attributes
    #         GROUP BY 1
    #       )
    #       SELECT
    #         repo_name,
    #         CASE
    #           WHEN is_ethereum THEN 'Ethereum'
    #           WHEN is_evm THEN 'Other EVM Chain'
    #           ELSE 'Other Ecosystem'
    #         END AS best_match_ecosystem
    #       FROM ecosystem_flags
    #     ),
    #     monthly_events AS (
    #       SELECT
    #        CAST(DATE_TRUNC('WEEK', event_time) AS DATE) AS bucket_week,
    #         CAST(DATE_TRUNC('MONTH', event_time) AS DATE) AS bucket_month,
    #         user_name,
    #         repo_name,
    #         github_repo_id,
    #         COUNT(*) AS event_count
    #       FROM int_sre_github_events_by_user
    #       WHERE
    #         event_type = 'PushEvent'
    #         AND user_name IN ({stringify(df_sre_users_all['user_name'])})
    #       GROUP BY 1,2,3,4,5
    #     )
    #     SELECT
    #       bucket_week,
    #       bucket_month,
    #       user_name,
    #       github_repo_id,
    #       repo_name,
    #       CASE
    #         WHEN user_name = split_part(repo_name, '/', 1)
    #           THEN 'Personal'
    #         WHEN best_match_ecosystem IS NOT NULL
    #           THEN best_match_ecosystem
    #         ELSE 'Unknown'
    #       END AS repo_label,
    #       event_count
    #     FROM monthly_events
    #     LEFT JOIN repo_mapping USING (repo_name)
    #     """,
    #     output=False,
    #     engine=pyoso_db_conn
    # )
    return


@app.cell
def _():
    # df_sre_users_all.shape , df_sre_users_all.describe() , df_sre_users_all.columns
    return


@app.cell
def _():
    # df_github_events_all.shape , df_github_events_all.describe() , df_github_events_all.columns
    return


@app.cell
def process_data():
    # df_merged = df_github_events_all.merge(df_sre_users_all, on='user_name')
    # df_merged['cohort_year'] = df_merged['cohort_year'].apply(str)
    # df_merged['batch_id'] = df_merged['batch_id'].apply(lambda x: '-' if pd.isna(x) else str(int(x)).zfill(2))
    # df_merged['month'] = (
    #     (pd.to_datetime(df_merged['bucket_month']).dt.year - pd.to_datetime(df_merged['start_month']).dt.year)*12
    #     + (pd.to_datetime(df_merged['bucket_month']).dt.month - pd.to_datetime(df_merged['start_month']).dt.month)
    # )
    # df_merged['scaffold-eth_fork'] = df_merged.apply(lambda x: "scaffold-eth" in x['repo_name'].split('/')[1] and x['repo_label'] == 'Personal', axis=1)

    # _forkers = df_merged[df_merged['scaffold-eth_fork']]['user_name'].unique()
    # df_merged['dev_forked_scaffold-eth'] = df_merged['user_name'].isin(_forkers)

    # _experience = pd.Series(index=df_merged['user_name'].unique(), dtype='object')
    # _min_months = df_merged.groupby('user_name')['month'].min()
    # _delayed_start = list(_min_months[_min_months>=3].index)
    # _experience.loc[_delayed_start] = 'Delayed Start'

    # _regular_start = list(_min_months[_min_months<3].index)
    # _month_count = df_merged[(df_merged['user_name'].isin(_regular_start)) & (df_merged['month'] < 0)].groupby('user_name')['month'].nunique()
    # _reg_counts = _month_count.reindex(_regular_start).fillna(0)

    # _experience.loc[_reg_counts[_reg_counts<=3].index] = 'Newb'
    # _experience.loc[_reg_counts[(_reg_counts>3) & (_reg_counts<=12)].index] = 'Learning'
    # _experience.loc[_reg_counts[_reg_counts>12].index] = 'Experienced'

    # df_merged = df_merged.merge(_experience.rename('experience_category'), left_on='user_name', right_index=True, how='left')
    # df_merged['last_month_activity'] = df_merged.groupby('user_name')['bucket_month'].transform('max')
    # # df_merged.to_csv('data/df_merged.csv')
    return


@app.cell
def _(df_merged):
    df_merged.shape , df_merged.describe() , df_merged.columns
    return


@app.cell
def _(df_merged):
    df_merged.head()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Feature exploration
    """)
    return


@app.cell
def _(pd):
    df_merged = pd.read_csv('data/df_merged.csv')
    return (df_merged,)


@app.cell
def _(df_merged):
    (df_merged.user_name.nunique(), 
    df_merged.start_month.isna().sum(), 
    df_merged[df_merged.repo_label == "Ethereum"].user_name.nunique())
    return


@app.cell
def _(df_merged):
    df_merged.columns
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Classifying churn and convertion
    """)
    return


@app.cell
def _(df_merged, pd):
    # Create a user-level dataframe to store our classifications
    user_convertion = df_merged.copy()
    user_classifications = pd.DataFrame({'user_name': user_convertion['user_name'].unique()})

    # 1. GENERAL CODING CLASSIFICATION
    # Find users who were already coders before the program (had any events before start_date)
    _pre_program_coders = user_convertion[
        user_convertion['bucket_week'] < user_convertion['start_date']
    ]['user_name'].unique()

    user_classifications['already_coder'] = user_classifications['user_name'].isin(_pre_program_coders)

    # Filter for users who were NOT coders before the program
    _non_coders = user_classifications[~user_classifications['already_coder']]['user_name'].unique()

    # Find non-coders who started coding after joining the program (had any events after start_date)
    _post_program_events = user_convertion[
        (user_convertion['user_name'].isin(_non_coders)) & 
        (user_convertion['bucket_week'] >= user_convertion['start_date'])
    ]['user_name'].unique()

    # Binary classification for modeling (only for non-coders)
    user_classifications['converted_to_coder'] = user_classifications['user_name'].isin(_post_program_events)
    user_classifications['coder_churn'] = (~user_classifications['already_coder']) & (~user_classifications['converted_to_coder'])

    # 2. ETHEREUM SPECIFIC CLASSIFICATION
    # Find users who contributed to Ethereum repos before joining
    _pre_program_ethereum = user_convertion[
        (user_convertion['repo_label'] == 'Ethereum') & 
        (user_convertion['bucket_week'] < user_convertion['start_date'])
    ]['user_name'].unique()

    user_classifications['already_ethereum_contributor'] = user_classifications['user_name'].isin(_pre_program_ethereum)

    # Find users who contributed to Ethereum repos after joining but weren't Ethereum contributors before
    _post_program_ethereum = user_convertion[
        (~user_convertion['user_name'].isin(_pre_program_ethereum)) & 
        (user_convertion['repo_label'] == 'Ethereum') & 
        (user_convertion['bucket_week'] >= user_convertion['start_date'])
    ]['user_name'].unique()

    user_classifications['converted_to_ethereum'] = user_classifications['user_name'].isin(_post_program_ethereum)
    user_classifications['ethereum_churn'] = (~user_classifications['already_ethereum_contributor']) & (~user_classifications['converted_to_ethereum'])

    # 3. EVM CLASSIFICATION (Ethereum + Other EVM Chain)
    # Find users who contributed to EVM repos before joining
    _pre_program_evm = user_convertion[
        (user_convertion['repo_label'].isin(['Ethereum', 'Other EVM Chain'])) & 
        (user_convertion['bucket_week'] < user_convertion['start_date'])
    ]['user_name'].unique()

    user_classifications['already_evm_contributor'] = user_classifications['user_name'].isin(_pre_program_evm)

    # Find users who contributed to EVM repos after joining but weren't EVM contributors before
    _post_program_evm = user_convertion[
        (~user_convertion['user_name'].isin(_pre_program_evm)) & 
        (user_convertion['repo_label'].isin(['Ethereum', 'Other EVM Chain'])) & 
        (user_convertion['bucket_week'] >= user_convertion['start_date'])
    ]['user_name'].unique()

    user_classifications['converted_to_evm'] = user_classifications['user_name'].isin(_post_program_evm)
    user_classifications['evm_churn'] = (~user_classifications['already_evm_contributor']) & (~user_classifications['converted_to_evm'])

    # Create status labels for each classification
    def _get_coder_status(row):
        if row['already_coder']:
            return "already_coder"
        elif row['converted_to_coder']:
            return "converted_to_coder"
        else:
            return "coder_churn"

    def _get_ethereum_status(row):
        if row['already_ethereum_contributor']:
            return "already_ethereum_contributor"
        elif row['converted_to_ethereum']:
            return "converted_to_ethereum"
        else:
            return "ethereum_churn"

    def _get_evm_status(row):
        if row['already_evm_contributor']:
            return "already_evm_contributor"
        elif row['converted_to_evm']:
            return "converted_to_evm"
        else:
            return "evm_churn"


    user_classifications['coder_status'] = user_classifications.apply(_get_coder_status, axis=1)
    user_classifications['ethereum_status'] = user_classifications.apply(_get_ethereum_status, axis=1)
    user_classifications['evm_status'] = user_classifications.apply(_get_evm_status, axis=1)

    # Merge the classifications back to the original dataframe
    user_convertion = user_convertion.merge(user_classifications, on='user_name', how='left') 


    user_convertion = user_convertion[['user_name','coder_status', 'ethereum_status',
       'evm_status']].drop_duplicates()
    return (user_classifications,)


@app.cell
def _(user_classifications):
    # Print statistics about the classifications
    print("\n--- General Coding Classification Statistics ---")
    print(f"Total users: {user_classifications.shape[0]}")
    print(f"Already coders before program: {user_classifications['already_coder'].sum()} ({user_classifications['already_coder'].mean()*100:.1f}%)")

    # Calculate percentages based on non-coders only
    non_coder_count = user_classifications[~user_classifications['already_coder']].shape[0]
    converted_count = user_classifications[user_classifications['converted_to_coder']].shape[0]
    churn_count = user_classifications[user_classifications['coder_churn']].shape[0]

    converted_pct = (converted_count / non_coder_count * 100) if non_coder_count > 0 else 0
    churn_pct = (churn_count / non_coder_count * 100) if non_coder_count > 0 else 0

    print(f"Non-coders who started coding after program: {converted_count} ({converted_pct:.1f}% of non-coders)")
    print(f"Non-coders who never started coding: {churn_count} ({churn_pct:.1f}% of non-coders)")

    print("\nCoder status distribution:")
    status_counts = user_classifications['coder_status'].value_counts()
    for category, count in status_counts.items():
        percentage = count / user_classifications.shape[0] * 100
        print(f"- {category}: {count} ({percentage:.1f}%)")

    print("\n--- Ethereum Contributor Classification Statistics ---")
    eth_converted_count = user_classifications['converted_to_ethereum'].sum()
    eth_total = user_classifications.shape[0] - user_classifications['already_ethereum_contributor'].sum()
    eth_pct = (eth_converted_count / eth_total * 100) if eth_total > 0 else 0
    print(f"Users who became Ethereum contributors: {eth_converted_count} ({eth_pct:.1f}% of potential converters)")

    print("\n--- EVM Contributor Classification Statistics ---")
    evm_converted_count = user_classifications['converted_to_evm'].sum()
    evm_total = user_classifications.shape[0] - user_classifications['already_evm_contributor'].sum()
    evm_pct = (evm_converted_count / evm_total * 100) if evm_total > 0 else 0
    print(f"Users who became EVM contributors: {evm_converted_count} ({evm_pct:.1f}% of potential converters)")
    return


@app.cell
def _(mo):
    mo.md(r"""
    ##  Building features
    """)
    return


@app.cell
def _(df_merged, np, pd):
    ## functions
    def _calc_weeks_diff(start_date, end_date):
        if pd.isna(start_date) or pd.isna(end_date):
            return None
        days_diff = (end_date - start_date).days
        weeks_diff = days_diff / 7
        return weeks_diff

    # Calculate weeks difference
    def _calc_weeks_before_program(row):
        if pd.isna(row['bucket_week']) or pd.isna(row['start_date']):
            return None
        # Calculate the difference in days and convert to weeks
        days_diff = (row['start_date'] - row['bucket_week']).days
        weeks_diff = days_diff / 7
        # Round up to get discrete week numbers
        return min(int(np.ceil(weeks_diff)), 12)

    user_features = df_merged.copy()

    # Convert date columns to datetime if they aren't already
    user_features['start_month'] = pd.to_datetime(user_features['start_month'])
    user_features['start_date'] = pd.to_datetime(user_features['start_date'])
    user_features['bucket_week'] = pd.to_datetime(user_features['bucket_week'])
    user_features['bucket_month'] = pd.to_datetime(user_features['bucket_month'])
    user_features.loc[user_features.repo_label == "Other Ecosystem", 'repo_label'] = "other_ecosystem"
    user_features.repo_label = user_features.repo_label.str.lower()


    # 1. User age in weeks when joining program (first activity to start_month)
    # Group by user to find their first activity ever
    _first_activity = user_features.groupby('user_name')['bucket_week'].min().reset_index()
    _first_activity.rename(columns={'bucket_week': 'first_activity_week_date'}, inplace=True)

    # Merge back to original dataframe
    user_features = user_features.merge(_first_activity, on='user_name', how='left')
    # User age in weeks when joining program
    user_features['user_age_weeks_at_join'] = user_features.apply(
        lambda row: _calc_weeks_diff(row['first_activity_week_date'], row['start_date']), 
        axis=1
    )

    # Print statistics
    print("\n--- User Age at Program Join Statistics ---")
    print("User age in weeks when joining program:")
    print(user_features.groupby('user_name')['user_age_weeks_at_join'].first().describe())


    # 2. Scaffold-eth features
    # Find first date when user contributed to scaffold-eth fork

    _scaffold_eth_contribs = user_features[user_features['scaffold-eth_fork'] == True].copy()
    if not _scaffold_eth_contribs.empty:
        _first_scaffold_contrib = _scaffold_eth_contribs.groupby('user_name')['bucket_week'].min().reset_index()
        _first_scaffold_contrib.rename(columns={'bucket_week': 'first_scaffold_eth_contrib_week_date'}, inplace=True)

        # Merge back to original dataframe
        user_features = user_features.merge(_first_scaffold_contrib, on='user_name', how='left')

        # Calculate weeks from start to first scaffold-eth contribution
        user_features['scaffold_eth_contrib_week_diff'] = user_features.apply(
            lambda row: _calc_weeks_diff(row['start_date'], row['first_scaffold_eth_contrib_week_date']), 
            axis=1
        )

        # Print statistics
        print("\n--- Scaffold-eth Contribution Statistics ---")
        print(f"Users with scaffold-eth contributions: {_first_scaffold_contrib.shape[0]}")
        print("Weeks to first scaffold-eth contribution:")
        print(user_features.groupby('user_name')['first_scaffold_eth_contrib_week_date'].first().describe())

    # 3. Weekly activity before joining program
    # Create a separate dataframe for pre-program activity analysis
    _pre_program_df = user_features[user_features['bucket_week'] < user_features['start_month']].copy()

    if not _pre_program_df.empty:
        # Apply the function to get week numbers
        _pre_program_df['week_num'] = _pre_program_df.apply(_calc_weeks_before_program, axis=1)

        # Filter for 12 weeks before program
        _pre_program_df = _pre_program_df[_pre_program_df['week_num'] <= 12]

        # Group by user and week to sum event counts
        _weekly_activity = _pre_program_df.groupby(['user_name', 'week_num'])['event_count'].sum().reset_index()

        # Create a pivot table for easier analysis
        _weekly_pivot = _weekly_activity.pivot(index='user_name', columns='week_num', values='event_count').fillna(0)

        # Get the actual columns that exist in the pivot table
        _existing_cols = sorted(_weekly_pivot.columns)
        print(f"Available week columns: {_existing_cols}")

        # Rename columns for clarity
        _week_cols = {_i: f'events_week_minus_{_i}' for _i in _existing_cols}
        _weekly_pivot = _weekly_pivot.rename(columns=_week_cols)

        # Create weekly stats dataframe
        _weekly_stats = pd.DataFrame(index=_weekly_pivot.index)

        # For 4-week stats, use columns that are <= 4
        _4week_cols = [f'events_week_minus_{_i}' for _i in _existing_cols if _i <= 4]
        if _4week_cols:  # Only proceed if we have columns
            _4week_data = _weekly_pivot[_4week_cols]
            _weekly_stats['events_4weeks_sum'] = _4week_data.sum(axis=1)
            _weekly_stats['events_4weeks_avg'] = _4week_data.mean(axis=1)
            _weekly_stats['events_4weeks_median'] = _4week_data.median(axis=1)
            _weekly_stats['events_4weeks_std'] = _4week_data.std(axis=1, ddof=0).fillna(0)
        else:
            print("No data available for 4-week statistics")
            _weekly_stats['events_4weeks_sum'] = 0
            _weekly_stats['events_4weeks_avg'] = 0
            _weekly_stats['events_4weeks_median'] = 0
            _weekly_stats['events_4weeks_std'] = 0

        # For 12-week stats, use all available columns
        _12week_cols = [f'events_week_minus_{_i}' for _i in _existing_cols if _i <= 12]
        if _12week_cols:  # Only proceed if we have columns
            _12week_data = _weekly_pivot[_12week_cols]
            _weekly_stats['events_12weeks_sum'] = _12week_data.sum(axis=1)
            _weekly_stats['events_12weeks_avg'] = _12week_data.mean(axis=1)
            _weekly_stats['events_12weeks_median'] = _12week_data.median(axis=1)
            _weekly_stats['events_12weeks_std'] = _12week_data.std(axis=1, ddof=0).fillna(0)
        else:
            print("No data available for 12-week statistics")
            _weekly_stats['events_12weeks_sum'] = 0
            _weekly_stats['events_12weeks_avg'] = 0
            _weekly_stats['events_12weeks_median'] = 0
            _weekly_stats['events_12weeks_std'] = 0

        # Merge weekly activity data back to main dataframe
        # First, create a user-level dataframe with the stats
        _user_weekly_stats = _weekly_stats.copy()
        _user_weekly_stats.reset_index(inplace=True)

        # Merge the weekly pivot data (individual week counts)
        for _col in _weekly_pivot.columns:
            _user_weekly_stats[_col] = _weekly_pivot[_col]

        # Merge back to the main dataframe
        user_features = user_features.merge(_user_weekly_stats, on='user_name', how='left')

    # 4.Contributions to 'Other Ecosystem', 'Personal', 'Unknown' repos before program
    # Filter for pre-program activities in specific repo labels
    _other_repos_df = user_features[
        (user_features['bucket_week'] < user_features['start_date']) & 
        (user_features['repo_label'].isin(['other_ecosystem', 'personal', 'unknown']))
    ].copy()

    if not _other_repos_df.empty:
        _other_repos_df['week_num'] = _other_repos_df.apply(_calc_weeks_before_program, axis=1)

        # Create user-level stats for other repos contributions
        _user_other_repos = pd.DataFrame({'user_name': user_features['user_name'].unique()})

        # Calculate breakdown by repo label

        for label in ['other_ecosystem', 'personal', 'unknown']:
            # Total events for this label
            _label_df = _other_repos_df[_other_repos_df['repo_label'] == label]
            if not _label_df.empty:
                _label_total = _label_df.groupby('user_name')['event_count'].sum().reset_index()
                _label_total.rename(columns={'event_count': f'{label.lower()}_total_events'}, inplace=True)
                _user_other_repos = _user_other_repos.merge(_label_total, on='user_name', how='left')
            _user_other_repos[f'{label.lower()}_total_events'] = _user_other_repos.get(f'{label.lower()}_total_events', pd.Series(0, index=_user_other_repos.index)).fillna(0)

            # 4-week events for this label
            _label_4w_df = _label_df[_label_df['week_num'] <= 4]
            if not _label_4w_df.empty:
                _label_4w_total = _label_4w_df.groupby('user_name')['event_count'].sum().reset_index()
                _label_4w_total.rename(columns={'event_count': f'{label.lower()}_repo_4weeks_events'}, inplace=True)
                _user_other_repos = _user_other_repos.merge(_label_4w_total, on='user_name', how='left')
            _user_other_repos[f'{label.lower()}_repo_4weeks_events'] = _user_other_repos.get(f'{label.lower()}_repo_4weeks_events', pd.Series(0, index=_user_other_repos.index)).fillna(0)

            # 12-week events for this label
            _label_12w_df = _label_df[_label_df['week_num'] <= 12]
            if not _label_12w_df.empty:
                _label_12w_total = _label_12w_df.groupby('user_name')['event_count'].sum().reset_index()
                _label_12w_total.rename(columns={'event_count': f'{label.lower()}_repo_12weeks_events'}, inplace=True)
                _user_other_repos = _user_other_repos.merge(_label_12w_total, on='user_name', how='left')
            _user_other_repos[f'{label.lower()}_repo_12weeks_events'] = _user_other_repos.get(f'{label.lower()}_repo_12weeks_events', pd.Series(0, index=_user_other_repos.index)).fillna(0)

        # Merge other repos stats back to main dataframe
        user_features = user_features.merge(_user_other_repos, on='user_name', how='left')



    # Select columns for the final user features dataframe
    user_features = user_features[['user_name', 'challenges_completed','dev_forked_scaffold-eth',
                                 'scaffold_eth_contrib_week_diff', 'experience_category', 'user_age_weeks_at_join',
                                 'events_4weeks_sum', 'events_4weeks_avg', 'events_4weeks_median', 'events_4weeks_std',
                                 'events_12weeks_sum', 'events_12weeks_avg', 'events_12weeks_median', 'events_12weeks_std',
                                 'other_ecosystem_total_events', 'personal_total_events', 'unknown_total_events',
                                 'other_ecosystem_repo_4weeks_events', 'personal_repo_4weeks_events', 'unknown_repo_4weeks_events',
                                 'other_ecosystem_repo_12weeks_events', 'personal_repo_12weeks_events', 'unknown_repo_12weeks_events'
                                ]].drop_duplicates()
    user_features
    return (user_features,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Modeling
    """)
    return


@app.cell
def _(pd, user_classifications, user_features):
    mdf = pd.merge(user_classifications, user_features, on='user_name', how='left')
    mdf.loc[mdf.experience_category.isin(['Newb', 'Delayed Start']), 'experience_category'] = 0 
    mdf.loc[mdf.experience_category.isin(['Learning']), 'experience_category'] = 1
    mdf.loc[mdf.experience_category.isin(['Experienced']), 'experience_category'] = 2
    return (mdf,)


@app.cell
def _(mdf):
    ## modeling coder and no coders into retention in Ethereum

    mdf_ethereum_modeling = mdf.copy()
    mdf_ethereum_modeling = mdf_ethereum_modeling.loc[mdf_ethereum_modeling.already_ethereum_contributor == False] 
    dropcolumns = ['converted_to_ethereum', 'ethereum_churn','already_ethereum_contributor', 'already_coder', 'converted_to_coder', 'coder_churn', 'coder_status','already_evm_contributor', 'converted_to_evm',
           'evm_churn','evm_status', 'other_ecosystem_total_events', 'personal_total_events',
           'unknown_total_events', 'scaffold_eth_contrib_week_diff']

    mdf_ethereum_modeling = mdf_ethereum_modeling.drop(columns=dropcolumns)
    mdf_ethereum_modeling.ethereum_status = mdf_ethereum_modeling.ethereum_status == 'converted_to_ethereum'
    mdf_ethereum_modeling.set_index('user_name', inplace = True)
    mdf_ethereum_modeling = mdf_ethereum_modeling.fillna(0)
    return (mdf_ethereum_modeling,)


@app.cell
def _(
    GradientBoostingClassifier,
    LogisticRegression,
    RandomForestClassifier,
    StandardScaler,
    classification_report,
    mdf_ethereum_modeling,
    np,
    pd,
    permutation_importance,
    train_test_split,
):
    # Define the target variable - using ethereum_status as target
    y = mdf_ethereum_modeling['ethereum_status']

    # Select features for modeling (exclude the target)
    feature_cols = [_col for _col in mdf_ethereum_modeling.columns if _col != 'ethereum_status' and 
                   pd.api.types.is_numeric_dtype(mdf_ethereum_modeling[_col])]

    print(f"Selected {len(feature_cols)} features for modeling:")
    print(feature_cols)

    # Check if we have enough data
    print(f"\nTotal samples: {mdf_ethereum_modeling.shape[0]}")
    print(f"Conversion rate: {y.mean()*100:.1f}%")

    # Split the data
    X = mdf_ethereum_modeling[feature_cols]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    # Scale the features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Create a dataframe to store feature importance results
    feature_importance_df = pd.DataFrame(index=feature_cols)

    # Train models and collect feature importance
    models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(random_state=42)
    }

    results = {}

    for _name, model in models.items():
        print(f"\n--- Training {_name} ---")

        # Train the model
        model.fit(X_train_scaled, y_train)

        # Evaluate on test set
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1] if hasattr(model, "predict_proba") else None

        # Calculate metrics
        _accuracy = (y_pred == y_test).mean()

        print(f"Accuracy: {_accuracy:.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))

        # Store results
        results[_name] = {
            'model': model,
            '_accuracy': _accuracy,
            'y_pred': y_pred,
            'y_prob': y_prob
        }

        # Extract feature importance
        if _name == 'Logistic Regression':
            importance = np.abs(model.coef_[0])
            feature_importance_df[f'{_name} Coefficient'] = importance
        elif hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            feature_importance_df[f'{_name} Importance'] = importance

        # Calculate permutation importance
        perm_importance = permutation_importance(model, X_test_scaled, y_test, n_repeats=10, random_state=42)
        feature_importance_df[f'{_name} Permutation Importance'] = perm_importance.importances_mean

    # Sort features by importance
    for _col in feature_importance_df.columns:
        if not feature_importance_df[_col].isna().all():
            feature_importance_df[f'{_col} Rank'] = feature_importance_df[_col].rank(ascending=False)

    # Calculate average rank across models
    rank_cols = [_col for _col in feature_importance_df.columns if 'Rank' in _col]
    if rank_cols:
        feature_importance_df['Average Rank'] = feature_importance_df[rank_cols].mean(axis=1)
        feature_importance_df = feature_importance_df.sort_values('Average Rank')

    print("\n--- Feature Importance Summary ---")
    print(feature_importance_df)
    return X, feature_cols, feature_importance_df, models, results, y, y_test


@app.cell
def _(
    X,
    alt,
    feature_cols,
    feature_importance_df,
    mo,
    models,
    np,
    pd,
    results,
    roc_auc_score,
    roc_curve,
    y,
    y_test,
):

    # 1. Bar plot of top features by average importance
    # Get top 15 features by average rank
    if 'Average Rank' in feature_importance_df.columns:
        _top_features = feature_importance_df.sort_values('Average Rank').head(15).index.tolist()
    else:
        # If no average rank, use the first importance column
        imp_cols = [col for col in feature_importance_df.columns if 'Importance' in col or 'Coefficient' in col]
        if imp_cols:
            _top_features = feature_importance_df.sort_values(imp_cols[0], ascending=False).head(15).index.tolist()
        else:
            _top_features = feature_cols[:15]  # Just take first 15 features

    # Create a dataframe for plotting
    plot_df = pd.DataFrame()

    # Add importance values for each model
    for _name in models.keys():
        # Find the corresponding importance column
        imp_cols = [col for col in feature_importance_df.columns if _name in col and ('Importance' in col or 'Coefficient' in col)]
        if imp_cols:
            # Normalize to 0-1 scale for comparison
            values = feature_importance_df[imp_cols[0]].loc[_top_features]
            if values.sum() > 0:  # Avoid division by zero
                plot_df[_name] = values / values.sum()

    # Create a long-format dataframe for Altair
    plot_long = plot_df.reset_index().melt(id_vars='index', var_name='Model', value_name='Importance')
    plot_long = plot_long.rename(columns={'index': 'Feature'})

    # Feature importance chart with Altair
    feature_importance_chart = alt.Chart(plot_long).mark_bar().encode(
        x=alt.X('Importance:Q', title='Normalized Importance'),
        y=alt.Y('Feature:N', sort='-x', title='Feature'),
        color=alt.Color('Model:N', title='Model'),
        tooltip=['Feature', 'Model', alt.Tooltip('Importance:Q', format='.3f')]
    ).properties(
        title='Top Features by Importance Across Models',
        width=700,
        height=500
    )

    # 2. Correlation heatmap using Altair
    # Calculate correlations with target
    corr_with_target = pd.DataFrame(index=feature_cols)
    corr_with_target['Correlation with Conversion'] = [X[col].corr(y) for col in feature_cols]
    corr_with_target = corr_with_target.sort_values('Correlation with Conversion', ascending=False)

    print("\n--- Feature Correlation with Conversion ---")
    print(corr_with_target)

    # Plot correlation heatmap of top features with each other
    top_corr_features = corr_with_target.index[:15].tolist()
    corr_matrix = X[top_corr_features].corr()

    # Convert correlation matrix to long format for Altair
    corr_data = corr_matrix.stack().reset_index()
    corr_data.columns = ['Feature1', 'Feature2', 'Correlation']

    # Create correlation heatmap with Altair
    correlation_heatmap = alt.Chart(corr_data).mark_rect().encode(
        x=alt.X('Feature1:N', title=None),
        y=alt.Y('Feature2:N', title=None),
        color=alt.Color('Correlation:Q', 
                       scale=alt.Scale(
                           domain=[-1, 0, 1],
                           range=['#1f77b4', '#ffffff', '#d62728']  # Blue, White, Red
                       ),
                       legend=alt.Legend(title='Correlation')),
        tooltip=[
            alt.Tooltip('Feature1:N', title='Feature 1'),
            alt.Tooltip('Feature2:N', title='Feature 2'),
            alt.Tooltip('Correlation:Q', format='.2f')
        ]
    ).properties(
        title='Correlation Matrix of Top Features',
        width=600,
        height=600
    )

    # Add text labels to the heatmap - simplified version without nested conditions
    text = alt.Chart(corr_data).mark_text(baseline='middle').encode(
        x=alt.X('Feature1:N'),
        y=alt.Y('Feature2:N'),
        text=alt.Text('Correlation:Q', format='.2f'),
        color=alt.condition(
            'abs(datum.Correlation) > 0.5',
            alt.value('white'),
            alt.value('black')
        )
    )

    # Combine heatmap and text
    correlation_chart = alt.layer(correlation_heatmap, text)

    # 3. ROC curves comparison using Altair
    # Create dataframe for ROC curves
    roc_data = []

    # Add a reference line for random classifier
    for fpr in np.linspace(0, 1, 100):
        roc_data.append({
            'False Positive Rate': fpr,
            'True Positive Rate': fpr,
            'Model': 'Random (AUC = 0.500)'
        })

    # Add ROC curve for each model
    for _name, result in results.items():
        if result['y_prob'] is not None:
            fpr, tpr, _ = roc_curve(y_test, result['y_prob'])
            auc = roc_auc_score(y_test, result['y_prob'])
            model_name = f'{_name} (AUC = {auc:.3f})'

            for _metric in range(len(fpr)):
                roc_data.append({
                    'False Positive Rate': fpr[_metric],
                    'True Positive Rate': tpr[_metric],
                    'Model': model_name
                })

    roc_df = pd.DataFrame(roc_data)

    # Create ROC curve chart with Altair
    roc_chart = alt.Chart(roc_df).mark_line().encode(
        x=alt.X('False Positive Rate:Q', title='False Positive Rate'),
        y=alt.Y('True Positive Rate:Q', title='True Positive Rate'),
        color=alt.Color('Model:N', title='Model'),
        tooltip=['Model', 
                alt.Tooltip('False Positive Rate:Q', format='.2f'), 
                alt.Tooltip('True Positive Rate:Q', format='.2f')]
    ).properties(
        title='ROC Curve Comparison',
        width=600,
        height=400
    )

    # Display the visualizations using mo.vstack
    mo.vstack([
        mo.md("## Feature Importance Across Models"),
        mo.md("This visualization shows which features are most important for predicting conversion across different models."),
        mo.ui.altair_chart(feature_importance_chart),

        mo.md("## Correlation Between Top Features"),
        mo.md("This heatmap shows how features correlate with each other. Strong correlations may indicate redundant information."),
        mo.ui.altair_chart(correlation_chart),

        mo.md("## Model Performance Comparison (ROC Curves)"),
        mo.md("ROC curves show the tradeoff between true positive rate and false positive rate at different thresholds."),
        mo.ui.altair_chart(roc_chart),

        mo.md("## Key Insights"),
        mo.md("""
        ### Top Predictors of Conversion:
        1. The features at the top of the importance chart are the strongest predictors of whether a user will convert
        2. Features with positive correlation with the target variable are associated with higher conversion rates
        3. Features with negative correlation with the target variable are associated with lower conversion rates

        ### Model Performance:
        - Higher AUC values indicate better model discrimination between converted and non-converted users
        - The model with the highest AUC provides the most reliable predictions

        ### Next Steps:
        - Consider feature engineering to combine or transform highly correlated features
        - Explore threshold tuning to optimize for precision or recall based on business priorities
        - Validate findings with domain experts to ensure insights are actionable
        """)
    ])

    # Create a table of AUC values for each model
    auc_data = []
    for _name, result in results.items():
        if result['y_prob'] is not None:
            auc = roc_auc_score(y_test, result['y_prob'])
            auc_data.append({
                'Model': _name,
                'AUC': auc,
                'Accuracy': result['accuracy']
            })

    auc_df = pd.DataFrame(auc_data).sort_values('AUC', ascending=False)

    # Format the metrics to show 3 decimal places
    auc_df['AUC'] = auc_df['AUC'].map('{:.3f}'.format)
    auc_df['Accuracy'] = auc_df['Accuracy'].map('{:.3f}'.format)

    # Display the visualizations using mo.vstack
    mo.vstack([
        mo.md("## Feature Importance Across Models"),
        mo.md("This visualization shows which features are most important for predicting conversion across different models."),
        mo.ui.altair_chart(feature_importance_chart),

        mo.md("## Model Performance Metrics"),
        mo.md("This table shows the AUC and accuracy values for each model, sorted by AUC (higher is better)."),
        mo.ui.dataframe(auc_df),

        mo.md("## Correlation Between Top Features"),
        mo.md("This heatmap shows how features correlate with each other. Strong correlations may indicate redundant information."),
        mo.ui.altair_chart(correlation_chart),

        mo.md("## Model Performance Comparison (ROC Curves)"),
        mo.md("ROC curves show the tradeoff between true positive rate and false positive rate at different thresholds."),
        mo.ui.altair_chart(roc_chart),

        mo.md("## Key Insights"),
        mo.md("""
        ### Top Predictors of Conversion:
        1. The features at the top of the importance chart are the strongest predictors of whether a user will convert
        2. Features with positive correlation with the target variable are associated with higher conversion rates
        3. Features with negative correlation with the target variable are associated with lower conversion rates

        ### Model Performance:
        - Higher AUC values indicate better model discrimination between converted and non-converted users
        - The model with the highest AUC provides the most reliable predictions

        ### Next Steps:
        - Consider feature engineering to combine or transform highly correlated features
        - Explore threshold tuning to optimize for precision or recall based on business priorities
        - Validate findings with domain experts to ensure insights are actionable
        """)
    ])
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
