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
    from datetime import datetime
    load_dotenv('../.env')
    return mo, os, pd, pyoso


@app.cell
def _(os, pyoso):
    OSO_API_KEY = os.environ['OSO_API_KEY']

    client = pyoso.Client(api_key=OSO_API_KEY)
    return


@app.cell
def _(pyoso):
    pyoso_db_conn = pyoso.Client().dbapi_connection()
    return (pyoso_db_conn,)


@app.cell
def _():
    stringify = lambda arr: "'" + "','".join(arr) + "'"
    return (stringify,)


@app.cell
def fetch_data(mo, pyoso_db_conn, stringify):
    df_sre_users_all = mo.sql(
        f"""
        WITH users AS (
          SELECT
            github_handle AS user_name,
            MAX(COALESCE(challenges_completed,0)) AS challenges_completed,
            MIN(batch_id) AS batch_id,
            MIN(created_at) AS start_date
          FROM int_sre_github_users
          GROUP BY 1
        )
        SELECT
          user_name,
          start_date,
          challenges_completed,
          batch_id,
          CAST(DATE_TRUNC('MONTH', start_date) AS DATE) AS start_month,
          YEAR(start_date) AS cohort_year
        FROM users
        """,
        output=False,
        engine=pyoso_db_conn
    )

    df_github_events_all = mo.sql(
        f"""
        WITH repo_mapping AS (
          WITH repo_attributes AS (
            SELECT
              LOWER(r.name) AS repo_name,
              e.name AS ecosystem_name,
              er.ecosystem_id AS ecosystem_id
            FROM stg_opendevdata__repos r
            JOIN stg_opendevdata__ecosystems_repos_recursive er
              ON r.id = er.repo_id
            JOIN stg_opendevdata__ecosystems e
              ON e.id = er.ecosystem_id
          ),
          ecosystem_flags AS (
            SELECT
              repo_name,
              bool_or(ecosystem_name = 'Ethereum') AS is_ethereum,
              bool_or(ecosystem_name = 'Ethereum Virtual Machine Stack') AS is_evm
            FROM repo_attributes
            GROUP BY 1
          )
          SELECT
            repo_name,
            CASE
              WHEN is_ethereum THEN 'Ethereum'
              WHEN is_evm THEN 'Other EVM Chain'
              ELSE 'Other Ecosystem'
            END AS best_match_ecosystem
          FROM ecosystem_flags
        ),
        monthly_events AS (
          SELECT
           CAST(DATE_TRUNC('WEEK', event_time) AS DATE) AS bucket_week,
            CAST(DATE_TRUNC('MONTH', event_time) AS DATE) AS bucket_month,
            user_name,
            repo_name,
            github_repo_id,
            COUNT(*) AS event_count
          FROM int_sre_github_events_by_user
          WHERE
            event_type = 'PushEvent'
            AND user_name IN ({stringify(df_sre_users_all['user_name'])})
          GROUP BY 1,2,3,4,5
        )
        SELECT
          bucket_week,
          bucket_month,
          user_name,
          github_repo_id,
          repo_name,
          CASE
            WHEN user_name = split_part(repo_name, '/', 1)
              THEN 'Personal'
            WHEN best_match_ecosystem IS NOT NULL
              THEN best_match_ecosystem
            ELSE 'Unknown'
          END AS repo_label,
          event_count
        FROM monthly_events
        LEFT JOIN repo_mapping USING (repo_name)
        """,
        output=False,
        engine=pyoso_db_conn
    )
    return df_github_events_all, df_sre_users_all


@app.cell
def _(df_sre_users_all):
    df_sre_users_all.shape , df_sre_users_all.describe() , df_sre_users_all.columns
    return


@app.cell
def _(df_github_events_all):
    df_github_events_all.shape , df_github_events_all.describe() , df_github_events_all.columns
    return


