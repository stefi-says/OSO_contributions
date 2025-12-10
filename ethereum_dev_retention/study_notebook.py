

@app.cell
def _():
    import marimo as mo
    import pyoso
    import pandas as pd
    import os
    from dotenv import load_dotenv
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
def _(mo):
    mo.md(r"""
    # Exploring the tables and queries
    """)
    return


@app.cell
def _(pd, pyoso_db_conn):
    # Developer lifecycle data - monthly aggregated
    query = """
    SELECT * FROM int_crypto_ecosystems_developer_lifecycle_monthly_aggregated
    limit 15
    """
    lifecycle_df = pd.read_sql(query, pyoso_db_conn)

    # Save to CSV
    lifecycle_df.to_csv('tables_csv/int_crypto_ecosystems_developer_lifecycle_monthly_aggregated.csv', index=False)

    lifecycle_df
    return


@app.cell
def _(pd, pyoso_db_conn):
    # GitHub events data
    query_int_monthly = """
    SELECT * FROM int_events_monthly__github
    LIMIT 15
    """
    github_events_df = pd.read_sql(query_int_monthly, pyoso_db_conn)

    # Save to CSV
    github_events_df.to_csv('tables_csv/int_events_monthly__github.csv', index=False)

    github_events_df
    return


@app.cell
def _(pd, pyoso_db_conn):
    # Repository collections data
    query_artifacts_by_collection = """
    SELECT * FROM artifacts_by_collection_v1
    LIMIT 15
    """
    repo_collections_df = pd.read_sql(query_artifacts_by_collection, pyoso_db_conn)

    # Save to CSV
    repo_collections_df.to_csv('tables_csv/artifacts_by_collection_v1.csv', index=False)

    repo_collections_df
    return


@app.cell
def _(pd, pyoso_db_conn):
    # Ecosystem repository data
    int_opendevdata_ecosystem_repos = """
    SELECT * FROM int_opendevdata_ecosystem_repos
    LIMIT 15
    """
    ecosystem_repos_df = pd.read_sql(int_opendevdata_ecosystem_repos, pyoso_db_conn)

    # Save to CSV
    ecosystem_repos_df.to_csv('tables_csv/int_opendevdata_ecosystem_repos.csv', index=False)

    ecosystem_repos_df
    return


@app.cell
def _(pd, pyoso_db_conn):
    # Ecosystem repository data
    distinct_ecosystem_name = """
    SELECT distinct(ecosystem_name) FROM int_opendevdata_ecosystem_repos
    where ecosystem_name like '%AI%'
    LIMIT 15
    """
    ecossytem_names = pd.read_sql(distinct_ecosystem_name, pyoso_db_conn)
    ecossytem_names
    return


@app.cell
def _(mo, pd, pyoso_db_conn):
    # Sample query to explore ecosystems of interest
    merged_query = """
    SELECT DISTINCT project_display_name
    FROM int_crypto_ecosystems_developer_lifecycle_monthly_aggregated
    WHERE project_display_name IN ('Ethereum', 'Solana')
    OR project_display_name LIKE '%AI%'
    """
    ecosystems_df = pd.read_sql(merged_query, pyoso_db_conn)
    mo.md("### Available Ecosystems for Analysis")
    ecosystems_df
    return


@app.cell
def _(mo, pd, pyoso_db_conn):
    # AI repositories filtering approach from the reference notebook
    mo.md("### AI Ecosystem Filtering Approach")
    ai_repos_query = """
    -- This shows how the reference notebook identifies AI repositories
    WITH ai_repos AS ( 
      SELECT DISTINCT artifact_id
      FROM artifacts_by_collection_v1
      WHERE
        collection_name IN (
          'ossinsight-ai-agent-frameworks',
          'ossinsight-artificial-intelligence'
        )
        AND artifact_source = 'GITHUB'
    )
    SELECT COUNT(*) as ai_repo_count FROM ai_repos
    """
    ai_repos_count = pd.read_sql(ai_repos_query, pyoso_db_conn)
    ai_repos_count
    return


