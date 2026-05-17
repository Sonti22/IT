"""RSS feeds to monitor. Add/remove as needed."""

SOURCES = [
    {
        "name": "HackerNews Top",
        "url": "https://hnrss.org/frontpage",
        "tag": "#hn",
        "emoji": "🟧",
    },
    {
        "name": "Habr Top",
        "url": "https://habr.com/ru/rss/all/top10/",
        "tag": "#habr",
        "emoji": "📰",
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "tag": "#tech",
        "emoji": "💼",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "tag": "#ai",
        "emoji": "🤖",
    },
    {
        "name": "ArXiv cs.AI",
        "url": "http://export.arxiv.org/rss/cs.AI",
        "tag": "#research",
        "emoji": "🧪",
    },
    {
        "name": "HuggingFace Papers",
        "url": "https://jamesg.blog/hf-papers.xml",
        "tag": "#ai #papers",
        "emoji": "🤗",
    },
    {
        "name": "r/MachineLearning",
        "url": "https://www.reddit.com/r/MachineLearning/.rss",
        "tag": "#ml",
        "emoji": "🧠",
    },
    {
        "name": "r/programming",
        "url": "https://www.reddit.com/r/programming/.rss",
        "tag": "#dev",
        "emoji": "💻",
    },
]

MAX_POSTS_PER_RUN = 3
MAX_STATE_HISTORY = 1000