@app.cell
def process_data(df_github_events_all, df_sre_users_all, pd):
    df_merged = df_github_events_all.merge(df_sre_users_all, on='user_name')
    df_merged['cohort_year'] = df_merged['cohort_year'].apply(str)
    df_merged['batch_id'] = df_merged['batch_id'].apply(lambda x: '-' if pd.isna(x) else str(int(x)).zfill(2))
    df_merged['month'] = (
        (pd.to_datetime(df_merged['bucket_month']).dt.year - pd.to_datetime(df_merged['start_month']).dt.year)*12
        + (pd.to_datetime(df_merged['bucket_month']).dt.month - pd.to_datetime(df_merged['start_month']).dt.month)
    )
    df_merged['scaffold-eth_fork'] = df_merged.apply(lambda x: "scaffold-eth" in x['repo_name'].split('/')[1] and x['repo_label'] == 'Personal', axis=1)

    _forkers = df_merged[df_merged['scaffold-eth_fork']]['user_name'].unique()
    df_merged['dev_forked_scaffold-eth'] = df_merged['user_name'].isin(_forkers)

    _experience = pd.Series(index=df_merged['user_name'].unique(), dtype='object')
    _min_months = df_merged.groupby('user_name')['month'].min()
    _delayed_start = list(_min_months[_min_months>=3].index)
    _experience.loc[_delayed_start] = 'Delayed Start'

    _regular_start = list(_min_months[_min_months<3].index)
    _month_count = df_merged[(df_merged['user_name'].isin(_regular_start)) & (df_merged['month'] < 0)].groupby('user_name')['month'].nunique()
    _reg_counts = _month_count.reindex(_regular_start).fillna(0)

    _experience.loc[_reg_counts[_reg_counts<=3].index] = 'Newb'
    _experience.loc[_reg_counts[(_reg_counts>3) & (_reg_counts<=12)].index] = 'Learning'
    _experience.loc[_reg_counts[_reg_counts>12].index] = 'Experienced'

    df_merged = df_merged.merge(_experience.rename('experience_category'), left_on='user_name', right_index=True, how='left')
    df_merged['last_month_activity'] = df_merged.groupby('user_name')['bucket_month'].transform('max')
    # df_merged.to_csv('data/df_merged.csv')
    return (df_merged,)


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
    user_table = pd.read_csv('data/user_table.csv')
    user_table
    return


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
def _():

    # def _calc_weeks_diff(start_date, end_date):
    #     if pd.isna(start_date) or pd.isna(end_date):
    #         return None
    #     days_diff = (end_date - start_date).days
    #     weeks_diff = days_diff / 7
    #     return weeks_diff

    # # Calculate weeks difference
    # def _calc_weeks_before_program(row):
    #     if pd.isna(row['bucket_week']) or pd.isna(row['start_date']):
    #         return None
    #     # Calculate the difference in days and convert to weeks
    #     days_diff = (row['start_date'] - row['bucket_week']).days
    #     weeks_diff = days_diff / 7
    #     # Round up to get discrete week numbers
    #     return min(int(np.ceil(weeks_diff)), 12)

    # user_features = df_merged.copy()


    # # Convert date columns to datetime if they aren't already
    # user_features['start_month'] = pd.to_datetime(user_features['start_month'])
    # user_features['start_date'] = pd.to_datetime(user_features['start_date'])
    # user_features['bucket_week'] = pd.to_datetime(user_features['bucket_week'])
    # user_features['bucket_month'] = pd.to_datetime(user_features['bucket_month'])


    # # 1. User age in weeks when joining program (first activity to start_month)
    # # Group by user to find their first activity ever
    # _first_activity = user_features.groupby('user_name')['bucket_week'].min().reset_index()
    # _first_activity.rename(columns={'bucket_week': 'first_activity_week_date'}, inplace=True)

    # # Merge back to original dataframe
    # user_features = user_features.merge(_first_activity, on='user_name', how='left')
    # # User age in weeks when joining program
    # user_features['user_age_weeks_at_join'] = user_features.apply(
    #     lambda row: _calc_weeks_diff(row['first_activity_week_date'], row['start_date']), 
    #     axis=1
    # )

    # # Print statistics
    # print("\n--- User Age at Program Join Statistics ---")
    # print("User age in weeks when joining program:")
    # print(user_features.groupby('user_name')['user_age_weeks_at_join'].first().describe())


    # # 2. Scaffold-eth features
    # # Find first date when user contributed to scaffold-eth fork

    # _scaffold_eth_contribs = user_features[user_features['scaffold-eth_fork'] == True].copy()
    # if not _scaffold_eth_contribs.empty:
    #     _first_scaffold_contrib = _scaffold_eth_contribs.groupby('user_name')['bucket_week'].min().reset_index()
    #     _first_scaffold_contrib.rename(columns={'bucket_week': 'first_scaffold_eth_contrib_week_date'}, inplace=True)

    #     # Merge back to original dataframe
    #     user_features = user_features.merge(_first_scaffold_contrib, on='user_name', how='left')

    #     # Calculate weeks from start to first scaffold-eth contribution
    #     user_features['first_scaffold_eth_contrib_week_date'] = user_features.apply(
    #         lambda row: _calc_weeks_diff(row['start_date'], row['first_scaffold_eth_contrib_week_date']), 
    #         axis=1
    #     )

    #     # Print statistics
    #     print("\n--- Scaffold-eth Contribution Statistics ---")
    #     print(f"Users with scaffold-eth contributions: {_first_scaffold_contrib.shape[0]}")
    #     print("Weeks to first scaffold-eth contribution:")
    #     print(user_features.groupby('user_name')['first_scaffold_eth_contrib_week_date'].first().describe())

    # # 3. Weekly activity before joining program
    # # Create a separate dataframe for pre-program activity analysis
    # _pre_program_df = user_features[user_features['bucket_week'] < user_features['start_month']].copy()

    # if not _pre_program_df.empty:
    #     # Apply the function to get week numbers
    #     _pre_program_df['week_num'] = _pre_program_df.apply(_calc_weeks_before_program, axis=1)

    #     # Filter for 12 weeks before program
    #     _pre_program_df = _pre_program_df[_pre_program_df['week_num'] <= 12]

    #     # Group by user and week to sum event counts
    #     _weekly_activity = _pre_program_df.groupby(['user_name', 'week_num'])['event_count'].sum().reset_index()

    #     # Create a pivot table for easier analysis
    #     _weekly_pivot = _weekly_activity.pivot(index='user_name', columns='week_num', values='event_count').fillna(0)

    #     # Get the actual columns that exist in the pivot table
    #     _existing_cols = sorted(_weekly_pivot.columns)
    #     print(f"Available week columns: {_existing_cols}")

    #     # Rename columns for clarity
    #     _week_cols = {i: f'events_week_minus_{i}' for i in _existing_cols}
    #     _weekly_pivot = _weekly_pivot.rename(columns=_week_cols)

    #     # Create weekly stats dataframe
    #     _weekly_stats = pd.DataFrame(index=_weekly_pivot.index)

    #     # For 4-week stats, use columns that are <= 4
    #     _4week_cols = [f'events_week_minus_{i}' for i in _existing_cols if i <= 4]
    #     if _4week_cols:  # Only proceed if we have columns
    #         _4week_data = _weekly_pivot[_4week_cols]
    #         _weekly_stats['events_4weeks_sum'] = _4week_data.sum(axis=1)
    #         _weekly_stats['events_4weeks_avg'] = _4week_data.mean(axis=1)
    #         _weekly_stats['events_4weeks_median'] = _4week_data.median(axis=1)
    #         _weekly_stats['events_4weeks_std'] = _4week_data.std(axis=1, ddof=0).fillna(0)
    #     else:
    #         print("No data available for 4-week statistics")
    #         _weekly_stats['events_4weeks_sum'] = 0
    #         _weekly_stats['events_4weeks_avg'] = 0
    #         _weekly_stats['events_4weeks_median'] = 0
    #         _weekly_stats['events_4weeks_std'] = 0

    #     # For 12-week stats, use all available columns
    #     _12week_cols = [f'events_week_minus_{i}' for i in _existing_cols if i <= 12]
    #     if _12week_cols:  # Only proceed if we have columns
    #         _12week_data = _weekly_pivot[_12week_cols]
    #         _weekly_stats['events_12weeks_sum'] = _12week_data.sum(axis=1)
    #         _weekly_stats['events_12weeks_avg'] = _12week_data.mean(axis=1)
    #         _weekly_stats['events_12weeks_median'] = _12week_data.median(axis=1)
    #         _weekly_stats['events_12weeks_std'] = _12week_data.std(axis=1, ddof=0).fillna(0)
    #     else:
    #         print("No data available for 12-week statistics")
    #         _weekly_stats['events_12weeks_sum'] = 0
    #         _weekly_stats['events_12weeks_avg'] = 0
    #         _weekly_stats['events_12weeks_median'] = 0
    #         _weekly_stats['events_12weeks_std'] = 0

    #     # Merge weekly activity data back to main dataframe
    #     # First, create a user-level dataframe with the stats
    #     _user_weekly_stats = _weekly_stats.copy()
    #     _user_weekly_stats.reset_index(inplace=True)

    #     # Merge the weekly pivot data (individual week counts)
    #     for col in _weekly_pivot.columns:
    #         _user_weekly_stats[col] = _weekly_pivot[col]

    #     # Merge back to the main dataframe
    #     user_features = user_features.merge(_user_weekly_stats, on='user_name', how='left')

    #     # Print statistics
    #     print("\n--- Pre-Program Activity Statistics ---")
    #     print("4-week activity statistics:")
    #     print(_weekly_stats[['events_4weeks_sum', 'events_4weeks_avg', 'events_4weeks_median', 'events_4weeks_std']].describe())
    #     print("\n12-week activity statistics:")
    #     print(_weekly_stats[['events_12weeks_sum', 'events_12weeks_avg', 'events_12weeks_median', 'events_12weeks_std']].describe())

    # #     # # Save the weekly activity dataframe for later plotting
    # #     # _weekly_activity_for_plotting = pd.concat([_weekly_pivot, _weekly_stats], axis=1)
    return


