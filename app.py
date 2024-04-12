#%%
import pandas as pd
import numpy as np
import unicodedata
import plotly.express as px
from sklearn.cluster import DBSCAN
from geopy.distance import great_circle
from shapely.geometry import MultiPoint
import streamlit as st
import json
import warnings
warnings.filterwarnings("ignore")
#%%
st.set_page_config(
    page_title="Reporte de Conflictos Mineros a Marzo 2024",
    page_icon=":pick:",
    layout="wide"
)
#%%
df = pd.read_excel("conflictos.xlsx")
#%%
with open("peru_departamental_simple.geojson", encoding="utf8") as data:
    departamentos = json.load(data)

for feature in departamentos["features"]:
    feature["properties"]["NOMBDEP"] = feature["properties"]["NOMBDEP"].lower()

id = []
departamento = []

for idx in range(len(departamentos["features"])):
    id.append(departamentos["features"][idx]["properties"]["FIRST_IDDP"])
    departamento.append(departamentos["features"][idx]["properties"]["NOMBDEP"])

geojson_df = pd.DataFrame({
    "id":id,
    "departamento":departamento
})
#%%
#Funcion para eliminar tildes
def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

#convertimos los nombres de los departamentos en minuscula y removemos tildes
df['departamento'] = df['departamento'].apply(lambda x: remove_accents(x).lower())
#%%
df["Count"] = 1
df_count = df.groupby("departamento").agg({"Count":"sum"}).reset_index()
df_choropleth = geojson_df.merge(df_count,
                                 how="left",
                                 on="departamento"
                                 )
#%%Analisis Geografico
fig_choro = px.choropleth_mapbox(df_choropleth, 
                    geojson=departamentos, 
                    locations='id', 
                    featureidkey='properties.FIRST_IDDP',
                    color='Count',
                    template="plotly_dark",
                    mapbox_style="carto-darkmatter", 
                    color_continuous_scale='deep',
                    hover_data=["departamento", "Count"], 
                    center={
                            "lat":-9,
                            "lon":-75
                            },
                    zoom=4,
                    )
fig_choro.update_layout(margin={'r':0,'t':0,'l':0,'b':0})
conflict_point = px.scatter_mapbox(df,
                            lat='lat',
                            lon='lon',
                            hover_data=["caso", "estado","distrito", "provincia", "departamento"],
                            color_discrete_sequence=["#FEFE14"]
                            )
conflict_point.update_layout(
    margin={'r': 0, 't': 0, 'b': 0, 'l': 0}
)
fig_choro.add_trace(conflict_point.data[0])
# %%
fig_map = px.scatter_mapbox(df,
                        lat='lat',
                        lon='lon',
                        mapbox_style='carto-darkmatter',
                        zoom=4,
                        size='Count',
                        color='estado',
                        hover_data=["caso", "estado","distrito", "provincia", "departamento"],
                        center={
                            "lat":-9,
                            "lon":-75
                            },
                        color_discrete_sequence=px.colors.qualitative.Dark24_r,
                        size_max=12
                        )
fig_map.update_layout(margin={'r':0,'t':0,'l':0,'b':0})
# %%
fig_density = px.density_mapbox(df,
                        lat='lat',
                        lon='lon',
                        hover_data=["caso", "estado","distrito", "provincia", "departamento"],
                        mapbox_style='carto-darkmatter',
                        color_continuous_scale='Inferno',
                        zoom=4,
                        z='Count',
                        radius=20,
                        opacity=0.9,
                        center={
                            "lat":-9,
                            "lon":-75
                            }
                        )
fig_density.update_layout(
    margin={'r': 0, 't': 0, 'b': 0, 'l': 0},
    coloraxis_colorbar=None
    )
#%%DBSCAN
KM_EPSILON = 15
MIN_SAMPLES = 2

