import base64
from io import BytesIO
from typing import List

import matplotlib.pyplot as plt
import pandas as pd
import requests
from wordcloud import STOPWORDS, WordCloud
from dagster import MetadataValue, OpExecutionContext, asset
from dagster_snowflake import snowflake_io_manager

snowflake_creds = {
    "account": "https://rb83340.europe-west4.gcp.snowflakecomputing.com/",
    "user": "ranjuramesh",
    "password": "NpI9UcA8Cn#9",
    "warehouse": "compute_wh",
    "database": "rawdata_db",
    "schema": "testing",
}

snowflake_io_manager = snowflake_io_manager.configured(snowflake_creds)

@asset(
    group_name="hackernews",
    compute_kind="HackerNews API",
    key_prefix=["hackernews"],
    io_manager_key="snowflake_io_manager",
)
def hackernews_topstory_ids() -> pd.DataFrame:
    """
    Get up to 500 top stories from the HackerNews topstories endpoint.
    API Docs: https://github.com/HackerNews/API#new-top-and-best-stories
    """
    newstories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    top_500_newstories = requests.get(newstories_url).json()
    return pd.DataFrame(top_500_newstories, columns=["item_ids"])

@asset(
    group_name="hackernews",
    compute_kind="HackerNews API",
    key_prefix=["hackernews"],
    io_manager_key="snowflake_io_manager",
)
def hackernews_topstories(
    context: OpExecutionContext, hackernews_topstory_ids: pd.DataFrame
) -> pd.DataFrame:
    """
    Get items based on story ids from the HackerNews items endpoint. It may take 1-2 minutes to fetch all 500 items.
    API Docs: https://github.com/HackerNews/API#items
    """
    results = []
    for item_id in hackernews_topstory_ids["item_ids"]:
        item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json").json()
        results.append(item)
        if len(results) % 20 == 0:
            context.log.info(f"Got {len(results)} items so far.")

    df = pd.DataFrame(results)

    context.add_output_metadata(
        {
            "num_records": len(df),
            "preview": MetadataValue.md(df.head().to_markdown()),
        }
    )

    return df

@asset(group_name="hackernews", compute_kind="Plot")
def hackernews_topstories_word_cloud(
    context: OpExecutionContext, hackernews_topstories: pd.DataFrame
) -> None:
    """
    Exploratory analysis: Generate a word cloud from the current top 500 HackerNews top stories.
    Embed the plot into a Markdown metadata for quick view.
    Read more about how to create word clouds in http://amueller.github.io/word_cloud/.
    """
    stopwords = set(STOPWORDS)
    stopwords.update(["Ask", "Show", "HN"])

    titles_text = " ".join([str(item) for item in hackernews_topstories["title"]])
    titles_cloud = WordCloud(stopwords=stopwords, background_color="white").generate(titles_text)

    plt.figure(figsize=(8, 8), facecolor=None)
    plt.imshow(titles_cloud, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    image_data = base64.b64encode(buffer.getvalue())
    md_content = f"![img](data:image/png;base64,{image_data.decode()})"

    context.add_output_metadata({"plot": MetadataValue.md(md_content)})
