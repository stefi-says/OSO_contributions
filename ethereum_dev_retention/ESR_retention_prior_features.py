import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell
def _():
    import pyoso
    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.express as px
    from scipy.stats import gaussian_kde
    from scipy import stats
    from scipy.stats import fisher_exact
    import datetime

    # from dotenv import load_dotenv
    # import os
    # load_dotenv("../.env")
    # OSO_API_KEY = os.environ['OSO_API_KEY']
    # pyoso_db_conn = pyoso.Client(api_key=OSO_API_KEY).dbapi_connection()
    pyoso_db_conn = pyoso.Client().dbapi_connection()
    return datetime, gaussian_kde, mo, np, pd, px, pyoso_db_conn, stats


@app.cell
def _(mo):
    mo.md(r"""
    # Speedrun Ethereum: Prior Experience and Contribution Analysis

    Investigating which pre-program characteristics predict whether participants will become Ethereum contributors.
    """)
    return


@app.cell
def _():
    stringify = lambda arr: "'" + "','".join(arr) + "'"
    return (stringify,)


@app.cell
def _(mo, pyoso_db_conn, stringify):
    df_sre_users_all = mo.sql(
        f"""
        WITH users AS (
          SELECT
            github_handle AS user_name,
            MAX(COALESCE(challenges_completed,0)) AS challenges_completed,
            MIN(batch_id) AS batch_id,
            MIN(created_at) AS start_date,
            MIN_BY(location_code, created_at) AS location_code
          FROM int_sre_github_users
          GROUP BY 1
        )
        SELECT
          user_name,
          challenges_completed,
          batch_id,
          start_date,
          CAST(DATE_TRUNC('MONTH', start_date) AS DATE) AS start_month,
          CAST(DATE_TRUNC('WEEK', start_date) AS DATE) AS start_week,
          YEAR(start_date) AS cohort_year,
          location_code
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
              r.repo_id,
              e.name AS ecosystem_name,
              er.ecosystem_id AS ecosystem_id,     
              e.is_chain,
              e.is_crypto,
            FROM int_opendevdata__repositories_with_repo_id r
            JOIN stg_opendevdata__ecosystems_repos_recursive er
              ON r.opendevdata_id = er.repo_id
            JOIN stg_opendevdata__ecosystems e
              ON e.id = er.ecosystem_id
          ),
          ecosystem_flags AS (
            SELECT
              repo_id,
              bool_or(ecosystem_name = 'Ethereum' OR ecosystem_name = 'Celo') AS is_ethereum,
              bool_or(ecosystem_name = 'Ethereum Virtual Machine Stack') AS is_evm,
              bool_or(is_chain = 1) AS is_nonevm,
              bool_or(is_crypto = 1) AS is_crypto
            FROM repo_attributes
            GROUP BY 1
          )
          SELECT
            repo_id AS github_repo_id,
            CASE
              WHEN is_ethereum THEN 'Ethereum'
              WHEN is_evm THEN 'Other EVM Chain'
              WHEN is_nonevm THEN 'Non-EVM Chain'
              WHEN is_crypto THEN 'Other (Crypto-Related)'
              ELSE 'Other (Non-Crypto)'
            END AS best_match_ecosystem
          FROM ecosystem_flags
        ),
        weekly_events AS (
          SELECT
            CAST(DATE_TRUNC('WEEK', event_time) AS DATE) AS bucket_week,
            CAST(DATE_TRUNC('MONTH', event_time) AS DATE) AS bucket_month,
            user_name,
            repo_name,
            github_repo_id,
            COUNT(*) AS event_count
          FROM int_sre_github_events_by_user
          WHERE
            event_type IN ('PushEvent', 'PullRequestEvent')
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
            WHEN best_match_ecosystem IS NOT NULL
              THEN best_match_ecosystem
            WHEN user_name = split_part(repo_name, '/', 1)
              THEN 'Personal'
            ELSE 'Unknown'
          END AS repo_label,
          event_count
        FROM weekly_events
        LEFT JOIN repo_mapping USING (github_repo_id)
        """,
        output=False,
        engine=pyoso_db_conn
    )


    # df_github_velocity_all = mo.sql(
    #     f"""
    #     WITH daily_activity AS(
    #       SELECT
    #         DATE_TRUNC('DAY', event_time) AS bucket_day,
    #         user_name,
    #         COUNT(*) AS event_count
    #       FROM int_sre_github_events_by_user
    #       WHERE
    #         event_type IN ('PushEvent', 'PullRequestEvent')
    #         AND user_name IN ({stringify(df_sre_users_all['user_name'])})
    #       GROUP BY 1,2
    #     )

    #     SELECT
    #       CAST(DATE_TRUNC('MONTH', bucket_day) AS DATE) AS bucket_month,
    #       user_name,
    #       SUM(1 + ln(event_count)) AS velocity
    #     FROM daily_activity
    #     GROUP BY 1,2
    #     """,
    #     output=False,
    #     engine=pyoso_db_conn
    # )
    return df_github_events_all, df_sre_users_all