def get_centermostpoint(cluster):
    centroid = (MultiPoint(cluster).centroid.x, MultiPoint(cluster).centroid.y)
    centermost_point = min(cluster, key=lambda point: great_circle(point,centroid).m)
    return tuple(centermost_point)

df_lc_clean = df[~df['lat'].isna()]
coords_cluster = df_lc_clean[['lat', 'lon']].to_numpy()

kms_per_radian = 6371.0088 #longitud de radio medio de la tierra. Distancias en radianes a kilometros
epsilon = KM_EPSILON / kms_per_radian

db = DBSCAN(eps=epsilon,
           min_samples=MIN_SAMPLES,
            algorithm='ball_tree',
            metric='haversine'
           ).fit(np.radians(coords_cluster))

cluster_labels = db.labels_

num_clusters = len(set(cluster_labels))
clusters = pd.Series([coords_cluster[cluster_labels == n] for n in range(num_clusters)]).iloc[:-1]

centermost_points = clusters.map(get_centermostpoint)

lats, lons = zip(*centermost_points)
rep_points = pd.DataFrame({'lat':lats, 'lon':lons})
rep_points['size'] = 6
#%%figDBSCAN
fig_choroDBSCAN = px.choropleth_mapbox(df_choropleth, 
                                        geojson=departamentos, 
                                        locations='id', 
                                        featureidkey='properties.FIRST_IDDP',
                                        color='Count',
                                        template="plotly_dark",
                                        mapbox_style="carto-darkmatter", 
                                        color_continuous_scale='deep',
                                        hover_data=["departamento", "Count"], 
                                        center={
                                                "lat":-9,
                                                "lon":-75
                                                },
                                        zoom=4,
                                        )

incidentes_cluster = px.scatter_mapbox(rep_points,
                                      lat="lat",
                                       lon="lon",
                                       hover_name="size",
                                       hover_data=["size"],
                                       mapbox_style="carto-darkmatter",
                                       zoom=10,
                                       center={
                                                "lat":-9,
                                                "lon":-75
                                                },
                                       opacity=0.6,
                                       color_discrete_sequence=['#FEFE14']
                                      )

fig_choroDBSCAN.add_trace(incidentes_cluster.data[0])
fig_choroDBSCAN.update_layout(
    margin={'r': 0, 't': 0, 'b': 0, 'l': 0}
                             )
#%%Analisis descriptivo
#%% Parallel
fig_parallel = px.parallel_categories(df,
                                      dimensions=["estado", "fase", "vio_if", "dial_if"],
                                      template="seaborn", #plotly_white, seaborn, simple_white, plotly, plotly_mpl
                                      #color_continuous_scale=px.colors.sequential.Inferno
                                      labels={
                                          "estado": "Estado del Caso",
                                          "fase":"Fase",
                                          "vio_if":"Hubo violencia",
                                          "dial_if":"Hubo diálogo"    
                                              },
                                      height=500
                                      )
#%%
empresas_count = df.groupby("empresa")["Count"].sum().reset_index()
empresas_count = empresas_count.sort_values(by="Count", ascending=False)
top_empresas = empresas_count.head(5)
top_empresas = top_empresas[::-1]
fig_topEmp = px.bar(top_empresas, 
                 x='Count', 
                 y='empresa',
                 template="plotly_white",
                 title='Top 5 Entidades con más casos',
                 labels={'empresa': 'Entidad', 'Count': 'Número de Casos'}
                 )
# %%
departamento_count = df.groupby("departamento")["Count"].sum().reset_index()
departamento_count = departamento_count.sort_values(by="Count", ascending=False)
top_departamentos = departamento_count.head(5)
top_departamentos = top_departamentos[::-1]
fig_topDep = px.bar(top_departamentos, 
                 x='Count', 
                 y='departamento',
                 template="plotly_white",
                 title='Top 5 Departamento con más casos',
                 labels={'departamento': 'Departamento', 'Count': 'Número de Casos'}
                 )
