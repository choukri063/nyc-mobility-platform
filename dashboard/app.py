import os

import pandas as pd
import plotly.express as px
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------------------------
# Configuration de la page
# Le style fonctionne en thème clair comme en thème sombre : aucune couleur de
# fond ou de texte n'est imposée, tout hérite du thème Streamlit actif.
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="NYC Mobility Dashboard",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

ACCENT = "#F2A900"
BOROUGH_COLORS = {
    "Manhattan": "#F2A900",
    "Queens": "#2F80ED",
    "Brooklyn": "#27AE60",
    "Bronx": "#EB5757",
    "Staten Island": "#9B51E0",
    "EWR": "#828282",
}
DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_LABELS = {
    "Mon": "Lundi", "Tue": "Mardi", "Wed": "Mercredi", "Thu": "Jeudi",
    "Fri": "Vendredi", "Sat": "Samedi", "Sun": "Dimanche",
}

st.markdown(
    """
    <style>
    .block-container {padding-top: 2.5rem; padding-bottom: 2rem; max-width: 1400px;}
    #MainMenu, footer {visibility: hidden;}
    .stDeployButton, [data-testid="stAppDeployButton"] {display: none;}
    [data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-left: 5px solid #F2A900;
        padding: 16px 18px;
        border-radius: 10px;
    }
    [data-testid="stMetricLabel"] p {font-size: 0.85rem; opacity: 0.75;}
    [data-testid="stMetricValue"] {font-size: 1.8rem; font-weight: 700;}
    h1, h2, h3 {letter-spacing: -0.01em;}
    .subtitle {opacity: 0.7; margin-top: -0.6rem; margin-bottom: 1.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Connexion et requêtes
# ----------------------------------------------------------------------------
@st.cache_resource
def init_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role="ACCOUNTADMIN",
        warehouse="NYC_WH",
        database="NYC_MOBILITY",
        schema="DBT_DEV",
    )


conn = init_connection()


@st.cache_data(ttl=600, show_spinner="Chargement des données...")
def run_query(query: str) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(query)
    df = cur.fetch_pandas_all()
    cur.close()
    df.columns = [c.lower() for c in df.columns]
    return df


def load_demand() -> pd.DataFrame:
    df = run_query(
        """
        SELECT month, day_of_week, hour_of_day, pickup_borough,
               nb_trips, avg_distance_mi, avg_duration_min, avg_total_amount
        FROM MART_DEMAND_BY_HOUR_BOROUGH
        """
    )
    df["month"] = pd.to_datetime(df["month"]).dt.strftime("%Y-%m")
    for col in ["hour_of_day", "nb_trips", "avg_distance_mi", "avg_duration_min", "avg_total_amount"]:
        df[col] = pd.to_numeric(df[col])
    # Les moyennes sont pondérées par le nombre de courses pour les agrégations
    df["revenue"] = df["avg_total_amount"] * df["nb_trips"]
    df["dist_x_trips"] = df["avg_distance_mi"] * df["nb_trips"]
    df["dur_x_trips"] = df["avg_duration_min"] * df["nb_trips"]
    return df


def load_zones() -> pd.DataFrame:
    df = run_query(
        """
        SELECT pickup_borough, pickup_zone, nb_trips, total_revenue, avg_total_amount
        FROM MART_TOP_PICKUP_ZONES
        """
    )
    for col in ["nb_trips", "total_revenue", "avg_total_amount"]:
        df[col] = pd.to_numeric(df[col])
    return df


def load_tips() -> pd.DataFrame:
    df = run_query(
        """
        SELECT payment_method, nb_trips, avg_tip, tip_pct_of_fare
        FROM MART_TIPS_BY_PAYMENT
        """
    )
    for col in ["nb_trips", "avg_tip", "tip_pct_of_fare"]:
        df[col] = pd.to_numeric(df[col])
    return df


# ----------------------------------------------------------------------------
# Helpers d'affichage
# ----------------------------------------------------------------------------
def fmt_compact(n: float) -> str:
    if n >= 1e9:
        return f"{n / 1e9:.2f} Md"
    if n >= 1e6:
        return f"{n / 1e6:.2f} M"
    if n >= 1e3:
        return f"{n / 1e3:.0f} k"
    return f"{n:.0f}"


def style(fig, height: int = 400):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="",
        title_font_size=16,
        uniformtext_minsize=11,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128, 128, 128, 0.25)")
    return fig


def show(fig):
    st.plotly_chart(fig)


# ----------------------------------------------------------------------------
# Chargement des données
# ----------------------------------------------------------------------------
demand = load_demand()
zones = load_zones()
tips = load_tips()

# ----------------------------------------------------------------------------
# Barre latérale : filtres
# ----------------------------------------------------------------------------
st.sidebar.title("🚕 Filtres")
st.sidebar.caption("S'appliquent à la demande et aux zones. Les pourboires ne sont pas filtrables.")

all_boroughs = sorted(demand["pickup_borough"].unique())
all_months = sorted(demand["month"].unique())

sel_boroughs = st.sidebar.multiselect("Quartiers de départ", all_boroughs, default=all_boroughs)
sel_months = st.sidebar.multiselect("Mois", all_months, default=all_months)

f = demand[demand["pickup_borough"].isin(sel_boroughs) & demand["month"].isin(sel_months)]

st.sidebar.markdown("---")
st.sidebar.caption("Données : NYC TLC, taxis jaunes, janvier à mars 2024")
st.sidebar.caption("Pipeline : Snowflake, dbt, Streamlit")

# ----------------------------------------------------------------------------
# En-tête
# ----------------------------------------------------------------------------
st.title("🚕 NYC Taxi Mobility")
st.markdown(
    '<p class="subtitle">Analyse de la demande, des revenus et des pourboires des taxis jaunes de New York</p>',
    unsafe_allow_html=True,
)

if f.empty:
    st.warning("Aucune donnée pour cette sélection. Élargis les filtres dans la barre latérale.")
    st.stop()

# ----------------------------------------------------------------------------
# KPI
# ----------------------------------------------------------------------------
total_trips = f["nb_trips"].sum()
total_revenue = f["revenue"].sum()
avg_fare = total_revenue / total_trips
avg_dist = f["dist_x_trips"].sum() / total_trips
avg_dur = f["dur_x_trips"].sum() / total_trips
peak_hour = int(f.groupby("hour_of_day")["nb_trips"].sum().idxmax())

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Courses", fmt_compact(total_trips))
k2.metric("Revenu total", f"{fmt_compact(total_revenue)} $")
k3.metric("Panier moyen", f"{avg_fare:.2f} $")
k4.metric("Distance / durée", f"{avg_dist:.1f} mi / {avg_dur:.0f} min")
k5.metric("Heure de pointe", f"{peak_hour:02d} h")

st.markdown("")

# ----------------------------------------------------------------------------
# Onglets
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Vue d'ensemble", "🕒 Temporel", "📍 Zones", "💸 Pourboires"]
)

# --- Vue d'ensemble ---------------------------------------------------------
with tab1:
    mode = st.radio(
        "Affichage de la courbe",
        ["Volume de courses", "Rythme comparé (indice, 100 = moyenne du quartier)"],
        horizontal=True,
    )
    hourly = f.groupby(["hour_of_day", "pickup_borough"], as_index=False)["nb_trips"].sum()
    if mode.startswith("Volume"):
        y_col, y_label = "nb_trips", "Courses"
    else:
        hourly["index"] = (
            hourly["nb_trips"]
            / hourly.groupby("pickup_borough")["nb_trips"].transform("mean")
            * 100
        )
        y_col, y_label = "index", "Indice"

    fig = px.line(
        hourly,
        x="hour_of_day",
        y=y_col,
        color="pickup_borough",
        color_discrete_map=BOROUGH_COLORS,
        markers=True,
        title="Demande par heure de la journée",
        labels={"hour_of_day": "Heure", y_col: y_label, "pickup_borough": "Quartier"},
    )
    fig.update_xaxes(dtick=2)
    show(style(fig, 420))
    if mode.startswith("Volume"):
        st.caption(
            "Manhattan concentre l'essentiel des courses : utilise l'indice pour comparer "
            "le rythme des autres quartiers."
        )

    c1, c2 = st.columns(2)
    by_borough = f.groupby("pickup_borough", as_index=False).agg(
        nb_trips=("nb_trips", "sum"), revenue=("revenue", "sum")
    )
    by_borough["avg_fare"] = by_borough["revenue"] / by_borough["nb_trips"]

    with c1:
        fig = px.pie(
            by_borough,
            names="pickup_borough",
            values="nb_trips",
            hole=0.55,
            color="pickup_borough",
            color_discrete_map=BOROUGH_COLORS,
            title="Part des courses par quartier",
        )
        fig.update_traces(textinfo="percent", textposition="inside")
        show(style(fig, 380))

    with c2:
        fig = px.bar(
            by_borough.sort_values("avg_fare", ascending=False),
            x="pickup_borough",
            y="avg_fare",
            color="pickup_borough",
            color_discrete_map=BOROUGH_COLORS,
            text_auto=".0f",
            title="Panier moyen par quartier ($)",
            labels={"pickup_borough": "", "avg_fare": "$ par course"},
        )
        fig.update_layout(showlegend=False)
        show(style(fig, 380))
        st.caption(
            "Queens et EWR ont les paniers les plus élevés à cause des aéroports "
            "(JFK, LaGuardia, Newark)."
        )

# --- Temporel ---------------------------------------------------------------
with tab2:
    pivot = (
        f.groupby(["day_of_week", "hour_of_day"])["nb_trips"].sum().unstack(fill_value=0)
    )
    pivot = pivot.reindex([d for d in DAY_ORDER if d in pivot.index])
    pivot.index = [DAY_LABELS[d] for d in pivot.index]

    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="YlOrBr",
        labels=dict(x="Heure", y="", color="Courses"),
        title="Intensité de la demande : jour de la semaine et heure",
    )
    fig.update_xaxes(dtick=2)
    show(style(fig, 420))

    monthly = f.groupby("month", as_index=False).agg(
        nb_trips=("nb_trips", "sum"), revenue=("revenue", "sum")
    )
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            monthly, x="month", y="nb_trips", text_auto=".3s",
            title="Courses par mois",
            labels={"month": "", "nb_trips": "Courses"},
            color_discrete_sequence=[ACCENT],
        )
        show(style(fig, 340))
    with c2:
        fig = px.bar(
            monthly, x="month", y="revenue", text_auto=".3s",
            title="Revenu estimé par mois ($)",
            labels={"month": "", "revenue": "Revenu"},
            color_discrete_sequence=["#2F80ED"],
        )
        show(style(fig, 340))

# --- Zones ------------------------------------------------------------------
with tab3:
    st.caption("Cette vue suit le filtre Quartiers. Elle couvre tous les mois chargés.")
    z = zones[zones["pickup_borough"].isin(sel_boroughs)]

    c1, c2 = st.columns([3, 1])
    metric_label = c2.radio("Classer par", ["Courses", "Revenu"], horizontal=False)
    top_n = c2.slider("Nombre de zones", 5, 25, 10)
    metric_col = "nb_trips" if metric_label == "Courses" else "total_revenue"

    top = z.sort_values(metric_col, ascending=False).head(top_n).sort_values(metric_col)
    with c1:
        fig = px.bar(
            top,
            x=metric_col,
            y="pickup_zone",
            orientation="h",
            color="pickup_borough",
            color_discrete_map=BOROUGH_COLORS,
            text_auto=".3s",
            title=f"Top {top_n} des zones de départ par {metric_label.lower()}",
            labels={metric_col: metric_label, "pickup_zone": "", "pickup_borough": "Quartier"},
        )
        show(style(fig, max(380, top_n * 32)))

    st.subheader("Détail des zones")
    detail = z.sort_values(metric_col, ascending=False).head(top_n).rename(
        columns={
            "pickup_borough": "Quartier",
            "pickup_zone": "Zone",
            "nb_trips": "Courses",
            "total_revenue": "Revenu ($)",
            "avg_total_amount": "Panier moyen ($)",
        }
    )
    st.dataframe(
        detail,
        hide_index=True,
        column_config={
            "Courses": st.column_config.NumberColumn(format="%d"),
            "Revenu ($)": st.column_config.NumberColumn(format="%d"),
            "Panier moyen ($)": st.column_config.NumberColumn(format="%.2f"),
        },
    )

# --- Pourboires -------------------------------------------------------------
with tab4:
    card = tips[tips["payment_method"] == "Carte"]
    if not card.empty:
        card = card.iloc[0]
        share_card = card["nb_trips"] / tips["nb_trips"].sum() * 100
        t1, t2, t3 = st.columns(3)
        t1.metric("Pourboire moyen (carte)", f"{card['avg_tip']:.2f} $")
        t2.metric("Pourboire / tarif (carte)", f"{card['tip_pct_of_fare']:.1f} %")
        t3.metric("Courses payées par carte", f"{share_card:.0f} %")

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.pie(
            tips,
            names="payment_method",
            values="nb_trips",
            hole=0.55,
            title="Répartition des courses par mode de paiement",
            color_discrete_sequence=[ACCENT, "#2F80ED", "#27AE60", "#EB5757", "#9B51E0"],
        )
        fig.update_traces(textinfo="percent", textposition="inside")
        show(style(fig, 380))
    with c2:
        comparable = tips[tips["payment_method"] != "Especes"]
        fig = px.bar(
            comparable,
            x="payment_method",
            y="tip_pct_of_fare",
            text_auto=".1f",
            title="Pourboire en % du tarif (hors espèces)",
            labels={"payment_method": "", "tip_pct_of_fare": "% du tarif"},
            color_discrete_sequence=[ACCENT],
        )
        show(style(fig, 380))

    st.info(
        "Les pourboires en espèces ne sont pas enregistrés par le taximètre : ils valent 0 dans les "
        "données et sont donc exclus de la comparaison. Seuls les paiements par carte sont fiables."
    )

st.markdown("---")
st.caption("NYC TLC Trip Record Data | Snowflake, dbt, Streamlit")