@app.cell
def _(df_github_events_all, df_sre_users_all, pd):
    df_merged = df_github_events_all.merge(df_sre_users_all, on='user_name')
    df_merged['cohort_year'] = df_merged['cohort_year'].apply(str)
    df_merged['batch_id'] = df_merged['batch_id'].apply(lambda x: '-' if pd.isna(x) else str(int(x)).zfill(2))

    df_merged['bucket_week'] = pd.to_datetime(df_merged['bucket_week'])
    df_merged['bucket_month'] = pd.to_datetime(df_merged['bucket_month'])
    df_merged['start_date'] = pd.to_datetime(df_merged['start_date'])
    df_merged['start_month'] = pd.to_datetime(df_merged['start_month'])
    df_merged['start_week'] = pd.to_datetime(df_merged['start_week'])

    df_merged['month'] = (
        (df_merged['bucket_month'].dt.year - df_merged['start_month'].dt.year) * 12
        + (df_merged['bucket_month'].dt.month - df_merged['start_month'].dt.month)
    )

    df_merged['scaffold-eth_fork'] = df_merged.apply(
        lambda x: "scaffold-eth" in x['repo_name'].split('/')[1] if '/' in x['repo_name'] and x['repo_label'] == 'Personal' else False, 
        axis=1
    )

    _forkers = df_merged[df_merged['scaffold-eth_fork']]['user_name'].unique()
    df_merged['dev_forked_scaffold-eth'] = df_merged['user_name'].isin(_forkers)

    _user_summary = (
        df_merged
        .assign(prior_month=lambda d: d['month'].where(d['month'] < 0))
        .groupby('user_name')
        .agg(
            min_month=('month', 'min'),
            months_of_prior_activity=('prior_month', lambda s: s.nunique()),
            first_month_activity=('bucket_month', 'min'),
            last_month_activity=('bucket_month', 'max'),
            start_month=('start_month', 'min')
        )
    )

    def classify_experience(row):
        if row['min_month'] >= 3:
            return 'Newb'
        m = row['months_of_prior_activity']
        if m > 12:
            return 'Experienced'
        elif m > 3:
            return 'Learning'
        else:
            return 'Newb'

    _user_summary['experience_category'] = _user_summary.apply(classify_experience, axis=1)

    df_merged = df_merged.merge(
        _user_summary[['first_month_activity', 'last_month_activity', 'months_of_prior_activity', 'experience_category']],
        left_on='user_name',
        right_index=True,
        how='left'
    )

    _post_program_ethereum = df_merged[
        (df_merged['repo_label'] == 'Ethereum') & 
        (df_merged['bucket_week'] >= df_merged['start_date'])
    ]['user_name'].unique()
    df_merged['activated'] = df_merged['user_name'].isin(_post_program_ethereum)
    return (df_merged,)