# %%
casos_activos = df[df['estado'] == 'Activo']
fase_count = casos_activos.groupby('fase').size().reset_index(name='Count')
fase_count = fase_count.sort_values(by='Count', ascending=True)
# Crear el gráfico de barras
fig_fase_activa = px.bar(fase_count, 
                         x='Count', 
                         y='fase',
                         template="plotly_white",
                         height=425,
                         title='Distribución de casos en estado activo por fase del conflicto',
                         labels={'fase': 'Fase del Conflicto', 'Count': 'Número de Casos'}
                        )
# %% Layout
st.title("Reporte de Conflictos Mineros a Marzo 2024")
st.write("El Reporte de Conflictos Mineros a Marzo 2024 proporciona una visión detallada de la situación de los conflictos sociales en Perú. A través de análisis descriptivos y geográficos, se exploran los principales departamentos afectados, las entidades involucradas y las fases de los conflictos activos. Además, se emplean diversas visualizaciones, como mapas choropleth, mapas de calor y gráficos de barras, para ofrecer una comprensión completa de la distribución geográfica y la intensidad de los conflictos. El uso del modelo de clustering espacial DBSCAN añade una capa adicional de análisis al identificar áreas críticas con alta concentración de conflictos. Este reporte proporciona valiosa información para comprender y abordar los desafíos relacionados con los conflictos mineros en el país.")
st.divider()

col = st.columns((3.3, 4.7), gap = "medium")

with col[0]:
    st.subheader("Análisis Descriptivo")
    st.divider()
    st.subheader("Top 5 Departamentos con más casos")
    st.write("Podemos observar cuáles son los departamentos que concentran mayor cantidad de conflictos mineros reportados. Podemos observar que tres departamentos son del sur del país como Apurímac, Cusco y Ayacucho.")
    st.plotly_chart(fig_topDep, use_container_width=True)
    st.subheader("Top 5 Entidades involucradas")
    st.write("En cuanto a las entidades involucradas en conflictos observamos que la Minera Las Bambas lidera la lista con 10 conflictos involucrados, además se destaca la presencia de conflictos vinculados con empresas informales e ilegales.")
    st.plotly_chart(fig_topEmp, use_container_width=True)
    st.subheader("Casos en Activo")
    st.write("El gráfico de barras muestra la distribución de casos en estado activo por fase del conflicto.  Destacan 48 casos en fase de diálogo, seguidos por 6 casos en fase de desescalada. Por otro lado, los conflictos en fases ascendentes son menos frecuentes, con tan solo 4 casos registrados.")
    st.plotly_chart(fig_fase_activa, use_container_width=True)
    st.write("")
    st.write("")
    st.subheader("Flujo de Casos: Categorías Paralelas")
    st.write("El Diagrama de Categorías Paralelas muestra de manera clara y concisa la relación entre el estado del caso, la fase del conflicto, la presencia de violencia y el diálogo posterior. Con ejes verticales que representan cada variable, y conexiones entre ellos, se identifican patrones en la evolución y resolución de los conflictos sociales de forma rápida y precisa.")
    st.plotly_chart(fig_parallel, use_container_width=True)