@app.cell
def _(user_features):
    user_features.columns
    return


@app.cell
def _(df_merged, pd):

    # Create a user-level dataframe to store our classifications
    user_features = df_merged.copy()
    user_classifications = pd.DataFrame({'user_name': user_features['user_name'].unique()})

    # Find users who contributed to Ethereum repos before joining
    _pre_program_ethereum = user_features[
        (user_features['repo_label'] == 'Ethereum') & 
        (user_features['bucket_week'] < user_features['start_date'])
    ]['user_name'].unique()

    user_classifications['already_contributor'] = user_classifications['user_name'].isin(_pre_program_ethereum)

    # Find users who contributed to Ethereum repos after joining
    _post_program_ethereum = user_features[
        (user_features['repo_label'] == 'Ethereum') & 
        (user_features['bucket_week'] >= user_features['start_date'])
    ]['user_name'].unique()

    # Binary classification for modeling
    user_classifications['converted'] = user_classifications['user_name'].isin(_post_program_ethereum)
    user_classifications['churn'] = ~user_classifications['converted']

    # Create a single classification label with 3 categories
    def _get_user_status(row):
        if row['already_contributor']:
            return "already_contributor"
        elif row['converted']:
            return "converted"
        else:
            return "churn"

    user_classifications['user_status'] = user_classifications.apply(_get_user_status, axis=1)

    # Merge the classifications back to the original dataframe
    user_features = user_features.merge(user_classifications, on='user_name', how='left')

    # Print statistics about the classifications
    print("\n--- User Classification Statistics ---")
    print(f"Total users: {user_classifications.shape[0]}")
    print(f"Already contributors before program: {user_classifications['already_contributor'].sum()} ({user_classifications['already_contributor'].mean()*100:.1f}%)")
    print(f"Converted to Ethereum after program: {user_classifications['converted'].sum()} ({user_classifications['converted'].mean()*100:.1f}%)")
    print(f"Churned (no Ethereum contribution after joining): {user_classifications['churn'].sum()} ({user_classifications['churn'].mean()*100:.1f}%)")

    print("\nUser status distribution:")
    status_counts = user_classifications['user_status'].value_counts()
    for category, count in status_counts.items():
        percentage = count / user_classifications.shape[0] * 100
        print(f"- {category}: {count} ({percentage:.1f}%)")

    return (user_features,)


@app.cell
def _():
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