@app.cell
def _(df_merged, pd):
    user_convertion = df_merged.copy()
    user_classifications = pd.DataFrame({'user_name': user_convertion['user_name'].unique()})

    _pre_program_coders = user_convertion[
        user_convertion['bucket_week'] < user_convertion['start_date']
    ]['user_name'].unique()

    user_classifications['already_coder'] = user_classifications['user_name'].isin(_pre_program_coders)

    _non_coders = user_classifications[~user_classifications['already_coder']]['user_name'].unique()

    _post_program_events = user_convertion[
        (user_convertion['user_name'].isin(_non_coders)) & 
        (user_convertion['bucket_week'] >= user_convertion['start_date'])
    ]['user_name'].unique()

    user_classifications['converted_to_coder'] = user_classifications['user_name'].isin(_post_program_events)
    user_classifications['coder_churn'] = (~user_classifications['already_coder']) & (~user_classifications['converted_to_coder'])

    _pre_program_ethereum = user_convertion[
        (user_convertion['repo_label'] == 'Ethereum') & 
        (user_convertion['bucket_week'] < user_convertion['start_date'])
    ]['user_name'].unique()

    user_classifications['already_ethereum_contributor'] = user_classifications['user_name'].isin(_pre_program_ethereum)

    _post_program_ethereum = user_convertion[
        (~user_convertion['user_name'].isin(_pre_program_ethereum)) & 
        (user_convertion['repo_label'] == 'Ethereum') & 
        (user_convertion['bucket_week'] >= user_convertion['start_date'])
    ]['user_name'].unique()

    user_classifications['converted_to_ethereum'] = user_classifications['user_name'].isin(_post_program_ethereum)
    user_classifications['ethereum_churn'] = (~user_classifications['already_ethereum_contributor']) & (~user_classifications['converted_to_ethereum'])

    _pre_program_evm = user_convertion[
        (user_convertion['repo_label'].isin(['Ethereum', 'Other EVM Chain'])) & 
        (user_convertion['bucket_week'] < user_convertion['start_date'])
    ]['user_name'].unique()

    user_classifications['already_evm_contributor'] = user_classifications['user_name'].isin(_pre_program_evm)

    _post_program_evm = user_convertion[
        (~user_convertion['user_name'].isin(_pre_program_evm)) & 
        (user_convertion['repo_label'].isin(['Ethereum', 'Other EVM Chain'])) & 
        (user_convertion['bucket_week'] >= user_convertion['start_date'])
    ]['user_name'].unique()

    user_classifications['converted_to_evm'] = user_classifications['user_name'].isin(_post_program_evm)
    user_classifications['evm_churn'] = (~user_classifications['already_evm_contributor']) & (~user_classifications['converted_to_evm'])

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
    return (user_classifications,)


@app.cell
def _(df_merged, np, pd):
    def _calc_weeks_diff(start_date, end_date):
        if pd.isna(start_date) or pd.isna(end_date):
            return None
        days_diff = (end_date - start_date).days
        weeks_diff = days_diff / 7
        return weeks_diff

    def _calc_weeks_before_program(row):
        if pd.isna(row['bucket_week']) or pd.isna(row['start_date']):
            return None
        days_diff = (row['start_date'] - row['bucket_week']).days
        weeks_diff = days_diff / 7
        return min(int(np.ceil(weeks_diff)), 12)

    user_features = df_merged.copy()

    _first_activity = user_features.groupby('user_name')['bucket_week'].min().reset_index()
    _first_activity.rename(columns={'bucket_week': 'first_activity_week_date'}, inplace=True)

    user_features = user_features.merge(_first_activity, on='user_name', how='left')
    user_features['user_age_weeks_at_join'] = user_features.apply(
        lambda row: _calc_weeks_diff(row['first_activity_week_date'], row['start_date']), 
        axis=1
    )

    _scaffold_eth_contribs = user_features[user_features['scaffold-eth_fork'] == True].copy()
    if not _scaffold_eth_contribs.empty:
        _first_scaffold_contrib = _scaffold_eth_contribs.groupby('user_name')['bucket_week'].min().reset_index()
        _first_scaffold_contrib.rename(columns={'bucket_week': 'first_scaffold_eth_contrib_week_date'}, inplace=True)
        user_features = user_features.merge(_first_scaffold_contrib, on='user_name', how='left')
        user_features['scaffold_eth_contrib_week_diff'] = user_features.apply(
            lambda row: _calc_weeks_diff(row['start_date'], row['first_scaffold_eth_contrib_week_date']), 
            axis=1
        )
    else:
        user_features['first_scaffold_eth_contrib_week_date'] = None
        user_features['scaffold_eth_contrib_week_diff'] = None

    _pre_program_df = user_features[user_features['bucket_week'] < user_features['start_month']].copy()

    if not _pre_program_df.empty:
        _pre_program_df['week_num'] = _pre_program_df.apply(_calc_weeks_before_program, axis=1)
        _pre_program_df = _pre_program_df[_pre_program_df['week_num'] <= 12]
        _weekly_activity = _pre_program_df.groupby(['user_name', 'week_num'])['event_count'].sum().reset_index()
        _weekly_pivot = _weekly_activity.pivot(index='user_name', columns='week_num', values='event_count').fillna(0)
        _existing_cols = sorted(_weekly_pivot.columns)
        _week_cols = {_i: f'events_week_minus_{_i}' for _i in _existing_cols}
        _weekly_pivot = _weekly_pivot.rename(columns=_week_cols)
        _weekly_stats = pd.DataFrame(index=_weekly_pivot.index)

        _4week_cols = [f'events_week_minus_{_i}' for _i in _existing_cols if _i <= 4]
        if _4week_cols:
            _4week_data = _weekly_pivot[_4week_cols]
            _weekly_stats['events_4weeks_sum'] = _4week_data.sum(axis=1)
            _weekly_stats['events_4weeks_avg'] = _4week_data.mean(axis=1)
            _weekly_stats['events_4weeks_median'] = _4week_data.median(axis=1)
            _weekly_stats['events_4weeks_std'] = _4week_data.std(axis=1, ddof=0).fillna(0)
        else:
            _weekly_stats['events_4weeks_sum'] = 0
            _weekly_stats['events_4weeks_avg'] = 0
            _weekly_stats['events_4weeks_median'] = 0
            _weekly_stats['events_4weeks_std'] = 0

        _12week_cols = [f'events_week_minus_{_i}' for _i in _existing_cols if _i <= 12]
        if _12week_cols:
            _12week_data = _weekly_pivot[_12week_cols]
            _weekly_stats['events_12weeks_sum'] = _12week_data.sum(axis=1)
            _weekly_stats['events_12weeks_avg'] = _12week_data.mean(axis=1)
            _weekly_stats['events_12weeks_median'] = _12week_data.median(axis=1)
            _weekly_stats['events_12weeks_std'] = _12week_data.std(axis=1, ddof=0).fillna(0)
        else:
            _weekly_stats['events_12weeks_sum'] = 0
            _weekly_stats['events_12weeks_avg'] = 0
            _weekly_stats['events_12weeks_median'] = 0
            _weekly_stats['events_12weeks_std'] = 0

        _user_weekly_stats = _weekly_stats.copy()
        _user_weekly_stats.reset_index(inplace=True)

        user_features = user_features.merge(_user_weekly_stats, on='user_name', how='left')
    else:
        user_features['events_4weeks_sum'] = 0
        user_features['events_4weeks_avg'] = 0
        user_features['events_4weeks_median'] = 0
        user_features['events_4weeks_std'] = 0
        user_features['events_12weeks_sum'] = 0
        user_features['events_12weeks_avg'] = 0
        user_features['events_12weeks_median'] = 0
        user_features['events_12weeks_std'] = 0

    user_features = user_features[[
        'user_name', 'challenges_completed', 'dev_forked_scaffold-eth',
        'scaffold_eth_contrib_week_diff', 'experience_category', 'user_age_weeks_at_join',
        'events_4weeks_sum', 'events_4weeks_avg', 'events_4weeks_median', 'events_4weeks_std',
        'events_12weeks_sum', 'events_12weeks_avg', 'events_12weeks_median', 'events_12weeks_std'
    ]].drop_duplicates()
    return (user_features,)


