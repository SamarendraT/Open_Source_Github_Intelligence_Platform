def scd2_upsert_dim_repo(incoming, catalog: str) -> None:
    incoming.createOrReplaceTempView("repo_incoming")
    incoming.sparkSession.sql(
        f"""
        MERGE INTO {catalog}.gold.dim_repo AS t
        USING (
            SELECT i.repo_id AS merge_key, i.* FROM repo_incoming i
            UNION ALL
            SELECT NULL AS merge_key, i.*
            FROM repo_incoming i
            JOIN {catalog}.gold.dim_repo c
                ON c.repo_id = i.repo_id AND c.is_current = true
            WHERE c.repo_name <> i.repo_name
        ) s
        ON t.repo_id = s.merge_key AND t.is_current = true
        WHEN MATCHED AND t.repo_name <> s.repo_name THEN
           UPDATE SET t.is_current = false, t.effective_to = s.observed_at
        WHEN MATCHED AND t.repo_name = s.repo_name
                AND s.language IS NOT NULL AND NOT (s.language <=> t.language) THEN
            UPDATE SET t.language = s.language
        WHEN NOT MATCHED THEN
            INSERT (repo_id, repo_name, owner, language, effective_from, effective_to, is_current)
            VALUES (s.repo_id, s.repo_name, s.owner, s.language,
            CASE WHEN s.merge_key IS NULL THEN s.observed_at ELSE s.first_seen_ts END,
            NULL, true)
        """
    )


def overwrite_date_range(df, table: str, start_date: str, end_date: str) -> None:
    target_cols = [f.name for f in df.sparkSession.table(table).schema.fields]
    (
        df.select(*target_cols)
        .write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"event_date >= '{start_date}' AND event_date <= '{end_date}'")
        .saveAsTable(table)
    )
