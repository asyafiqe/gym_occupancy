# -*- coding: utf-8 -*-
"""
Created on Wed Apr 12 19:02:18 2023

@author: Abdullah Syafiq
"""
import datetime
import gspread
import numpy as np
import plotly.express as px
import streamlit as st
import pandas as pd

# %%
# config
MAX_SESSION_DUR = 180
MAX_CAPACITY = 2
TIMEZONE_OFFSET = +9.0  # 'Tokyo Standard Time' (UTC+09:00)
CACHE_TTL = 300
# %%
st.set_page_config(
    page_title="NIG Training Gym Occupancy",
    page_icon=":muscle:",
    layout="centered",
    initial_sidebar_state="auto",
)
# %%
GSHEETS_URL = st.secrets["gsheets_url"]
CRED_JSON = st.secrets["gcp_service_account"]


def convert_datetime(input_df, cols):
    """Batch convert df columns dtypes to datetime"""
    for x in cols:
        input_df[x] = pd.to_datetime(input_df[x])
    return input_df


def datetime_now(input_timezone_offset):
    """Get current datetime corrected to timezone, remove timezone info"""
    now_utc = datetime.datetime.utcnow()
    now_tz = now_utc + datetime.timedelta(hours=input_timezone_offset)
    return now_tz


@st.cache_resource(ttl=CACHE_TTL, show_spinner="Fetching data from API...")
def load_worksheet(input_gsheets_url, _input_json):
    """Fetch gsheet via gspread"""
    # authentication
    gc = gspread.service_account(_input_json)

    # import google sheet
    sh = gc.open_by_url(input_gsheets_url)

    worksheet_active_loaded = sh.worksheet("active")
    worksheet_log_loaded = sh.worksheet("log")

    return worksheet_active_loaded, worksheet_log_loaded


# %%
worksheet_active, worksheet_log = load_worksheet(GSHEETS_URL, CRED_JSON)


@st.cache_data(ttl=CACHE_TTL, show_spinner="Processing data...")
def load_df(_worksheet_active, _worksheet_log):
    """Process imported gsheet's worksheet into workable dataframe"""
    df_loaded = pd.DataFrame(worksheet_active.get_all_records())
    # check for empty df
    if len(df_loaded.index) == 0:
        df_loaded = pd.DataFrame(
            columns=["name", "lab", "start", "finish_estimation", "duration_estimation"]
        )

    log_df_loaded = pd.DataFrame(worksheet_log.get_all_records())
    # check for empty log_df
    if len(log_df_loaded.index) == 0:
        log_df_loaded = pd.DataFrame(
            columns=[
                "name",
                "lab",
                "start",
                "finish_estimation",
                "duration_estimation",
                "finish_actual",
                "duration_actual",
            ]
        )

    cols = ["start", "finish_estimation"]
    # parse date
    df_loaded = convert_datetime(df_loaded, cols)
    log_df_loaded = convert_datetime(log_df_loaded, cols)

    return df_loaded, log_df_loaded


df, log_df = load_df(worksheet_active, worksheet_log)
# %%
# check if old entry hasn't been logged out
current_time = datetime_now(TIMEZONE_OFFSET)
df = df.assign(delta=current_time - df["start"])
old_entries = df.index[df["delta"] / np.timedelta64(1, "m") > MAX_SESSION_DUR].values

# remove old entry
if len(old_entries) > 0:
    for entry in old_entries:
        worksheet_active.delete_rows(int(entry) + 2)

df = df.drop(columns=["delta"])
# %%
st.title(":muscle: NIG Training Gym Occupancy  :man-lifting-weights:")

# %%
tab1, tab2, tab3, tab4 = st.tabs(["Home", "Login", "Logout", "Data (to be hidden)"])