with col[1]:
    st.subheader("Análisis Geográfico")
    st.divider()
    st.subheader("Mapa Choropleth")
    st.write("El gráfico generado combina un mapa choropleth con puntos de conflicto superpuestos para proporcionar una representación visual completa de la distribución geográfica de los conflictos sociales en los departamentos de Perú. En el choropleth, el color de cada departamento indica la intensidad de los conflictos, mientras que los puntos individuales resaltan ubicaciones específicas de conflictos.")
    st.plotly_chart(fig_choro, use_container_width=True)
    st.subheader("Mapa de Calor")
    st.write("El gráfico de densidad muestra la concentración de conflictos sociales en Perú mediante un mapa de calor. Los colores más intensos indican áreas con mayor densidad de casos, mientras que los colores más claros representan áreas con menor concentración. Esto proporciona una visualización clara de las zonas de mayor y menor incidencia de conflictos en el país.")
    st.plotly_chart(fig_density, use_container_width=True)
    st.subheader("Mapa de Puntos")
    st.write("El gráfico muestra la distribución geográfica de los conflictos sociales en Perú mediante puntos ubicados en el mapa. Cada punto representa un incidente, con su tamaño indicando la cantidad de casos y su color representando el estado del conflicto. Esta visualización permite identificar fácilmente las áreas más afectadas y el estado predominante de los conflictos en el país.")
    st.plotly_chart(fig_map, use_container_width=True)
    st.subheader("Modelo de Clustering Espacial DBSCAN")
    st.write("DBSCAN (Density-Based Spatial Clustering of Applications with Noise) es un algoritmo de clustering geoespacial que puede ser aplicado para detectar zonas críticas donde se concentran conflictos sociales en el país. Este modelo identifica regiones densas en el espacio geográfico, representadas por puntos en el mapa, las cuales indican áreas donde ocurren numerosos conflictos sociales. Al detectar estas zonas, DBSCAN proporciona una visión clara de las áreas geográficas que requieren una atención particular debido a la alta incidencia de conflictos sociales.")
    st.plotly_chart(fig_choroDBSCAN, use_container_width=True)
    with st.expander("Acerca de:", expanded=False):
        st.write(
    """
    - :orange[**Realizado por:**] [Tato Warthon](https://github.com/warthon-190399).
    - :orange[**Fuente:**] Los datos fueron recopilados mediante técnicas de extracción web automatizada a partir de los reportes de conflictos sociales de la Defensoría del Pueblo que se publican mensualmente.
    - :orange[**Metodología:**] 
        - **Recopilación de Datos**: Los datos se obtuvieron a partir de los reportes mensuales de conflictos sociales publicados por la Defensoría del Pueblo. Se utilizó un proceso de extracción web automatizada para recopilar la información necesaria.
        - **Preprocesamiento de Datos**: Una vez recopilados, los datos fueron sometidos a un proceso de limpieza y preprocesamiento para eliminar datos duplicados, incompletos o inconsistentes, así como para homogeneizar el formato de los datos.
        - **Análisis Descriptivo**: Se realizó un análisis descriptivo de los datos para explorar la distribución y características de los conflictos sociales en Perú. Esto incluyó la identificación de los principales departamentos afectados, las entidades involucradas y las fases de los conflictos.
        - **Análisis Geoespacial**: Se emplearon técnicas de visualización geoespacial para explorar la distribución geográfica de los conflictos sociales. Esto incluyó la creación de mapas choropleth, mapas de calor y mapas de puntos para representar la intensidad y ubicación de los conflictos.
        - **Modelado con DBSCAN**: Se aplicó el algoritmo de clustering espacial DBSCAN para identificar áreas críticas con alta concentración de conflictos. Esto proporcionó información adicional sobre las zonas más afectadas y la distribución espacial de los conflictos. Los parámetros a destacar son:
            - `KM_EPSILON = 15`: Este parámetro define la distancia máxima entre dos puntos para que se consideren parte del mismo vecindario. En este caso, se estableció en 15 kilómetros, lo que significa que dos puntos están en el mismo vecindario si están dentro de esta distancia.
            - `MIN_SAMPLES = 2`: Este parámetro especifica el número mínimo de puntos que deben estar dentro de la distancia `KM_EPSILON` para formar un grupo. Se fijó en 2, lo que implica que se necesitan al menos dos puntos en un vecindario para formar un grupo.
        Este proceso identificó áreas críticas con alta concentración de conflictos, proporcionando información adicional sobre las zonas más afectadas y la distribución espacial de los conflictos.
    """
        )
    logo = "logoPulseNegro.png"
    st.image(logo, width=400)
