import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ---------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------
st.set_page_config(
    page_title="Movie Dashboard 🎬",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("mymoviedb.xlsx", engine="openpyxl")
    # Normalize column names and fix Genre column if it has trailing \r or different name
    df.columns = df.columns.str.strip()
    if "Genre" not in df.columns:
        # find a column that contains the word 'Genre' (handles 'Genre\r')
        genre_candidates = [c for c in df.columns if "Genre" in c]
        if genre_candidates:
            df = df.rename(columns={genre_candidates[0]: "Genre"})
        else:
            df["Genre"] = ""
    # Clean Genre and Release_Date
    df["Genre"] = df["Genre"].astype(str).str.replace("\r", "", regex=True).str.strip()
    df["Release_Date"] = pd.to_numeric(df["Release_Date"], errors="coerce")
    # Drop rows missing essential info
    df = df.dropna(subset=["Release_Date", "Title"])
    # Ensure Vote_Average, Popularity, Vote_Count exist and correct types (fill missing safely)
    for col, dtype in [("Vote_Average", "float"), ("Popularity", "float"), ("Vote_Count", "Int64")]:
        if col not in df.columns:
            if dtype == "Int64":
                df[col] = pd.Series([0]*len(df), dtype="Int64")
            else:
                df[col] = 0.0
        else:
            if dtype == "Int64":
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    # Convert Release_Date to int for nicer display (year)
    df["Release_Date"] = df["Release_Date"].astype(int)
    return df

df = load_data()

# ---------------------------------------------------
# SIDEBAR - FILTERS & THEME
# ---------------------------------------------------
st.sidebar.title("🎯 Filters & Settings")

# Theme Toggle
theme_mode = st.sidebar.radio("Choose Theme:", ["Dark", "Light"], index=0)

# Theme Colors
if theme_mode == "Dark":
    bg_color = "#0E1117"
    text_color = "#F2C94C"
    chart_color = "#F2C94C"
    st.markdown(
        """
        <style>
        body {background-color: #0E1117; color: #F2C94C;}
        .stMetric {background-color: rgba(242, 201, 76, 0.06); border-radius: 10px; padding: 10px;}
        .stAppViewContainer { background-color: #0E1117; }
        </style>
        """,
        unsafe_allow_html=True
    )
else:
    bg_color = "#FFFFFF"
    text_color = "#111827"
    chart_color = "#E6B800"
    st.markdown(
        """
        <style>
        body {background-color: #FFFFFF; color: #111827;}
        .stMetric {background-color: rgba(230, 184, 0, 0.06); border-radius: 10px; padding: 10px;}
        .stAppViewContainer { background-color: #FFFFFF; }
        </style>
        """,
        unsafe_allow_html=True
    )

# Year Filter
years = sorted(df["Release_Date"].dropna().unique())
selected_years = st.sidebar.multiselect("Select Release Year(s):", years, default=years)

# Genre Filter (derive unique genres robustly)
genre_series = df["Genre"].dropna().astype(str)
all_genres = sorted(
    set(
        g.strip()
        for cell in genre_series
        for g in (cell.split(",") if cell else [])
        if g.strip()
    )
)
selected_genres = st.sidebar.multiselect("Select Genre(s):", all_genres, default=[])

# Apply Filters
filtered_df = df[df["Release_Date"].isin(selected_years)]
if selected_genres:
    # Keep rows where any selected genre appears in the Genre string
    filtered_df = filtered_df[
        filtered_df["Genre"].apply(lambda x: any(sel in [g.strip() for g in x.split(",")] for sel in selected_genres))
    ]

# ---------------------------------------------------
# KPIs
# ---------------------------------------------------
st.title("🎬 Movie Dashboard")
total_movies = len(filtered_df)
# handle empty filtered_df gracefully
if total_movies > 0:
    avg_rating = round(filtered_df["Vote_Average"].mean(), 2)
    avg_popularity = round(filtered_df["Popularity"].mean(), 2)
else:
    avg_rating = 0.0
    avg_popularity = 0.0

col1, col2, col3 = st.columns(3)
col1.metric("🎞️ Total Movies", f"{total_movies:,}")
col2.metric("⭐ Average Rating", avg_rating)
col3.metric("🔥 Avg Popularity", avg_popularity)

st.markdown("---")

# ---------------------------------------------------
# CHARTS
# ---------------------------------------------------
st.subheader("📊 Visual Insights")

tab1, tab2, tab3, tab4 = st.tabs([
    "Rating by Year", "Top 10 Popular Movies", "Genre Distribution", "Popularity vs Rating"
])

# Choose a valid continuous colorscale name supported by Plotly
valid_continuous_scale = "sunset"  # valid plotly colorscale

# 1️⃣ Rating by Year
with tab1:
    if total_movies > 0:
        rating_year = (
            filtered_df.groupby("Release_Date", as_index=False)["Vote_Average"]
            .mean()
            .sort_values("Release_Date")
        )
        fig1 = px.line(
            rating_year,
            x="Release_Date",
            y="Vote_Average",
            markers=True,
            title="Average Rating by Year",
            color_discrete_sequence=[chart_color],
        )
        fig1.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=text_color)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