with tab1:
    # show number of people currently on the room
    st.write("**Occupancy**: ", len(df.index), "/", MAX_CAPACITY)

    if len(df.index) > MAX_CAPACITY:
        st.write("The gym is currently exceeding maximum capacity :warning:")
    elif len(df.index) == MAX_CAPACITY:
        st.write("The gym is currently at full capacity	")
    elif len(df.index) == 0:
        st.write("It seems like nobody is in the gym :eyes:")
    else:
        st.write("It must be fun to do some workout:sparkles:")

    st.divider()
    st.header("Who's in the gym? :thinking_face:")
    if len(df.index) != 0:
        fig = px.timeline(
            df,
            x_start="start",
            x_end="finish_estimation",
            y="name",
            color="name",
            template="plotly",
        )
        # otherwise names are listed from the bottom up
        fig.update_yaxes(
            autorange="reversed",
            # visible=False,
            # showticklabels=False,
            # tickfont_family='Arial Black',
            tickfont_size=16,
            # tickfont_color='black',
        )
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="",
        )
        fig.update(
            layout_showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write(
            "![confused_travolta](https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMzBjNzk0MDRkMjFiOTQxZTVlNmVlNzE1ZmY4Y2JhNjU0Y2RhODVjMyZjdD1n/3nZRJP0BBMP28/giphy.gif)"
        )

    if st.button("Refresh", key="refresh_home_btn"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.experimental_rerun()
# %%
with tab2:
    st.header("Login")
    st.write("I'm ready to squeeze out my sudoriferous glands")

    # login input
    st.subheader("Name")
    name_input = st.text_input(
        "Name", label_visibility="collapsed", placeholder="Anonymous"
    )
    if name_input in df["name"].values:
        st.write("Are you a twin?:thinking_face: Pick another name.	:nerd_face:")

    st.subheader("Lab")
    lab_input = st.text_input(
        "Lab", label_visibility="collapsed", placeholder="Hada Labo"
    )

    st.write("")
    st.subheader("Estimated duration of usage")
    st.write("I will be here for around...(minutes)")
    dur_input = st.number_input(
        "Duration", min_value=10, step=10, value=30, label_visibility="collapsed"
    )

    # calculate finish time
    start_time = datetime_now(TIMEZONE_OFFSET)
    dur = datetime.timedelta(minutes=dur_input)
    finish_time = start_time + dur

    st.write("I might finish at around", f'**{finish_time.strftime("%I:%M %p")}**')
    st.write("")

    # set nested button
    # declare initial state
    if "login" not in st.session_state:
        st.session_state["login"] = False

    # action on submit click
    if st.button("Login"):
        # toggle login button session state
        st.session_state["login"] = not st.session_state["login"]
        # check for blank input
        if len(name_input) == 0:
            st.error("Please write your name", icon="🚨")
        elif len(lab_input) == 0:
            st.error("Please write your lab", icon="🚨")
        # check if input name is already exist
        elif name_input in df["name"].values:
            st.error(
                "Are you a twin?:thinking_face: Pick another name.	:nerd_face:",
                icon="🚨",
            )
        else:
            input_row = [
                name_input,
                lab_input,
                str(start_time),
                str(finish_time),
                int(dur_input),
            ]
            # push to gsheet
            worksheet_active.append_row(input_row, table_range="A1:E1")
            worksheet_log.append_row(input_row, table_range="A1:E1")
            # notification
            st.success("Logged in, enjoy your workout!", icon="✅")
            st.write("")
            st.write("")
    # nested refresh button
    if st.session_state["login"]:
        if st.button("Refresh", key="refresh_login_btn"):
            st.session_state["login"] = False
            st.cache_data.clear()
            st.cache_resource.clear()
            st.experimental_rerun()
# %%
with tab3:
    st.header("Logout")
    st.write("My glycogen stores has been depleted")
    # name and duration input box
    name_logout = st.selectbox("Name", options=df["name"].unique())

    if len(df.index) > 0:
        # select row
        input_log_df = df.loc[df["name"] == name_logout]

        # get current time
        finish_actual = datetime_now(TIMEZONE_OFFSET)

        # calculate actual duration
        start_time = pd.Timestamp(input_log_df["start"].values[0]).to_pydatetime()
        duration_actual = int((finish_actual - start_time).total_seconds() / 60)

        # show duration
        st.write("You have been here for", f"**{duration_actual}**", "minutes")
        st.write("")

    # set nested button
    # declare initial state
    if "logout" not in st.session_state:
        st.session_state["logout"] = False

    # action on logout button click
    if st.button("Logout"):
        st.session_state["logout"] = not st.session_state["logout"]
        # locate logout_name index in log_df
        start_time = df["start"][df["name"] == name_logout].values[0]
        name_logout_log_idx = (
            log_df.index[
                ((log_df["name"] == name_logout) & (log_df["start"] == start_time))
            ].tolist()[0]
            + 2
        )
        # update log
        worksheet_log.update_cell(name_logout_log_idx, 6, str(finish_actual))
        worksheet_log.update_cell(name_logout_log_idx, 7, duration_actual)
        # remove name entry
        name_logout_idx = df.index[df["name"] == name_logout].tolist()[0] + 2
        worksheet_active.delete_rows(name_logout_idx)

        st.success("Logged out, Thank you for using NIG Training Gym", icon="✅")
        st.balloons()
        st.write("")
        st.write("")

    # nested refresh button
    if st.session_state["logout"]:
        if st.button("Refresh", key="refresh_logout_btn"):
            st.session_state["logout"] = False
            st.cache_data.clear()
            st.cache_resource.clear()
            st.experimental_rerun()
# %%
with tab4:
    # show active user df
    st.subheader("Active user")
    st.dataframe(df)
    # show user log df
    st.subheader("User log")
    st.dataframe(log_df)
# %%
footer = """<style>
.footer {
position: static;
left: 0;
bottom: 0;
width: 100%;
background: rgba(0,0,0,0);
text-align: center;
}
</style>

<div class="footer">
<p style='display: block;
 text-align: center;
 font-size:14px;
 color:darkgray'>Developed with ❤ by Abdullah Syafiq</p>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)
