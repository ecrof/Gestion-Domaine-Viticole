import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Gestion Domaine Viticole", layout="centered")

# 1 & 2. Initialisation du client Supabase
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = get_supabase_client()

# 3. Initialisation de st.session_state pour vider les formulaires et éviter les doublons au rechargement
if "reg_volunteer_name" not in st.session_state:
    st.session_state["reg_volunteer_name"] = ""
if "reg_needs_meal" not in st.session_state:
    st.session_state["reg_needs_meal"] = False
if "task_title" not in st.session_state:
    st.session_state["task_title"] = ""
if "task_row_number" not in st.session_state:
    st.session_state["task_row_number"] = 1


def add_registration_callback():
    event_id = st.session_state.get("reg_event")
    name = st.session_state.get("reg_volunteer_name", "").strip()
    meal = st.session_state.get("reg_needs_meal", False)
    
    if not name:
        st.error("Veuillez saisir le nom de l'intervenant.")
        return
    
    if name and event_id:
        try:
            supabase.table("registrations").insert({
                "event_id": event_id,
                "volunteer_name": name,
                "needs_meal": meal
            }).execute()
            st.success("Inscription réussie !")
            # Réinitialisation des champs du formulaire
            st.session_state.reg_volunteer_name = ""
            st.session_state.reg_needs_meal = False
        except Exception as e:
            st.error(f"Erreur lors de l'inscription : {e}")


def add_task_callback():
    title = st.session_state.get("task_title", "").strip()
    row = st.session_state.get("task_row_number", 1)
    
    if not title:
        st.error("Veuillez saisir la description de la tâche.")
        return
    
    if title:
        try:
            supabase.table("tasks").insert({
                "title": title,
                "row_number": row,
                "status": "À faire"
            }).execute()
            st.success("Tâche ajoutée avec succès !")
            # Réinitialisation des champs du formulaire
            st.session_state.task_title = ""
            st.session_state.task_row_number = 1
        except Exception as e:
            st.error(f"Erreur lors de l'ajout de la tâche : {e}")


def complete_task_callback(task_id):
    try:
        supabase.table("tasks").update({"status": "Fait"}).eq("id", task_id).execute()
        st.success("Tâche marquée comme faite !")
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour : {e}")


st.title("🍇 Gestion du Domaine Viticole")

# Récupération globale des données avec la syntaxe v2
try:
    events_data = supabase.table("events").select("*").execute().data
except Exception as e:
    st.error(f"Impossible de charger les événements : {e}")
    events_data = []

try:
    registrations_data = supabase.table("registrations").select("*").execute().data
except Exception as e:
    st.error(f"Impossible de charger les inscriptions : {e}")
    registrations_data = []

try:
    tasks_data = supabase.table("tasks").select("*").execute().data
except Exception as e:
    st.error(f"Impossible de charger les tâches : {e}")
    tasks_data = []


# 4. Création des 3 onglets
tab1, tab2, tab3 = st.tabs(["Chantiers", "Tâches", "Ressources"])

# ONGLET 1 : CHANTIERS
with tab1:
    st.header("Chantiers et Inscriptions")
    
    if events_data:
        # Les événements possèdent 'title' et 'start_date' dans le schéma réel
        event_options = {e['id']: f"{e.get('start_date', 'Sans date')} - {e.get('title', 'Chantier')}" for e in events_data}
        
        st.subheader("S'inscrire à un chantier")
        with st.form("registration_form"):
            st.selectbox("Sélectionner un chantier", 
                         options=list(event_options.keys()), 
                         format_func=lambda x: event_options[x], 
                         key="reg_event")
            st.text_input("Nom de l'intervenant", key="reg_volunteer_name")
            st.checkbox("Repas requis (cocher si oui)", key="reg_needs_meal")
            
            # Utilisation du callback pour l'insertion
            st.form_submit_button("S'inscrire", on_click=add_registration_callback)
            
        st.subheader("Récapitulatif des inscriptions")
        if registrations_data:
            df_events = pd.DataFrame(events_data)
            df_regs = pd.DataFrame(registrations_data)
            
            # Filtrer les inscriptions associées à un événement valide
            df_regs_valid = df_regs[df_regs["event_id"].notna()]
            
            if not df_events.empty and not df_regs_valid.empty:
                # Jointure pour obtenir le nom de l'événement associé à l'inscription
                df_merged = pd.merge(df_regs_valid, df_events, left_on="event_id", right_on="id", suffixes=('_reg', '_event'))
                
                # Tableau récapitulatif : inscrits et repas par événement (les colonnes réelles de events sont 'title' et 'start_date')
                if "title_event" in df_merged.columns or "title" in df_merged.columns:
                    title_col = "title_event" if "title_event" in df_merged.columns else "title"
                    summary = df_merged.groupby(title_col).agg(
                        Inscrits=('volunteer_name', 'count'),
                        Repas_Prévus=('needs_meal', lambda x: int(x.fillna(False).sum()))
                    ).reset_index().rename(columns={
                        title_col: "Chantier",
                        "Inscrits": "Nombre d'inscrits",
                        "Repas_Prévus": "Repas requis"
                    })
                    
                    st.dataframe(summary, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune inscription associée à un chantier pour le moment.")
        else:
            st.info("Aucune inscription enregistrée dans la base de données.")
    else:
        st.warning("Aucun chantier configuré dans la table events. Créez des chantiers dans votre base Supabase (avec title, start_date et type).")

# ONGLET 2 : TÂCHES
with tab2:
    st.header("Gestion des Tâches")
    
    st.subheader("Ajouter une tâche")
    with st.form("task_form"):
        st.text_input("Description de la tâche", key="task_title")
        st.number_input("Numéro de rang (1-40)", min_value=1, max_value=40, step=1, key="task_row_number")
        st.form_submit_button("Ajouter", on_click=add_task_callback)
        
    st.subheader("Liste des tâches")
    if tasks_data:
        df_tasks = pd.DataFrame(tasks_data)
        if "row_number" in df_tasks.columns:
            df_tasks = df_tasks.sort_values(by="row_number")
        
        for index, row in df_tasks.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            # La colonne réelle est 'title' pour la description, et 'row_number' pour le rang
            col1.write(f"**Rang {row.get('row_number', 'N/A')}** : {row.get('title', '')}")
            
            status = row.get("status", "À faire")
            if status == "Fait":
                col2.success("Fait")
                col3.write("") 
            else:
                col2.warning("À faire")
                # Bouton pour changer le statut utilisant un callback
                col3.button("✓ Terminer", 
                            key=f"btn_done_{row.get('id')}", 
                            on_click=complete_task_callback, 
                            args=(row.get("id"),))
    else:
        st.info("Aucune tâche répertoriée.")

# ONGLET 3 : RESSOURCES
with tab3:
    st.header("Ressources et Matériel")
    
    st.markdown("""
    ### ✂️ Taille
    - Sécateur manuel ou électrique (batteries chargées)
    - Scie passe-partout
    - Gants de protection anti-coupure
    - Vêtements chauds et adaptés aux intempéries

    ### 🌱 Ébourgeonnage
    - Gants légers de protection
    - Ceinture de maintien lombaire (recommandé)
    - Lunettes de protection contre les sarments

    ### 🍇 Vendanges
    - Sécateur de vendange (épinette)
    - Seau / Panier de récolte
    - Bottes ou chaussures de sécurité étanches
    - Casquette ou chapeau, crème solaire
    """)