@app.cell
def _(user_classifications, user_features):
    df = user_features.merge(user_classifications[["user_name", "coder_status", "ethereum_status", "evm_status"]], on='user_name', how='left')
    return (df,)


@app.cell
def _():
    ## User Classification Overview
    return


@app.cell
def _(mo):
    mo.md("""
    The following tables show the composition of the user sample on their coding and Ethereum contribution status. .
    """)
    return


@app.cell
def _(df, mo):
    _coder_counts = df["coder_status"].value_counts().reset_index()
    _coder_counts.columns = ["Status", "Count"]
    _coder_counts["Percentage"] = (df["coder_status"].value_counts(normalize=True) * 100).round(1).values
    _coder_counts["Percentage"] = _coder_counts["Percentage"].astype(str) + "%"

    mo.vstack([
        mo.md("### Coder Status Distribution"),
        mo.ui.table(_coder_counts)
    ])
    return


@app.cell
def _(df, mo):
    _eth_counts = df["ethereum_status"].value_counts().reset_index()
    _eth_counts.columns = ["Status", "Count"]
    _eth_counts["Percentage"] = (df["ethereum_status"].value_counts(normalize=True) * 100).round(1).values
    _eth_counts["Percentage"] = _eth_counts["Percentage"].astype(str) + "%"

    mo.vstack([
        mo.md("### Ethereum Contributor Status Distribution"),
        mo.ui.table(_eth_counts)
    ])
    return


@app.cell
def _(df, mo):
    _evm_counts = df["evm_status"].value_counts().reset_index()
    _evm_counts.columns = ["Status", "Count"]
    _evm_counts["Percentage"] = (df["evm_status"].value_counts(normalize=True) * 100).round(1).values
    _evm_counts["Percentage"] = _evm_counts["Percentage"].astype(str) + "%"

    mo.vstack([
        mo.md("### EVM Contributor Status Distribution"),
        mo.ui.table(_evm_counts)
    ])
    return


@app.cell
def _(mo):
    mo.md("""
    ## Cross-Category Analysis: Coder Status → Ethereum Status

    This Sankey diagram shows how users flow from their general coding status to their Ethereum contribution status.
    """)
    return