@app.cell
def _(mo, pd, pyoso_db_conn):
    # Example of the combined repos approach from reference notebook
    mo.md("### Combined Repositories Approach")
    combined_repos_query = """
    -- This shows how the reference notebook combines different ecosystems
    WITH
    -- AI repositories from collections
    ai_repos AS ( 
      SELECT DISTINCT artifact_id
      FROM artifacts_by_collection_v1
      WHERE
        collection_name IN (
          'ossinsight-ai-agent-frameworks',
          'ossinsight-artificial-intelligence'
        )
        AND artifact_source = 'GITHUB'
    ),
    -- Crypto repositories from Electric Capital data
    crypto_repos AS (
      SELECT
        DISTINCT
          artifact_id,
          ecosystem_name
      FROM int_opendevdata_ecosystem_repos
      WHERE
        ecosystem_name IN (
          'Ethereum',
          'Solana'
        )
    ),
    -- Combined repositories with ecosystem labels
    combined_repos AS (
      SELECT
        artifact_id,
        'AI' AS ecosystem_name
      FROM ai_repos
      UNION ALL
      SELECT
        artifact_id,
        ecosystem_name
      FROM crypto_repos
    )
    -- Sample of the combined repositories
    SELECT ecosystem_name, COUNT(*) as repo_count
    FROM combined_repos
    GROUP BY ecosystem_name
    """
    combined_repos_df = pd.read_sql(combined_repos_query, pyoso_db_conn)
    combined_repos_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Open dev data scec notebook dat exploration
    """)
    return


@app.cell
def _():
    ## SRE table 
    return


@app.cell
def _(pd, pyoso_db_conn):
    # AI repositories filtering approach from the reference notebook

    sre_events_sql = """
    SELECT *
    FROM int_sre_github_events_by_user
    limit 15 
    """
    sre_events = pd.read_sql(sre_events_sql, pyoso_db_conn)

    # Save to CSV
    sre_events.to_csv('tables_csv/int_sre_github_events_by_user.csv', index=False)

    sre_events
    return


@app.cell
def _(pd, pyoso_db_conn):

    sre_users_sql = """
        SELECT *,
               min(DATE_TRUNC('month', CAST(created_at AS DATE))) AS first_cohort
        FROM int_sre_github_users
        LIMIT 100
    """
    sre_users = pd.read_sql(sre_users_sql, pyoso_db_conn)

    # Save to CSV
    # sre_users.to_csv('tables_csv/int_sre_github_users.csv', index=False)

    sre_users
    return (sre_users,)


@app.cell
def _(pd, pyoso_db_conn):

    int_sre_github_users_sql = """
    SELECT *
    FROM int_sre_github_users
    LIMIT 5
    """
    int_sre_github_users = pd.read_sql(int_sre_github_users_sql, pyoso_db_conn)

    # Save to CSV
    int_sre_github_users.to_csv('tables_csv/int_sre_github_users_sample.csv', index=False)

    int_sre_github_users
    return


@app.cell
def _(pd, pyoso_db_conn):

    int_sre_github_events_by_user_sql = """
    SELECT
    *
    FROM int_sre_github_events_by_user 
    limit 15
    """
    int_sre_github_events_by_user = pd.read_sql(int_sre_github_events_by_user_sql, pyoso_db_conn)

    # Save to CSV
    int_sre_github_events_by_user.to_csv('tables_csv/int_sre_github_events_by_user_sample.csv', index=False)

    int_sre_github_events_by_user
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Working on the best data model for analysising SRE developer retention
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    tables to be used:
    - int_sre_github_events_by_user - for the developer activity info
    - int_opendevdata_ecosystem_repos - to be able to indentify if the contribution was made to ethereum or unknown repo

    for later :
    - int_sre_github_user : can be used to enhance user info
    - int_events_monthly__github- can be used to track if the developer have continued on Ethe or moved on
    """)
    return


@app.cell
def _(pd, pyoso_db_conn):
    sre_users_and_contributions_sql = """
    SELECT
    *
    FROM int_sre_github_events_by_user 
    limit 15
    """
    sre_users_and_contributions = pd.read_sql(sre_users_and_contributions_sql, pyoso_db_conn)
    return (sre_users_and_contributions,)


