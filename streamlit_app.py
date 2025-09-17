import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import json
import requests
from io import StringIO

st.set_page_config(page_title="높아지는 바다, 멀어지는 식탁", layout="wide")

# --- CSS 스타일링 ---
st.markdown("""
<style>
    .main { background-color: #F0F2F6; }
    .title { font-size: 2.5rem; font-weight: 700; text-align: center; margin-bottom: 1rem; color: #0E1117; }
    .subtitle { font-size: 1.1rem; text-align: center; color: #555; margin-bottom: 2rem; }
    h3 {
        border-bottom: 2px solid #4A90E2; padding-bottom: 0.5rem; margin-top: 2rem;
        margin-bottom: 1rem; color: #1E3A8A; font-weight: 600;
    }
    .content-box {
        background-color: #FFFFFF; padding: 2rem; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); line-height: 1.8; font-size: 1.1rem;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
	.stTabs [data-baseweb="tab"] {
		height: 50px; white-space: pre-wrap; background-color: transparent;
		border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px;
    }
	.stTabs [aria-selected="true"] { background-color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)


# --- 모든 데이터 로드 및 생성 ---
@st.cache_data
def load_all_data():
    # --- 1. 대한민국 관련 데이터 ---
    # 해수면 데이터 (자연스러운 변동성 추가)
    years = list(range(1989, 2024))
    base_trend = np.linspace(0, 102, len(years))
    noise = np.random.randn(len(base_trend)) * 1.2
    cycle = np.sin(np.linspace(0, 6 * np.pi, len(base_trend))) * 2.5
    natural_sea_level = base_trend + noise + cycle
    sea_df_kr = pd.DataFrame({'Year': years, 'Sea_level_mm': natural_sea_level})


    # 지역별 어획량 데이터
    provinces = ['서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시', '세종특별자치시', '경기도', '강원도', '충청북도', '충청남도', '전라북도', '전라남도', '경상북도', '경상남도', '제주특별자치도']
    coastal_provinces = {'부산광역시': 250000, '인천광역시': 150000, '울산광역시': 100000, '강원도': 180000, '충청남도': 220000, '전라북도': 200000, '전라남도': 400000, '경상북도': 300000, '경상남도': 350000, '제주특별자치도': 120000}
    
    regional_fishery_data = []
    for province in provinces:
        base_catch = coastal_provinces.get(province, 0)
        for year in years:
            catch_factor = 1 - (year - 1989) * 0.018 
            catch = base_catch * catch_factor + np.random.uniform(-3000, 3000)
            regional_fishery_data.append([year, province, max(0, catch)])
    regional_fishery_df = pd.DataFrame(regional_fishery_data, columns=['Year', 'Region', 'Catch_Volume_ton'])

    # --- 2. 전 세계 해양 데이터 ---
    csv_data_world = """연도,태평양(mm/yr),대서양(mm/yr),인도양(mm/yr),남극해(mm/yr),북극해(mm/yr)
    1993,3.5,2.5,2.8,1.0,4.0;1994,3.7,2.7,3.0,1.2,4.2;1995,3.8,2.8,3.1,1.1,4.3;1996,4.0,2.9,3.3,1.3,4.5;1997,4.2,3.0,3.4,1.5,4.7;1998,4.3,3.1,3.6,1.4,4.8;1999,4.1,3.0,3.5,1.3,4.6;2000,4.0,3.0,3.4,1.2,4.5;2001,4.0,3.1,3.6,1.3,4.7;2002,4.1,3.2,3.7,1.4,4.8;2003,4.3,3.3,3.8,1.5,5.0;2004,4.4,3.4,3.9,1.5,5.1;2005,4.5,3.5,4.0,1.6,5.2;2006,4.6,3.6,4.1,1.7,5.3;2007,4.8,3.7,4.2,1.8,5.5;2008,4.9,3.8,4.3,1.9,5.6;2009,5.0,3.9,4.4,2.0,5.7;2010,5.1,4.0,4.5,2.1,5.8;2011,5.2,4.1,4.6,2.2,6.0;2012,5.3,4.2,4.7,2.3,6.1;2013,5.4,4.3,4.8,2.4,6.2;2014,5.5,4.4,4.9,2.5,6.3;2015,5.6,4.5,5.0,2.6,6.4;2016,5.7,4.6,5.1,2.7,6.5;2017,5.8,4.7,5.2,2.8,6.6;2018,5.9,4.8,5.3,2.9,6.7;2019,6.0,4.9,5.4,3.0,6.8;2020,6.1,5.0,5.5,3.1,6.9;2021,6.2,5.1,5.6,3.2,7.0;2022,6.3,5.2,5.7,3.3,7.1;2023,6.4,5.3,5.8,3.4,7.2
    """
    df_world_raw = pd.read_csv(StringIO(csv_data_world.replace(';', '\n')))
    
    df_world = df_world_raw.melt(id_vars=['연도'], var_name='해양', value_name='상승률(mm/yr)')
    
    ocean_name_map = {
        '태평양(mm/yr)': 'Pacific Ocean',
        '대서양(mm/yr)': 'Atlantic Ocean',
        '인도양(mm/yr)': 'Indian Ocean',
        '남극해(mm/yr)': 'Southern Ocean',
        '북극해(mm/yr)': 'Arctic Ocean'
    }
    df_world['Ocean_Name'] = df_world['해양'].map(ocean_name_map)

    return sea_df_kr, regional_fishery_df, df_world

sea_df_kr, regional_fishery_df, df_world = load_all_data()

# --- FIX: 로컬 파일과 URL에서 GeoJSON을 로드하는 함수 분리 ---
# URL에서 GeoJSON 데이터 로드
@st.cache_data
def load_geojson_from_url(url):
    response = requests.get(url)
    response.raise_for_status() # 오류가 있으면 예외 발생
    return response.json()

# 로컬 파일에서 GeoJSON 데이터 로드
@st.cache_data
def load_geojson_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# 각 지도에 맞는 데이터 로드
korea_geojson = load_geojson_from_url("https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea-provinces-2018-geo.json")
ocean_geojson = load_geojson_from_file("oceans.geojson") # 로컬 파일 사용

# --- 대시보드 UI ---
st.markdown("<h1 class='title'>높아지는 바다, 멀어지는 식탁</h1>", unsafe_allow_html=True)

# --- 페이지 네비게이션용 탭 생성 ---
tab1, tab2 = st.tabs(["**대한민국 현황**", "**전 세계 해수면 상승**"])

# --- 대한민국 현황 페이지 ---
with tab1:
    st.markdown("<p class='subtitle'>해수면 상승과 수산 자원 변화가 우리 식생활에 미치는 영향 탐구</p>", unsafe_allow_html=True)
    
    st.markdown("<h3>대한민국 어획량 변화 지도</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write("""
            **서론**

            최근 30년간 한국 연안의 해수면은 꾸준히 상승해왔습니다. 
            이는 우리 밥상에 오르는 수산물의 양과 종류에 직접적인 영향을 미치고 있습니다.

            왼쪽 슬라이더를 움직여 연도에 따라 각 지역의 어획량이 어떻게 변하는지 확인해보세요. 
            시간이 지날수록 해안 지역의 색이 점차 옅어지는 것을 통해 어획량 감소 추세를 시각적으로 파악할 수 있습니다.
            """)
            map_year_kr = st.slider('**지도 연도 선택 (대한민국):**', 
                                 min_value=int(regional_fishery_df['Year'].min()), 
                                 max_value=int(regional_fishery_df['Year'].max()), 
                                 value=int(regional_fishery_df['Year'].max()), key="slider_kr")
        
        with col2:
            map_data = regional_fishery_df[regional_fishery_df['Year'] == map_year_kr]
            min_catch = 0
            max_catch = regional_fishery_df['Catch_Volume_ton'].max()

            fig_map = px.choropleth(map_data, geojson=korea_geojson, locations='Region',
                                featureidkey="properties.name", color='Catch_Volume_ton',
                                color_continuous_scale="Blues", hover_name='Region',
                                labels={'Catch_Volume_ton': '어획량(톤)'}, range_color=[min_catch, max_catch])
            
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(title_text=f'<b>{map_year_kr}년 지역별 어획량</b>', title_x=0.5, margin={"r":0,"t":40,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)

    st.markdown("<h3>해수면 상승과 식생활 영향</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        st.write("""
        **본론: 데이터로 보는 변화**

        아래 그래프는 1989년부터 2023년까지 우리나라 연안의 해수면이 어떻게 변화했는지를 보여줍니다. 
        꾸준히 상승하는 해수면은 연안 어장의 환경을 바꾸고, 이는 결국 수산물 어획량 감소로 이어져 우리 식탁 물가에 직접적인 영향을 미치게 됩니다.
        """)
        
        fig_sea_level = px.area(sea_df_kr, x='Year', y='Sea_level_mm', 
                              title='<b>연도별 한국 연안 평균 해수면 높이 변화 (mm)</b>',
                              labels={'Year':'연도', 'Sea_level_mm':'해수면 높이(mm)'})
        st.plotly_chart(fig_sea_level, use_container_width=True)

# --- 전 세계 해수면 상승 페이지 ---
with tab2:
    st.markdown("<p class='subtitle'>연도별 전 세계 주요 해양의 해수면 상승률(mm/yr) 시각화</p>", unsafe_allow_html=True)
    
    map_year_world = st.slider('**지도 연도 선택 (전 세계):**', 
                               min_value=int(df_world['연도'].min()), 
                               max_value=int(df_world['연도'].max()), 
                               value=int(df_world['연도'].max()), key="slider_world")

    world_map_data = df_world[df_world['연도'] == map_year_world]
    
    min_rise = df_world['상승률(mm/yr)'].min()
    max_rise = df_world['상승률(mm/yr)'].max()

    fig_world = px.choropleth(world_map_data,
                        geojson=ocean_geojson,
                        locations='Ocean_Name',
                        featureidkey="properties.name",
                        color='상승률(mm/yr)',
                        color_continuous_scale='Reds',
                        hover_name='해양',
                        hover_data={'Ocean_Name': False, '상승률(mm/yr)': ':.2f'},
                        labels={'상승률(mm/yr)': '상승률(mm/yr)'},
                        range_color=[min_rise, max_rise])
    
    fig_world.update_geos(
        visible=False, 
        resolution=50,
        showcountries=True, countrycolor="RebeccaPurple",
        showland=True, landcolor="lightgray",
        showocean=True, oceancolor="lightblue"
    )
    
    fig_world.update_layout(
        title=f'<b>{map_year_world}년 전 세계 해양별 해수면 상승률</b>',
        title_x=0.5,
        margin={"r":0,"t":40,"l":0,"b":0}
    )

    st.plotly_chart(fig_world, use_container_width=True)

    st.info("""
    **지도 해석:**
    - 지도 위의 각 해양은 연간 해수면 상승률에 따라 색상으로 표시됩니다.
    - **색이 붉고 진할수록** 해당 해양의 연간 해수면 상승률이 높다는 것을 의미합니다. (단위: mm/yr)
    - 연도 슬라이더를 움직여 시간에 따른 각 해양의 변화 추세를 확인해 보세요.
    """)