@app.cell
def _(df, go, mo):
    _cross = df.groupby(["coder_status", "ethereum_status"]).size().reset_index(name="count")
    _total = len(df)
    _cross["percentage"] = (_cross["count"] / _total * 100).round(1)

    _coder_labels = ["already_coder", "converted_to_coder", "coder_churn"]
    _eth_labels = ["already_ethereum_contributor", "converted_to_ethereum", "ethereum_churn"]
    _all_labels = _coder_labels + _eth_labels

    _label_to_idx = {label: idx for idx, label in enumerate(_all_labels)}

    _sources = []
    _targets = []
    _values = []
    _colors = []
    _custom_data = []

    _color_map = {
        "already_ethereum_contributor": "rgba(46, 204, 113, 0.6)",
        "converted_to_ethereum": "rgba(52, 152, 219, 0.6)",
        "ethereum_churn": "rgba(231, 76, 60, 0.6)"
    }

    for _, row in _cross.iterrows():
        _sources.append(_label_to_idx[row["coder_status"]])
        _targets.append(_label_to_idx[row["ethereum_status"]])
        _values.append(row["count"])
        _colors.append(_color_map.get(row["ethereum_status"], "rgba(128, 128, 128, 0.5)"))
        _custom_data.append(f"{row['count']:,} users ({row['percentage']}%)")

    _fig_sankey = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=_all_labels,
            color=["#2ecc71", "#3498db", "#e74c3c", "#27ae60", "#2980b9", "#c0392b"]
        ),
        link=dict(
            source=_sources,
            target=_targets,
            value=_values,
            color=_colors,
            customdata=_custom_data,
            hovertemplate='%{source.label} → %{target.label}<br>%{customdata}<extra></extra>'
        )
    )])

    _fig_sankey.update_layout(
        title_text="User Flow: Coder Status → Ethereum Status",
        font_size=12,
        height=500
    )

    mo.ui.plotly(_fig_sankey)
    return


@app.cell
def _(mo):
    mo.md("""
    As shown above, 36% of participants were already Ethereum contributors before joining. To properly analyze the characteristics that predict conversion, we will exclude these users from the analysis going forward and focus only on participants who were not yet contributing to the Ethereum ecosystem.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Comparing Converted vs. Churned Users: Pre-Program Activity Features
    """)
    return


@app.cell
def _(df):
    df_analysis = df[df.ethereum_status != "already_ethereum_contributor"].copy()
    df_analysis[['events_4weeks_sum', 'events_12weeks_sum', 'events_4weeks_median','events_12weeks_median', 'events_12weeks_avg', 'events_4weeks_avg']] = df_analysis[['events_4weeks_sum', 'events_12weeks_sum', 'events_4weeks_median','events_12weeks_median', 'events_12weeks_avg', 'events_4weeks_avg']].fillna(0)
    return (df_analysis,)