@app.cell
def _(sre_users_and_contributions):
    sre_users_and_contributions
    return


@app.cell
def _(pd, pyoso_db_conn):
    int_opendevdata_ecosystem_repos_sql = """
    SELECT
    *
    FROM int_opendevdata_ecosystem_repos 
    limit 15
    """
    int_opendevdata_ecosystem_repos_ex = pd.read_sql(int_opendevdata_ecosystem_repos_sql, pyoso_db_conn)
    int_opendevdata_ecosystem_repos_ex
    return


@app.cell
def _():
    return


@app.cell
def _(pd, pyoso_db_conn):
    ### getting what could be the possible value for ethereum ecossitem lable 
    eth_label_values_sql = """
    SELECT
    distinct( ecosystem_name)
    from int_opendevdata_ecosystem_repos 
    where lower(ecosystem_name) like '%ethereum%'
    """
    eth_label_values = pd.read_sql(eth_label_values_sql, pyoso_db_conn)
    eth_label_values

    ## Note here, better filter what ethereum labels should be considered or not. 
    return (eth_label_values,)


@app.cell
def _(eth_label_values):
    eth_label_values.to_parquet('')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### analysing if users have joined the program multiple time
    """)
    return


@app.cell
def _(sre_users):
    sre_users.describe()
    return


@app.cell
def _(sre_users):
    sre_users.columns
    return


@app.cell
def _(sre_users):
    multiple_participations = sre_users.groupby('github_handle').created_at.nunique()
    multiple_participations = multiple_participations.reset_index()
    return (multiple_participations,)


@app.cell
def _(multiple_participations):

    multiple_participations[multiple_participations.created_at == 5]
    return


@app.cell
def _(pd, pyoso_db_conn):

    user_cohort_sql = """


        SELECT 
        github_handle,
        created_at,
        FIRST_VALUE(DATE_TRUNC('month', CAST(created_at AS DATE))) OVER (
            PARTITION BY github_handle 
            ORDER BY CAST(created_at AS DATE)
        ) AS first_cohort
    FROM int_sre_github_users
    WHERE github_handle = 'saraeutsza'

    """
    user_cohort = pd.read_sql(user_cohort_sql, pyoso_db_conn)
    user_cohort
    return


@app.cell
def _():



    return


@app.cell
def _(mo):
    mo.md(r"""
    # Analysis data model
    """)
    return


@app.cell
def _():

    # esp_users_event_classification_sql = """
    #   with ethreum_repos_labels as (
    #   SELECT
    #   distinct( ecosystem_name)
    #   from int_opendevdata_ecosystem_repos 
    #   where ecosystem_name in  ('Ethereum', 'Solana')
    #   ), 

    #   cohort_label as (
    #      SELECT 
    #         github_handle,
    #         created_at,
    #         FIRST_VALUE(DATE_TRUNC('week', CAST(created_at AS DATE))) OVER (
    #             PARTITION BY github_handle 
    #             ORDER BY CAST(created_at AS DATE)
    #         ) AS first_cohort_week_date,
    #         CONCAT(
    #             CAST(YEAR(FIRST_VALUE(DATE_TRUNC('week', CAST(created_at AS DATE))) OVER (
    #                 PARTITION BY github_handle 
    #                 ORDER BY CAST(created_at AS DATE)
    #             )) AS VARCHAR),
    #             '-W',
    #             LPAD(CAST(WEEK(FIRST_VALUE(DATE_TRUNC('week', CAST(created_at AS DATE))) OVER (
    #                 PARTITION BY github_handle 
    #                 ORDER BY CAST(created_at AS DATE)
    #             )) AS VARCHAR), 2, '0')
    #         ) AS cohort_year_week_label
    #     FROM int_sre_github_users
    #   )

    # ,_filter as (
    #   SELECT
    #       events.*, 
    #       repos.ecosystem_name, 
    #       case 
    #         when repos.ecosystem_name = 'Ethereum' then 'Ethereum'
    #         when repos.ecosystem_name = 'Solana' then 'Solana'
    #         else 'Unknown'
    #       end as ecosystem_label,
    #       cohort_label.first_cohort_week_date,
    #       cohort_label.cohort_year_week_label,
    #       CONCAT(
    #           CAST(YEAR(DATE_TRUNC('week', CAST(events.event_time AS DATE))) AS VARCHAR),
    #           '-W',
    #           LPAD(CAST(WEEK(DATE_TRUNC('week', CAST(events.event_time AS DATE))) AS VARCHAR), 2, '0')
    #       ) AS event_year_week_label

    #   FROM int_sre_github_events_by_user as events
    #   left join int_opendevdata_ecosystem_repos as repos
    #   on events.github_repo_id = repos.repo_id
    #   left join cohort_label  
    #   ON events.user_name = cohort_label.github_handle
    #  )

    #  select * from _filter 
    #  where 
    #  -- ecosystem_label = 'Ethereum'
    #  -- and 
    #  first_cohort_week_date is not null
    #   """
    # esp_users_event_classification = pd.read_sql(esp_users_event_classification_sql, pyoso_db_conn)
    # esp_users_event_classification.user_name.nunique() , 
    # esp_users_event_classification.github_user_id.nunique()

    # # esp_users_event_classification.to_parquet('data/esp_users_event_classification.parquet')
    return


