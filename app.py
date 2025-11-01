# yt_dashboard_complete.py
import streamlit as st
from googleapiclient.discovery import build
import pandas as pd, numpy as np, re
import plotly.express as px
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ── YouTube API setup ─────────────────────────────
API_KEY = "AIzaSyCkZdQjqju6_LiOgajHxpBE_TNefe0yyX8"  # Replace with your actual API key
youtube = build("youtube", "v3", developerKey=API_KEY)

CATEGORY_MAP = {
    "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music", "15": "Pets & Animals",
    "17": "Sports", "18": "Short Movies", "19": "Travel & Events", "20": "Gaming",
    "22": "People & Blogs", "23": "Comedy", "24": "Entertainment", "25": "News & Politics",
    "26": "Howto & Style", "27": "Education", "28": "Science & Technology", "29": "Nonprofits & Activism"
}

def uploads_playlist(channel_id):
    res = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    return res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

def fetch_channel_info(channel_id):
    res = youtube.channels().list(part="snippet,statistics", id=channel_id).execute()
    it = res["items"][0]
    return {
        "name": it["snippet"]["title"],
        "subs": int(it["statistics"].get("subscriberCount", 0)),
        "start": it["snippet"]["publishedAt"][:10],
    }

def fetch_videos(playlist_id, cap=250):
    vids, nxt = [], None
    while len(vids) < cap:
        res = youtube.playlistItems().list(
            part="snippet", playlistId=playlist_id, maxResults=50, pageToken=nxt
        ).execute()
        for it in res["items"]:
            vids.append({
                "title": it["snippet"]["title"],
                "video_id": it["snippet"]["resourceId"]["videoId"],
                "published_at": it["snippet"]["publishedAt"],
            })
            if len(vids) >= cap: break
        nxt = res.get("nextPageToken")
        if not nxt: break
    return vids

def video_stats(ids):
    out = []
    for i in range(0, len(ids), 50):
        res = youtube.videos().list(
            part="statistics,snippet", id=",".join(ids[i:i+50])
        ).execute()
        for it in res["items"]:
            s = it["statistics"]
            out.append({
                "title": it["snippet"]["title"],
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
                "published_at": it["snippet"]["publishedAt"],
                "categoryId": it["snippet"].get("categoryId", "")
            })
    return out

# ── Page config and state ──────────────────────────
st.set_page_config(page_title="YouTube Insights Dashboard", layout="wide")

if "step" not in st.session_state:
    st.session_state.step = "landing"

def goto_channel():
    st.session_state.step = "channel"