@app.cell
def _(df_analysis, mo):
    _population_distribution = df_analysis["ethereum_status"].value_counts(normalize = True).reset_index()
    _population_distribution = _population_distribution.merge(df_analysis["ethereum_status"].value_counts().reset_index(), on = "ethereum_status", how = "left")
    _population_distribution["count"] = _population_distribution["count"].round(0).astype(int)
    _population_distribution.columns = ["ethereum_status", "percentage", "count"]
    mo.vstack([
        mo.md("### Checking the Population Distribution"),
        mo.ui.table(_population_distribution)

    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Analysing activity distributions
    """)
    return


@app.cell
def _(mo):
    feature_options = {
        "User Age at Join (weeks)": "user_age_weeks_at_join",
        "Events 4 Weeks - Sum": "events_4weeks_sum",
        "Events 4 Weeks - Average": "events_4weeks_avg",
        "Events 4 Weeks - Median": "events_4weeks_median",
        "Events 12 Weeks - Sum": "events_12weeks_sum",
        "Events 12 Weeks - Average": "events_12weeks_avg",
        "Events 12 Weeks - Median": "events_12weeks_median",
    }

    feature_selector = mo.ui.dropdown(
        options=list(feature_options.keys()),
        value="User Age at Join (weeks)",
        label="Select Feature to Analyze"
    )
    feature_selector
    return feature_options, feature_selector


@app.cell
def _(df_analysis, feature_options, feature_selector, go, mo, np, px, stats):

    _selected_label = feature_selector.value
    _selected_col = feature_options[_selected_label]

    _fig_kde = go.Figure()
    _colors = px.colors.qualitative.Plotly

    for i, status in enumerate(df_analysis["ethereum_status"].unique()):
        _data = df_analysis[df_analysis["ethereum_status"] == status][_selected_col].dropna()
        if len(_data) > 1:
            _kde = stats.gaussian_kde(_data)
            _x_range = np.linspace(_data.min(), _data.max(), 200)
            _y_kde = _kde(_x_range)
            _fig_kde.add_trace(go.Scatter(
                x=_x_range, 
                y=_y_kde, 
                mode='lines',
                fill='tozeroy',
                name=str(status),
                opacity=0.6,
                line=dict(color=_colors[i % len(_colors)])
            ))

    _fig_kde.update_layout(
        title=f"{_selected_label} - Density Distribution by Ethereum Status",
        xaxis_title=_selected_label,
        yaxis_title="Density"
    )

    _fig_box = px.box(
        df_analysis, 
        x="ethereum_status", 
        y=_selected_col,
        points=False,
        color="ethereum_status",
        title=f"{_selected_label} - Box Plot by Ethereum Status",
        labels={_selected_col: _selected_label, "ethereum_status": "Ethereum Status"}
    )

    mo.vstack([
        mo.ui.plotly(_fig_kde),
        mo.ui.plotly(_fig_box)
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Exploring Activity Distribution Differences Between Groups

    Using the sum of GitHub events in the 12 weeks prior to joining, we examine whether activity levels can distinguish users who will convert from those who will churn.
    """)
    return


@app.cell
def _(df_analysis, gaussian_kde, go, mo, np):

    _kde_convert = gaussian_kde(df_analysis[df_analysis["ethereum_status"] == "converted_to_ethereum"]["events_12weeks_sum"])
    _kde_churn = gaussian_kde(df_analysis[df_analysis["ethereum_status"] == "ethereum_churn"]["events_12weeks_sum"])

    _p_convert = df_analysis["ethereum_status"].value_counts(normalize=True).loc["converted_to_ethereum"]
    _p_churn = df_analysis["ethereum_status"].value_counts(normalize=True).loc["ethereum_churn"]

    _x_range = np.linspace(0, 3000, 3000)
    _convert_density = _kde_convert(_x_range) * _p_convert
    _churn_density = _kde_churn(_x_range) * _p_churn
    _y_probs = _convert_density / (_convert_density + _churn_density)

    _fig = go.Figure()

    _fig.add_trace(go.Scatter(
        x=_x_range,
        y=_y_probs,
        mode='lines',
        name='P(Converted | Activity)',
        line=dict(color='#3498db', width=3)
    ))

    _fig.add_hline(y=0.5, line_dash="dash", line_color="gray", 
                   annotation_text="50% threshold", annotation_position="right")

    _fig.update_layout(
        title="Probability of Conversion vs. 12-Week Activity",
        xaxis_title="Events in Last 12 Weeks",
        yaxis_title="P(Converted | Activity)",
        yaxis=dict(tickformat='.0%', range=[0, 1]),
        hovermode='x unified'
    )

    mo.ui.plotly(_fig)
    return


@app.cell
def _(df_analysis):
    df_analysis[df_analysis.events_12weeks_sum > 2530]
    return


@app.cell
def _(mo):
    mo.md("""
    ### Conclusion of the 12-Week Activity Distribution Analysis

    The converted and churned groups have very similar distributions, with significant overlap for users with up to ~1,000 events.

    **Key finding:** Users with 3,500+ events have a >70% probability of converting. However, only 0.6% of users fall into this category, making this threshold highly precise but with low recall, therefore too few candidates to be actionable for targeting purposes.
    As the 4 weeks activity distribution visually shows the same pattern and is contained in the 12 weeks activity distribution, we can discard this feature too from being a good predictor of future conversion.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Analyzing Prior Repository Contributions

    We examine which repositories, organizations, and ecosystem categories users contributed to before joining the program, looking for patterns that differentiate converters from churners.
    """)
    return


@app.cell
def _(df_analysis, df_merged):
    c = df_merged[df_merged.bucket_week < df_merged.start_week ][[ 'user_name' ,  'github_repo_id','repo_name', 'repo_label']].copy() 
    c.drop_duplicates(inplace = True)
    c = c.merge(df_analysis[['user_name', 'ethereum_status']], on = 'user_name', how = 'inner')
    c["organization_name"] = c["repo_name"].str.split("/").str[0]
    c["repo_title"] = c["repo_name"].str.split("/").str[1]
    return


@app.cell
def _(datetime, df_analysis, df_merged):
    ### one year prior before contributing to eth 
    oneyearpr = df_merged[ (df_merged.bucket_week >= df_merged.start_week - datetime.timedelta(weeks=52)) & (df_merged.bucket_week < df_merged.start_week)][[ 'user_name' ,  'github_repo_id','repo_name', 'repo_label']].copy() 
    oneyearpr.drop_duplicates(inplace = True)
    oneyearpr = oneyearpr.merge(df_analysis[['user_name', 'ethereum_status']], on = 'user_name', how = 'inner')
    oneyearpr["organization_name"] = oneyearpr["repo_name"].str.split("/").str[0]
    oneyearpr["repo_title"] = oneyearpr["repo_name"].str.split("/").str[1]
    return (oneyearpr,)


@app.cell
def _(oneyearpr):
    oneyearpr.groupby("ethereum_status")["user_name"].nunique()
    return


@app.cell
def _(mo):
    repo_grouping_options = {
        "Repository Label": "repo_label",
        "Repository Title": "repo_title",
        "Organization Name": "organization_name"
    }

    repo_grouping_selector = mo.ui.dropdown(
        options=list(repo_grouping_options.keys()),
        value="Repository Label",
        label="Group by"
    )

    top_n_selector = mo.ui.slider(
        start=5,
        stop=30,
        step=5,
        value=15,
        label="Top N items to show"
    )

    mo.hstack([repo_grouping_selector, top_n_selector])
    return repo_grouping_options, repo_grouping_selector, top_n_selector


@app.cell
def _(
    mo,
    oneyearpr,
    px,
    repo_grouping_options,
    repo_grouping_selector,
    top_n_selector,
):
    _selected_label = repo_grouping_selector.value
    _selected_col = repo_grouping_options[_selected_label]
    _top_n = top_n_selector.value

    _grouped = oneyearpr.groupby(["ethereum_status", _selected_col])["user_name"].nunique().reset_index()
    _grouped.columns = ["ethereum_status", _selected_label, "user_count"]

    _top_items = (
        _grouped.groupby(_selected_label)["user_count"]
        .sum()
        .sort_values(ascending=False)
        .head(_top_n)
        .index.tolist()
    )
    _grouped_filtered = _grouped[_grouped[_selected_label].isin(_top_items)]

    _fig = px.bar(
        _grouped_filtered,
        x=_selected_label,
        y="user_count",
        color="ethereum_status",
        barmode="group",
        title=f"User Count by {_selected_label} (Top {_top_n}) - One Year Prior to Program",
        labels={
            "user_count": "Number of Users",
            _selected_label: _selected_label,
            "ethereum_status": "Ethereum Status"
        },
        color_discrete_map={
            "converted_to_ethereum": "#3498db",
            "ethereum_churn": "#e74c3c"
        }
    )

    _fig.update_layout(
        xaxis_tickangle=-45,
        legend_title="Ethereum Status",
        height=500
    )

    mo.ui.plotly(_fig)
    return


@app.cell
def _(
    mo,
    oneyearpr,
    px,
    repo_grouping_options,
    repo_grouping_selector,
    top_n_selector,
):
    _selected_label = repo_grouping_selector.value
    _selected_col = repo_grouping_options[_selected_label]
    _top_n = top_n_selector.value

    _grouped = oneyearpr.groupby(["ethereum_status", _selected_col])["user_name"].nunique().reset_index()
    _grouped.columns = ["ethereum_status", _selected_label, "user_count"]

    _total_per_status = oneyearpr.groupby("ethereum_status")["user_name"].nunique().to_dict()
    _grouped["user_proportion"] = _grouped.apply(
        lambda row: row["user_count"] / _total_per_status[row["ethereum_status"]] * 100, 
        axis=1
    )

    _top_items = (
        _grouped.groupby(_selected_label)["user_count"]
        .sum()
        .sort_values(ascending=False)
        .head(_top_n)
        .index.tolist()
    )
    _grouped_filtered = _grouped[_grouped[_selected_label].isin(_top_items)]

    _fig = px.bar(
        _grouped_filtered,
        x=_selected_label,
        y="user_proportion",
        color="ethereum_status",
        barmode="group",
        title=f"User Proportion by {_selected_label} (Top {_top_n}) - One Year Prior to Program",
        labels={
            "user_proportion": "% of Users in Status Group",
            _selected_label: _selected_label,
            "ethereum_status": "Ethereum Status"
        },
        color_discrete_map={
            "converted_to_ethereum": "#3498db",
            "ethereum_churn": "#e74c3c"
        },
        text=_grouped_filtered["user_proportion"].round(1).astype(str) + "%"
    )

    _fig.update_traces(textposition='outside')
    _fig.update_layout(
        xaxis_tickangle=-45,
        legend_title="Ethereum Status",
        height=500,
        yaxis_ticksuffix="%"
    )

    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Odds ratio analysis

    Checking the odds ratio of users converting given they have contributed to a certain repo, organization or repo category.

    **Methodology:**
    - For each category (repo label, organization, or repo title), we build a 2x2 contingency table comparing users who contributed vs. didn't contribute, split by conversion status
    - We apply **Fisher's exact test** to determine if the association is statistically significant (p < 0.05)
    - The **odds ratio** tells us how much more likely a contributor to that category is to convert compared to non-contributors
    - **Relative lift** shows the ratio of contribution rates between converted and churned users
    """)
    return


@app.cell
def _(
    mo,
    oneyearpr,
    pd,
    repo_grouping_options,
    repo_grouping_selector,
    top_n_selector,
):
    from scipy.stats import fisher_exact

    _selected_label = repo_grouping_selector.value
    _selected_col = repo_grouping_options[_selected_label]
    _top_n = top_n_selector.value

    _total_converted = oneyearpr[oneyearpr["ethereum_status"] == "converted_to_ethereum"]["user_name"].nunique()
    _total_churn = oneyearpr[oneyearpr["ethereum_status"] == "ethereum_churn"]["user_name"].nunique()

    _grouped = oneyearpr.groupby(["ethereum_status", _selected_col])["user_name"].nunique().reset_index()
    _grouped.columns = ["ethereum_status", _selected_label, "user_count"]

    _top_items = (
        _grouped.groupby(_selected_label)["user_count"]
        .sum()
        .sort_values(ascending=False)
        .head(_top_n)
        .index.tolist()
    )

    _results = []

    for _item in _top_items:
        _converted_contrib = _grouped[
            (_grouped["ethereum_status"] == "converted_to_ethereum") & 
            (_grouped[_selected_label] == _item)
        ]["user_count"].sum()

        _churn_contrib = _grouped[
            (_grouped["ethereum_status"] == "ethereum_churn") & 
            (_grouped[_selected_label] == _item)
        ]["user_count"].sum()

        _converted_not_contrib = _total_converted - _converted_contrib
        _churn_not_contrib = _total_churn - _churn_contrib

        _table = [
            [_converted_contrib, _converted_not_contrib],
            [_churn_contrib, _churn_not_contrib]
        ]

        _odds_ratio, _p_value = fisher_exact(_table, alternative="two-sided")

        _rate_converted = _converted_contrib / _total_converted * 100
        _rate_churn = _churn_contrib / _total_churn * 100
        _relative_lift = _rate_converted / _rate_churn if _rate_churn > 0 else float('inf')

        _significance = "✓ Significant" if _p_value < 0.05 else "Not Significant"
        _direction = "↑ Favors Conversion" if _odds_ratio > 1 else "↓ Favors Churn" if _odds_ratio < 1 else "Neutral"

        _results.append({
            _selected_label: _item,
            "Converted %": f"{_rate_converted:.1f}%",
            "Churn %": f"{_rate_churn:.1f}%",
            "Odds Ratio": round(_odds_ratio, 2),
            "Relative Lift": f"{_relative_lift:.2f}x",
            "p-value": f"{_p_value:.4f}" if _p_value >= 0.0001 else "<0.0001",
            "Significance (p<0.05)": _significance,
            "Direction": _direction
        })

    _results_df = pd.DataFrame(_results)

    mo.vstack([
        mo.md(f"""
    ### Odds Ratio Analysis: {_selected_label}

    **Interpretation:**
    - **Odds Ratio > 1**: Contributors to this {_selected_label.lower()} are more likely to convert
    - **Odds Ratio < 1**: Contributors to this {_selected_label.lower()} are more likely to churn
    - **Relative Lift**: How many times more likely converted users are to contribute vs churn users
        """),
        mo.ui.table(_results_df)
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Conclusion

    **Activity volume alone is not a strong predictor:** The distribution of pre-program activity for converted vs. churned users showed significant overlap, indicating that raw activity metrics are poor predictors of future conversion.

    **Prior ecosystem contributions matter:**  odds ratio analysis revealed statistically significant associations between prior contributions to certain repo categories and future Ethereum conversion:

    | Repo Category | Odds Ratio | Interpretation |
    |---------------|------------|----------------|
    | Other EVM Chain | 2.68x | Strongest predictor |
    | Other Crypto-Related | 1.73x | Moderate predictor |
    | Non-EVM Chain | 1.67x | Moderate predictor |

    Users with prior contributions to blockchain/crypto ecosystems are significantly more likely to become Ethereum contributors after joining the program.
    There were no indication of specific repo or organization that would be a good predictor of future conversion.
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