@app.cell
def _(esp_users_event_classification):
    def _():
        esp_users_event_classification.to_parquet('data/esp_users_event_classification.parquet', engine='fastparquet')
        return


    _()
    return


@app.cell
def _(esp_users_event_classification):
    esp_users_event_classification.columns
    return


@app.cell
def _(esp_users_event_classification):
    esp_users_event_classification[['user_name', 'github_user_id']].nunique() 
    return


@app.cell
def _(esp_users_event_classification):
    esp_users_event_classification[esp_users_event_classification.ecosystem_name == "Ethereum"].github_user_id.nunique()
    return


@app.cell
def _(esp_users_event_classification):
    _user_cohort = esp_users_event_classification.groupby('first_cohort_week_date')['user_name'].nunique()
    _user_cohort
    return


@app.cell
def _(esp_users_event_classification):
    esp_users_event_classification.user_name.nunique()
    return


@app.cell
def _(esp_users_event_classification):
    esp_users_event_classification.first_cohort_week_date.nunique()
    return


@app.cell
def _(esp_users_event_classification):
    esp_users_event_classification
    return


@app.cell
def _(esp_users_event_classification, pd):
    # Create month and year columns from first_cohort_week_date
    df = esp_users_event_classification.copy()
    df['first_cohort_week_date'] = pd.to_datetime(df['first_cohort_week_date'])
    df['cohort_year_month'] = df['first_cohort_week_date'].dt.to_period('M').astype(str)
    df['cohort_year'] = df['first_cohort_week_date'].dt.year
    return (df,)


@app.cell
def _(df):
    # Unique users by cohort month
    users_by_month = df.groupby('cohort_year_month')['user_name'].nunique().reset_index()
    users_by_month.columns = ['cohort_year_month', 'unique_users']
    users_by_month.unique_users.describe()
    return


@app.cell
def _(df):
    # Unique users by cohort year
    users_by_year = df.groupby('cohort_year')['user_name'].nunique().reset_index()
    users_by_year.columns = ['cohort_year', 'unique_users']
    users_by_year
    return


@app.cell
def _(pd, pyoso_db_conn):

    _sre_users_sql = """


        SELECT 
        github_handle,
        created_at,
        FIRST_VALUE(DATE_TRUNC('week', CAST(created_at AS DATE))) OVER (
            PARTITION BY github_handle 
            ORDER BY CAST(created_at AS DATE)
        ) AS first_cohort
    FROM int_sre_github_users


    """
    sre_users = pd.read_sql(_sre_users_sql, pyoso_db_conn)
    sre_users.github_handle.nunique(), sre_users.first_cohort.isna().sum()
    return (sre_users,)


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