# ── Landing Page ───────────────────────────────────
if st.session_state.step == "landing":
    st.markdown(
        """
        <style>
        /* Logo hover & spin animation */
        .logo-container img {
            transition: transform 0.3s ease;
            animation: spinIn 2.5s ease-out;
        }
        .logo-container img:hover {
            transform: scale(1.1);
        }
        @keyframes spinIn {
            from { transform: rotate(-360deg) scale(0.5); opacity: 0; }
            to { transform: rotate(0deg) scale(1); opacity: 1; }
        }

        /* Gradient background fade-in */
        .gradient-bg {
            background: linear-gradient(135deg, #ffffff, #ffe6e6);
            padding: 50px;
            border-radius: 15px;
            animation: fadeIn 1.5s ease-in-out;
        }

        /* Fade-in for content */
        .fade-in {
            animation: fadeIn 1.2s ease-in-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Button styling with pulse */
        .stButton>button {
            background-color: #ff4b4b !important;
            color: white !important;
            font-size: 18px !important;
            padding: 0.75em 2em !important;
            border-radius: 8px !important;
            border: none !important;
            transition: background-color 0.3s ease, transform 0.2s ease;
            animation: pulse 2s infinite;
            box-shadow: 0 0 0 rgba(255, 75, 75, 0.7);
        }
        .stButton>button:hover {
            background-color: #ff3333 !important;
            transform: scale(1.05);
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 75, 75, 0.6); }
            70% { box-shadow: 0 0 0 15px rgba(255, 75, 75, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 75, 75, 0); }
        }
        </style>

        <div class="gradient-bg fade-in" style="text-align: center; margin-top: 50px;">
            <div class="logo-container">
                <img src="https://upload.wikimedia.org/wikipedia/commons/4/42/YouTube_icon_%282013-2017%29.png" width="120">
            </div>
            <h1 style="margin-top: 20px;"><strong>Welcome to YouTube Channel Insights Dashboard</strong></h1>
            <p style="font-size: 18px; max-width: 700px; margin: 20px auto;">
                This application helps YouTube creators analyze their channel performance using real-time data.
                It provides data-driven insights, personalized growth suggestions, category trends, and smart 
                recommendations to boost engagement and reach.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([3, 1, 3])
    with col2:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        if st.button("🚀 Get Started", key="start_btn"):
            st.session_state.step = "channel-info"
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


# ── Dashboard ──────────────────────────────────────
st.title("📈 YouTube Data‑Driven Insights Dashboard")

cid = st.text_input("🔗 Enter YouTube Channel ID")

if cid:
    try:
        with st.spinner("Fetching channel data…"):
            cinfo = fetch_channel_info(cid.strip())
            pid = uploads_playlist(cid.strip())
            vids = fetch_videos(pid)
            ids = [v["video_id"] for v in vids]
            stats = video_stats(ids)
        if not stats:
            st.warning("No public videos found for that channel.")
            st.stop()
        df = pd.DataFrame(stats)
        df["published_at"] = pd.to_datetime(df["published_at"])
        df["hour"] = df["published_at"].dt.hour
        df["engagement_rate"] = (df["likes"] + df["comments"]) / df["views"].replace(0, 1)
        df["category"] = df["categoryId"].map(CATEGORY_MAP)

        st.subheader("📋 Channel Info")
        # Get channel logo from API
        res = youtube.channels().list(part="snippet", id=cid.strip()).execute()
        logo_url = res["items"][0]["snippet"]["thumbnails"]["high"]["url"]

        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(logo_url, width=120)

        with col2:
            st.markdown(f"**Name:** {cinfo['name']}  ")
            st.markdown(f"**Subscribers:** {cinfo['subs']:,}  ")
            st.markdown(f"**Start Date:** {cinfo['start']}")


        st.markdown("---")

        min_d, max_d = df["published_at"].min().date(), df["published_at"].max().date()
        with st.form("date_form"):
            st.subheader("📅 Filter by Date")
            start = st.date_input("Start", min_d)
            end = st.date_input("End", max_d)
            submitted = st.form_submit_button("Submit")

        if submitted:
            fdf = df[(df["published_at"].dt.date >= start) & (df["published_at"].dt.date <= end)]
            st.success(f"Loaded **{len(fdf)}** videos from {start} to {end}")

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Views", f"{fdf['views'].sum():,}")
            col2.metric("Avg Engagement", f"{fdf['engagement_rate'].mean():.2%}")
            if not fdf.empty:
                peak_hour = fdf.groupby("hour")["views"].mean().idxmax()
            else:
                st.warning("No videos in the selected date range.")
                st.stop()
            col3.metric("Best Upload Hour", f"{peak_hour}:00")

            # ── 🚀 Growth Suggestions ────────────────
            st.header("🚀 Growth Suggestions")

            all_words = re.findall(r"\b\w+\b", " ".join(fdf["title"].str.lower()))
            top_kw = [w for w, _ in Counter(all_words).most_common(5)]
            target_er = fdf["engagement_rate"].median() * 1.10

            keyword_sentence = f"Use keywords like **{'**, **'.join(top_kw[:3])}** in your titles to boost discoverability."
            upload_tip = f"Upload during **{peak_hour}:00** — historically your best performing hour."
            engagement_tip = f"Median engagement is **{fdf['engagement_rate'].median():.2%}**. Aim for **{target_er:.2%}** by prompting comments or shares."

            st.markdown(upload_tip)
            st.markdown(keyword_sentence)
            st.markdown(engagement_tip)

            # ── Category Tip ───────────────────────
            st.subheader("🎯 Category Tip")
            cat_df = fdf.groupby("category").agg(
                avg_views=("views", "mean"),
                avg_engagement=("engagement_rate", "mean")
            ).sort_values(by="avg_views", ascending=False)

            best_cat = cat_df.index[0] if not cat_df.empty else None
            if best_cat:
                st.markdown(f"Try publishing more content in the **{best_cat}** category—it’s currently your highest-performing category.")

            # ── 📌 Category Chart ───────────────────
            st.subheader("📊 Performance by All Categories")
            full_cat_df = df.groupby("category").agg(
                avg_views=("views", "mean"),
                avg_engagement=("engagement_rate", "mean")
            ).reset_index()

            fig = px.bar(
                full_cat_df.melt(id_vars="category", value_vars=["avg_views", "avg_engagement"]),
                x="category", y="value", color="variable", barmode="group",
                title="Average Views & Engagement Rate by Category"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            st.subheader("📈 Views Over Time")
            st.plotly_chart(
                px.line(fdf.sort_values("published_at"), x="published_at", y="views"),
                use_container_width=True
            )

            st.subheader("☁️ Title Word Cloud")
            text = " ".join(fdf["title"].dropna().astype(str).tolist()).lower()
            wc = WordCloud(width=800, height=400, background_color="white", colormap="plasma").generate(text)

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig)
            plt.close(fig)

            st.download_button(
                "📥 Download CSV",
                data=fdf.to_csv(index=False),
                file_name="youtube_stats.csv",
                mime="text/csv",
            )
    except Exception as e:
        st.error("❌ Invalid Channel ID. Please check and try again.")
else:
    st.info("Paste a Channel ID like `UC_x5XG1OV2P6uZZ5FSM9Ttw` to begin.")