# 2️⃣ Top 10 Movies by Popularity
with tab2:
    if total_movies > 0:
        top_movies = filtered_df.nlargest(10, "Popularity")[["Title", "Popularity", "Vote_Average"]]
        fig2 = px.bar(
            top_movies,
            x="Popularity",
            y="Title",
            orientation="h",
            title="Top 10 Movies by Popularity",
            color="Vote_Average",
            color_continuous_scale=valid_continuous_scale,
            labels={"Vote_Average": "Avg Rating"}
        )
        fig2.update_yaxes(categoryorder="total ascending")
        fig2.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=text_color)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

# 3️⃣ Genre Distribution
with tab3:
    if total_movies > 0:
        genre_split = []
        for genres in filtered_df["Genre"].dropna():
            if genres:
                genre_split.extend([g.strip() for g in genres.split(",") if g.strip()])
        if genre_split:
            genre_df = pd.Series(genre_split).value_counts().reset_index()
            genre_df.columns = ["Genre", "Count"]
            fig3 = px.pie(
                genre_df,
                values="Count",
                names="Genre",
                title="Genre Distribution",
                color_discrete_sequence=px.colors.sequential.Agsunset
            )
            fig3.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=text_color)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No genre information available for the selected filters.")
    else:
        st.info("No data available for the selected filters.")

# 4️⃣ Popularity vs Rating (fixed size handling)
with tab4:
    if total_movies > 0:
        # Convert Vote_Count to a plain numeric numpy array for Plotly's size argument
        # Fill missing with 0, convert to int, and use a small scaling for marker sizes.
        size_series = filtered_df.get("Vote_Count", pd.Series([0]*len(filtered_df)))
        # Ensure it's numeric (fallback to zeros)
        size_numeric = pd.to_numeric(size_series, errors="coerce").fillna(0).astype(int)
        size_vals = size_numeric.to_numpy()

        # Optionally scale sizes for better visualization (linear scaling)
        # small constant to avoid zero-size markers
        min_size = 5
        max_display_size = 40
        if size_vals.max() > 0:
            # Normalize to [min_size, max_display_size]
            norm = (size_vals - size_vals.min()) / (size_vals.max() - size_vals.min())
            plot_sizes = (norm * (max_display_size - min_size) + min_size)
        else:
            plot_sizes = np.full_like(size_vals, fill_value=min_size, dtype=float)

        fig4 = px.scatter(
            filtered_df,
            x="Popularity",
            y="Vote_Average",
            size=plot_sizes,             # pass the scaled numeric array
            color="Release_Date",
            hover_name="Title",
            title="Popularity vs Rating",
            color_continuous_scale=valid_continuous_scale,
        )
        fig4.update_traces(marker=dict(sizemode="diameter"))
        fig4.update_layout(plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=text_color)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

# ---------------------------------------------------
# DOWNLOAD FILTERED DATA
# ---------------------------------------------------
st.markdown("---")
if total_movies > 0:
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name="filtered_movies.csv",
        mime="text/csv",
    )
else:
    st.write("No data to download for the current filters.")

# ---------------------------------------------------
# FOOTER
# ---------------------------------------------------
st.markdown(
    f"<p style='text-align:center; color:{text_color};'>📊 Dashboard created by <b>Aditi Rajesh Nair</b> | Powered by Streamlit & Plotly</p>",
    unsafe_allow_html=True,
)
